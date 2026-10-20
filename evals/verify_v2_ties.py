"""Read-only verification of archived rankings; never performs retrieval or evaluation."""

import asyncio
import hashlib
import json
from collections import Counter
from pathlib import Path

from psycopg.rows import dict_row

from filinglens.config import Settings
from filinglens.db import pool_for


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def identity(row):
    # Exact stored text is the comparison; provenance disambiguates repeated text.
    return row["accession"], row["item"], row["ordinal"], row["text"]


async def main():
    protected = [
        "evals/handwritten.jsonl",
        "evals/handwritten_v2.jsonl",
        "evals/results/retrieval.json",
        "evals/results/retrieval_v2.json",
    ]
    before = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in protected}
    archives = [read(protected[2]), read(protected[3])]
    migration = read("evals/corpus_v2_migration.json")
    audit = read("docs/CORPUS_V2_AUDIT.json")["items"]
    records = [
        json.loads(line) for line in Path(protected[1]).read_text(encoding="utf-8").splitlines()
    ]
    rankings = [{(d["question_id"], d["mode"]): d for d in a["details"]} for a in archives]
    checked = []
    for record in records:
        filters = record["filters"]
        repaired = [
            item
            for item in audit
            if item["approved_repair"]
            and all(item.get(key) == value for key, value in filters.items() if key != "items")
            and (not filters.get("items") or item["item"] in filters["items"])
        ]
        if archives[1]["changes"][record["id"]]["group"] == "a" and not repaired:
            checked.append(record["id"])
    assert len(checked) == 24
    assert set(checked) == {r["id"] for r in records} - {
        r["id"] for r in migration["review_questions"]
    }
    output = {
        "method": (
            "Archived rankings only; repeatable-read READ ONLY SQL scores; "
            "exact float4 bytes, not rounded scores. No retrieval/evaluation run."
        ),
        "checked_questions": checked,
        "per_question": [],
        "exceptions": [],
        "keyword_ties_overall": {},
    }
    tie_slots = [0, 0]
    total_slots = [0, 0]
    async with pool_for(Settings().database_url) as pool, pool.connection() as conn:
        conn.row_factory = dict_row
        await conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        for record in records:
            qid = record["id"]
            row = await (
                await conn.execute(
                    "SELECT tsvector_to_array(to_tsvector('english',%s)) AS lexemes",
                    (record["question"],),
                )
            ).fetchone()
            terms = " | ".join(
                "'" + word.replace("\\", "\\\\").replace("'", "''") + "'" for word in row["lexemes"]
            )
            versions = []
            for index, corpus_id in enumerate([migration["v1"], migration["v2"]]):
                keyword = rankings[index][qid, "keyword"]
                vector = rankings[index][qid, "vector"]
                ids = list(set(keyword["ranked_ids"] + vector["ranked_ids"]))
                rows = await (
                    await conn.execute(
                        """SELECT c.id,c.accession,c.item,c.ordinal,c.text,
                                  ts_rank_cd(c.tsv,%s::tsquery) AS score,
                                  encode(float4send(ts_rank_cd(c.tsv,%s::tsquery)),
                                         'hex') AS score_hex
                           FROM chunks c JOIN corpus_chunks cc ON cc.chunk_id=c.id
                           WHERE cc.corpus_id=%s AND c.id=ANY(%s)""",
                        (terms, terms, corpus_id, ids),
                    )
                ).fetchall()
                by_id = {row["id"]: row for row in rows}
                assert len(by_id) == len(ids)
                saved_cache = read(keyword["cache_path"])
                assert [hit["chunk_id"] for hit in saved_cache] == keyword["ranked_ids"]
                for hit in saved_cache:
                    assert hit["text"] == by_id[hit["chunk_id"]]["text"]
                    assert hit["score"] == by_id[hit["chunk_id"]]["score"]
                kw = [by_id[chunk_id] for chunk_id in keyword["ranked_ids"]]
                counts = Counter(row["score_hex"] for row in kw)
                tied = sum(count for count in counts.values() if count > 1)
                tie_slots[index] += tied
                total_slots[index] += len(kw)
                assert kw == sorted(kw, key=lambda row: (-row["score"], row["id"]))
                versions.append(
                    {
                        "keyword": kw,
                        "vector": [by_id[chunk_id] for chunk_id in vector["ranked_ids"]],
                        "tied_slots": tied,
                    }
                )
            detail = {
                "id": qid,
                "question": record["question"],
                "checked_unchanged_scope": qid in checked,
                "keyword_tied_slots_v1": versions[0]["tied_slots"],
                "keyword_tied_slots_v2": versions[1]["tied_slots"],
            }
            if qid in checked:
                # Confirm the whole eligible passage set, not just retrieved candidates.
                eligible = []
                for corpus_id in [migration["v1"], migration["v2"]]:
                    where = ["cc.corpus_id=%s"]
                    params = [corpus_id]
                    for key, value in record["filters"].items():
                        if key == "items":
                            where.append("c.item=ANY(%s)")
                        else:
                            assert key in {"ticker", "fiscal_year", "fiscal_period"}
                            where.append(f"{'co' if key == 'ticker' else 'c'}.{key}=%s")
                        params.append(value)
                    rows = await (
                        await conn.execute(
                            "SELECT c.accession,c.item,c.ordinal,c.text,c.tsv::text AS tsv "
                            "FROM chunks c JOIN corpus_chunks cc ON cc.chunk_id=c.id "
                            "JOIN companies co ON co.cik=c.cik WHERE " + " AND ".join(where),
                            params,
                        )
                    ).fetchall()
                    eligible.append(Counter((*identity(row), row["tsv"]) for row in rows))
                assert eligible[0] == eligible[1], qid
                detail["eligible_passages_identical_including_tsv"] = True
                detail["eligible_chunks"] = sum(eligible[0].values())
                detail["vector_identical_by_text"] = [
                    row["text"] for row in versions[0]["vector"]
                ] == [row["text"] for row in versions[1]["vector"]]
                if not detail["vector_identical_by_text"]:
                    output["exceptions"].append({"id": qid, "reason": "vector text order differs"})
                old, new = (v["keyword"] for v in versions)
                old_map = {identity(row): (rank, row) for rank, row in enumerate(old, 1)}
                new_map = {identity(row): (rank, row) for rank, row in enumerate(new, 1)}
                assert len(old_map) == len(old) and len(new_map) == len(new)
                shared = old_map.keys() & new_map.keys()
                assert all(old_map[k][1]["score_hex"] == new_map[k][1]["score_hex"] for k in shared)
                inversions = []
                for a in shared:
                    for b in shared:
                        if old_map[a][0] < old_map[b][0] and new_map[a][0] > new_map[b][0]:
                            inversions.append((a, b))
                bad_inversions = [
                    (a, b)
                    for a, b in inversions
                    if old_map[a][1]["score_hex"] != old_map[b][1]["score_hex"]
                ]
                leaving = old_map.keys() - new_map.keys()
                entering = new_map.keys() - old_map.keys()
                boundary_ok = not (leaving or entering) or (
                    len(leaving) == len(entering)
                    and old[-1]["score_hex"] == new[-1]["score_hex"]
                    and all(old_map[k][1]["score_hex"] == old[-1]["score_hex"] for k in leaving)
                    and all(new_map[k][1]["score_hex"] == new[-1]["score_hex"] for k in entering)
                )
                moves = []
                for key in old_map.keys() | new_map.keys():
                    before_rank = old_map[key][0] if key in old_map else None
                    after_rank = new_map[key][0] if key in new_map else None
                    if before_rank == after_rank:
                        continue
                    reference = old_map[key][1] if key in old_map else new_map[key][1]
                    # Include every intervening neighbor in each archived list.
                    lo, hi = sorted((before_rank or 31, after_rank or 31))
                    neighbors = old[lo - 1 : hi] + new[lo - 1 : hi]
                    exact_neighbors = all(
                        row["score_hex"] == reference["score_hex"] for row in neighbors
                    )
                    moves.append(
                        {
                            "accession": reference["accession"],
                            "item": reference["item"],
                            "ordinal": reference["ordinal"],
                            "text_sha256": hashlib.sha256(reference["text"].encode()).hexdigest(),
                            "v1_rank": before_rank,
                            "v2_rank": after_rank,
                            "score": reference["score"],
                            "score_hex": reference["score_hex"],
                            "all_crossed_neighbors_exactly_tied": exact_neighbors,
                        }
                    )
                detail.update(
                    {
                        "keyword_different_text_slots": sum(
                            a["text"] != b["text"] for a, b in zip(old, new, strict=True)
                        ),
                        "keyword_moves": moves,
                        "inverted_pairs": len(inversions),
                        "non_tied_inverted_pairs": len(bad_inversions),
                        "leaving_top30": len(leaving),
                        "entering_top30": len(entering),
                        "boundary_exact_ties": boundary_ok,
                        "fully_explained": not bad_inversions
                        and boundary_ok
                        and all(m["all_crossed_neighbors_exactly_tied"] for m in moves),
                    }
                )
                if not detail["fully_explained"]:
                    output["exceptions"].append(
                        {"id": qid, "reason": "keyword movement not fully tied"}
                    )
            output["per_question"].append(detail)
        # Transaction remains read-only until the connection is returned.
    after = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in protected}
    assert before == after
    output["preservation_sha256"] = after
    for index, version in enumerate(["v1", "v2"]):
        output["keyword_ties_overall"][version] = {
            "tied_slots": tie_slots[index],
            "total_slots": total_slots[index],
            "fraction": tie_slots[index] / total_slots[index],
        }
    subset = [d for d in output["per_question"] if d["checked_unchanged_scope"]]
    output["summary"] = {
        "questions_checked": len(subset),
        "keyword_changed_questions": sum(d["keyword_different_text_slots"] > 0 for d in subset),
        "different_text_slots": sum(d["keyword_different_text_slots"] for d in subset),
        "moved_passages_including_boundary": sum(len(d["keyword_moves"]) for d in subset),
        "fully_tied_moves": sum(
            m["all_crossed_neighbors_exactly_tied"] for d in subset for m in d["keyword_moves"]
        ),
        "inverted_pairs": sum(d["inverted_pairs"] for d in subset),
        "entering_top30": sum(d["entering_top30"] for d in subset),
        "leaving_top30": sum(d["leaving_top30"] for d in subset),
        "vector_identical_questions": sum(d["vector_identical_by_text"] for d in subset),
        "exceptions": len(output["exceptions"]),
    }
    Path("docs/CORPUS_V2_TIE_VERIFICATION.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "summary": output["summary"],
                "ties": output["keyword_ties_overall"],
                "exceptions": output["exceptions"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        runner.run(main())
