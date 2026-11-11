"""Question generation (D083-D086, D097, D101), offline on synthetic facts (test data only)."""

import json
import os
from decimal import Decimal

import pytest

from evals import generate as g
from evals.generate import Fact


@pytest.fixture(autouse=True)
def test_company_names(monkeypatch):
    for ticker in ("AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH"):
        monkeypatch.setitem(g.NAMES, ticker, f"Company {ticker}")
        monkeypatch.setitem(g.SECTORS, ticker, "Test sector")


def fact(
    fid,
    ticker="AAA",
    metric="revenue",
    fy=2025,
    fp="Q1",
    value="100",
    ptype="quarter",
    derived=False,
    inputs=(),
    first_value=None,
    first_filed="2025-05-01",
    end="2025-03-31",
    unit="USD",
    accession="0000000000-25-000001",
):
    return Fact(
        fact_id=str(fid),
        ticker=ticker,
        cik="1",
        metric=metric,
        concept="Revenues",
        period_type=ptype,
        start=None if ptype == "instant" else "2025-01-01",
        end=end,
        fiscal_year=fy,
        fiscal_period=fp,
        value=Decimal(value),
        unit=unit,
        derived=derived,
        accession=accession,
        filed=first_filed,
        url=f"https://www.sec.gov/{fid}",
        inputs=tuple(inputs),
        first_value=Decimal(first_value)
        if first_value is not None
        else (None if derived else Decimal(value)),
        first_filed=None if derived else first_filed,
    )


def derived_q4(
    fid,
    ticker="AAA",
    metric="revenue",
    fy=2025,
    value="40",
    fy_value="160",
    nine_value="120",
    fy_first=None,
    fy_acc="A2",
    nine_acc="A1",
    fy_filed="2025-08-01",
    nine_filed="2025-05-01",
):
    inputs = (
        {
            "coefficient": 1,
            "value": fy_value,
            "concept": "Revenues",
            "start": "2024-04-01",
            "end": "2025-03-31",
            "accession": fy_acc,
            "filed": fy_filed,
            "first_value": fy_first or fy_value,
            "first_filed": fy_filed,
        },
        {
            "coefficient": -1,
            "value": nine_value,
            "concept": "Revenues",
            "start": "2024-04-01",
            "end": "2024-12-31",
            "accession": nine_acc,
            "filed": nine_filed,
            "first_value": nine_value,
            "first_filed": nine_filed,
        },
    )
    return fact(fid, ticker, metric, fy, "Q4", value, derived=True, inputs=inputs)


def by_template(facts):
    return g.candidates(facts)


def test_gold_values_are_recomputed_with_decimal_per_template():
    facts = [
        fact(1, fp="Q1", value="100"),
        fact(2, fp="Q2", value="110"),
        fact(3, fp="Q3", value="130"),
        derived_q4(4, value="160", fy_value="500", nine_value="340"),
        fact(5, metric="gross_profit", fp="Q1", value="40"),
        fact(6, fp="FY", ptype="annual", value="500", fy=2025),
        fact(7, fp="FY", ptype="annual", value="400", fy=2024),
        fact(8, metric="eps_diluted", fp="Q1", value="0.27", unit="USD/shares"),
    ]
    pools = by_template(facts)
    margin = next(c for c in pools["margin"] if c.metric == "gross_margin")
    assert g.fixed(margin.gold, True) == "40"  # 40 / 100 * 100
    growth = next(c for c in pools["yoy_growth"] if c.metric == "revenue")
    assert g.fixed(growth.gold, True) == "25"  # (500 - 400) / 400 * 100
    trend = next(c for c in pools["trend_avg"] if c.metric == "revenue")
    assert g.fixed(trend.gold, False) == "125"  # (100 + 110 + 130 + 160) / 4
    q4 = next(c for c in pools["derived_q4"])
    assert q4.gold == Decimal("160") and q4.facts[0].derived
    multi = next(c for c in pools["multi_step"])
    assert g.fixed(multi.gold, True) == "60"  # (160 - 100) / 100 * 100
    lookups = {(c.metric, c.periods): c for c in pools["lookup"]}
    assert lookups[("eps_diluted", ((2025, "Q1"),))].unit == "USD/shares"
    assert lookups[("revenue", ((2025, "Q1"),))].gold == Decimal("100")
    assert all(not c.facts[0].derived for c in pools["lookup"])
    assert g.tolerance("USD/shares") == {"kind": "eps", "relative": "0.005", "absolute": "0.005"}
    assert "fiscal Q2 2025" in next(
        c.question for c in pools["lookup"] if c.periods == ((2025, "Q2"),)
    )


def test_comparison_records_choice_and_skips_close_pairs():
    facts = [
        fact(1, "AAA", "revenue", 2025, "FY", "1000", "annual"),
        fact(2, "AAA", "net_income", 2025, "FY", "100", "annual"),  # 10%
        fact(3, "BBB", "revenue", 2025, "FY", "1000", "annual"),
        fact(4, "BBB", "net_income", 2025, "FY", "150", "annual"),  # 15%
        fact(5, "CCC", "revenue", 2025, "FY", "1000", "annual"),
        fact(6, "CCC", "net_income", 2025, "FY", "101", "annual"),  # 10.1%: too close to AAA
    ]
    pairs = {frozenset(c.companies): c for c in by_template(facts)["comparison"]}
    ab = pairs[frozenset({"AAA", "BBB"})]
    assert ab.gold == Decimal(5) and ab.gold_choice == "BBB" and ab.unit == "percentage_points"
    assert frozenset({"AAA", "CCC"}) not in pairs  # |10.0 - 10.1| < 0.2 pp


def annual_margin(fid, ticker, net, fy=2025):
    """Revenue 1000 and the given net income: a net margin of net / 10 percent."""
    return [
        fact(fid, ticker, "revenue", fy, "FY", "1000", "annual"),
        fact(fid + 1, ticker, "net_income", fy, "FY", net, "annual"),
    ]


def comparison_pairs(facts):
    return {frozenset(c.companies) for c in by_template(facts)["comparison"]}


def test_comparison_pairs_only_same_sector_and_never_bank_with_non_bank(monkeypatch):
    monkeypatch.setitem(g.SECTORS, "CCC", "Other sector")
    facts = [
        *annual_margin(1, "AAA", "100"),
        *annual_margin(3, "BBB", "150"),
        *annual_margin(5, "CCC", "200"),
        *annual_margin(7, "JPM", "300"),
        *annual_margin(9, "BAC", "250"),
    ]
    assert comparison_pairs(facts) == {frozenset({"AAA", "BBB"}), frozenset({"JPM", "BAC"})}
    # Even with a sector table that put a non-bank among the banks, no mixed pair is generated.
    monkeypatch.setitem(g.SECTORS, "AAA", "Financials")
    pairs = comparison_pairs(facts)
    assert frozenset({"JPM", "BAC"}) in pairs
    assert not any(len(p & set(g.BANKS)) == 1 for p in pairs)


def test_comparison_selection_fills_sectors_evenly(monkeypatch):
    monkeypatch.setattr(g, "TARGETS", {"comparison": 7})
    for ticker, sector in [("AAA", "S1"), ("BBB", "S1"), ("CCC", "S1"), ("DDD", "S1")]:
        monkeypatch.setitem(g.SECTORS, ticker, sector)
    for ticker, sector in [("EEE", "S2"), ("FFF", "S2"), ("GGG", "S3"), ("HHH", "S3")]:
        monkeypatch.setitem(g.SECTORS, ticker, sector)
    facts, fid = [], 1
    for fy in (2024, 2025):  # S1: 6 pairs a year
        for i, t in enumerate(("AAA", "BBB", "CCC", "DDD")):
            facts += annual_margin(fid, t, str(100 + 10 * i), fy)
            fid += 2
    for fy in (2023, 2024, 2025):  # S2: 1 pair a year
        for i, t in enumerate(("EEE", "FFF")):
            facts += annual_margin(fid, t, str(100 + 10 * i), fy)
            fid += 2
    for i, t in enumerate(("GGG", "HHH")):  # S3: a single pair
        facts += annual_margin(fid, t, str(100 + 10 * i))
        fid += 2
    chosen = g.select(g.candidates(facts))["comparison"]
    by_sector = {s: sum(g.sector_of(c) == s for c in chosen) for s in ("S1", "S2", "S3")}
    assert by_sector == {"S1": 3, "S2": 3, "S3": 1}  # S3 runs out; S1 and S2 share the rest


def test_sector_table_covers_every_company_and_financials_are_the_banks():
    assert set(g.SECTORS) == set(g.NAMES)
    assert {t for t, s in g.SECTORS.items() if s == "Financials"} == set(g.BANKS)


@pytest.mark.skipif(
    not g.DRAFT_PATH.exists() and not g.FROZEN_PATH.exists(), reason="no question set"
)
def test_question_set_comparisons_are_same_sector():
    path = g.FROZEN_PATH if g.FROZEN_PATH.exists() else g.DRAFT_PATH
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    comparisons = [r for r in records if r["template"] == "comparison"]
    assert comparisons
    for r in comparisons:
        a, b = r["companies"]
        assert g.SECTORS[a] == g.SECTORS[b], r["id"]
        assert (a in g.BANKS) == (b in g.BANKS), r["id"]


def test_skip_rules_banks_bases_eps_and_instants():
    facts = [
        fact(1, "JPM", "net_income", 2025, "Q1", "10"),  # no revenue quarter -> no margin
        fact(2, "AAA", "revenue", 2025, "FY", "0", "annual"),
        fact(3, "AAA", "revenue", 2026, "FY", "5", "annual"),
        fact(4, "AAA", "eps_diluted", 2025, "Q1", "1.0", unit="USD/shares"),
        fact(5, "AAA", "total_assets", 2025, "Q1", "999", "instant"),
    ]
    pools = by_template(facts)
    assert not pools["margin"] and not pools["yoy_growth"]  # missing revenue; zero base
    assert not pools["trend_avg"] and not pools["derived_q4"]
    instant = next(c for c in pools["lookup"] if c.metric == "total_assets")
    assert (
        instant.question.startswith("What were")
        and "at the end of fiscal Q1 2025" in instant.question
    )


def test_mixed_vintage_derivations_are_excluded():
    clean = derived_q4(1, ticker="AAA", fy_acc="A2", nine_acc="A1")
    mixed = derived_q4(2, ticker="BBB", fy_value="170", fy_first="160", value="50")
    assert not clean.mixed_vintage and mixed.mixed_vintage
    pools = by_template([clean, mixed])
    assert {c.companies[0] for c in pools["derived_q4"]} == {"AAA"}


def test_fairness_cutoff_restatement_and_derived_flags():
    restated = fact(1, value="110", first_value="100", first_filed="2026-05-31")
    after = fact(2, fp="Q2", value="120", first_filed="2026-07-01")
    june = fact(3, fp="Q3", value="130", first_filed="2026-06-15")
    pools = by_template([restated, after, june])
    by_fid = {c.facts[0].fact_id: g.fairness(c) for c in pools["lookup"]}
    assert by_fid["1"]["restated"] is True
    assert by_fid["1"]["restated_detail"]["gold_as_first_reported"] == "100"
    assert by_fid["1"]["cutoff_bucket"]["claude-sonnet-5-5"] == "before"
    assert by_fid["2"]["cutoff_bucket"]["claude-opus-5-5"] == "after"
    assert by_fid["3"]["cutoff_bucket"]["claude-sonnet-5-5"] == "june"
    q4 = derived_q4(4, fy_filed="2026-08-01", nine_filed="2026-05-01")
    f = g.fairness(by_template([q4])["derived_q4"][0])
    assert f["derived_q4"] and f["first_filed_max"] == "2026-08-01" and f["restated"] is False


def test_selection_split_and_sample_are_deterministic_and_stratified(monkeypatch):
    monkeypatch.setattr(g, "TARGETS", {"lookup": 20})
    facts = [
        fact(
            i,
            ticker=t,
            fp=fp,
            fy=fy,
            value=str(100 + i),
            first_filed="2026-08-01" if i % 7 == 0 else "2025-05-01",
        )
        for i, (t, fp, fy) in enumerate(
            (t, fp, fy)
            for t in ("AAA", "BBB", "CCC")
            for fy in (2024, 2025)
            for fp in ("Q1", "Q2", "Q3", "Q4")
        )
    ]
    first = g.build(facts)
    second = g.build(facts)
    assert g.dumps(first) == g.dumps(second)  # identical output for a fixed seed
    questions = [r for r in first if r["split"] != "probe"]
    assert len(questions) == 20 and sum(r["split"] == "dev" for r in questions) == 6  # 30%
    assert (
        sum(r["fairness"]["cutoff_bucket"]["claude-sonnet-5-5"] == "after" for r in questions) >= 4
    )
    companies = [t for r in questions for t in r["companies"]]
    assert (
        max(companies.count(t) for t in "AAA BBB CCC".split())
        - min(companies.count(t) for t in "AAA BBB CCC".split())
        <= 1
    )  # balanced
    assert all(r["split"] == "test" for r in questions if r["sample_100"])


def test_freeze_writes_manifest_and_refuses_to_overwrite(tmp_path, monkeypatch):
    draft = tmp_path / "draft.jsonl"
    records = g.build([fact(1), fact(2, fp="Q2")])
    g.write_draft(records, draft)
    monkeypatch.setattr(g, "B2_META_PATH", tmp_path / "missing.jsonl")
    info = g.freeze(draft, tmp_path / "q.jsonl", tmp_path / "m.json")
    assert info["sha256"] == g.sha256_file(tmp_path / "q.jsonl") and info["seed"] == g.SEED
    with pytest.raises(FileExistsError):
        g.freeze(draft, tmp_path / "q.jsonl", tmp_path / "m.json")
    assert g.load_frozen(tmp_path / "q.jsonl", tmp_path / "m.json") == records
    (tmp_path / "q.jsonl").write_text(g.dumps(records[:-1]), encoding="utf-8")
    with pytest.raises(ValueError, match="frozen manifest hash"):
        g.load_frozen(tmp_path / "q.jsonl", tmp_path / "m.json")


@pytest.mark.skipif(not g.FROZEN_PATH.exists(), reason="question set not frozen yet")
def test_frozen_question_set_matches_its_manifest():
    assert g.load_frozen()  # raises on any hash mismatch (D084)


@pytest.mark.integration
@pytest.mark.skipif(os.environ.get("FILINGLENS_TEST_DB") != "1", reason="Set FILINGLENS_TEST_DB=1")
@pytest.mark.skipif(
    not g.DRAFT_PATH.exists() and not g.FROZEN_PATH.exists(), reason="no question set"
)
def test_every_gold_matches_financial_facts_independently():
    """Recompute each gold from the stored facts named in its record, by template formula."""
    import psycopg

    from filinglens.config import Settings
    from filinglens.db import connection_options

    path = g.FROZEN_PATH if g.FROZEN_PATH.exists() else g.DRAFT_PATH
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    url = Settings().database_url
    with psycopg.connect(url, **connection_options(url)) as conn:
        values = {
            str(i): v
            for i, v in conn.execute(
                "SELECT id, value FROM financial_facts WHERE snapshot_id=%s", (g.SNAPSHOT_ID,)
            ).fetchall()
        }
    for r in records:
        if r["template"] == "abstention_probe":
            assert r["gold_value"] is None and r["gold_status"] in ("not_applicable", "unavailable")
            continue
        v = [values[f] for f in r["gold_fact_ids"]]
        t = r["template"]
        if t in ("lookup", "derived_q4"):
            expected = v[0]
        elif t in ("yoy_growth", "multi_step"):
            expected = g.growth(v[1], v[0])
        elif t == "margin":
            expected = g.pct(v[0], v[1])
        elif t == "trend_avg":
            expected = g.mean(v)
        else:
            expected = abs(g.pct(v[0], v[1]) - g.pct(v[2], v[3]))
        ratio = r["gold_unit"] in ("percent", "percentage_points")
        assert g.fixed(expected, ratio) == r["gold_value"], r["id"]
        for item in r["computation"]["inputs"]:
            assert Decimal(item["value"]) == values[item["fact_id"]]
