"""Pinned, project-local model artifacts and explicit CPU model loading."""

import argparse
import json
from functools import lru_cache
from pathlib import Path

from filinglens.config import ROOT

MODEL_DIR = ROOT / "data" / "models"
MODELS = {"embed": "BAAI/bge-small-en-v1.5", "rerank": "BAAI/bge-reranker-base"}
REVISIONS = {
    "embed": "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a",
    "rerank": "2cfc18c9415c912f9d8155881c133215df768a70",
}
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def model_path(kind: str) -> Path:
    lock = MODEL_DIR / "revisions.json"
    if not lock.exists():
        raise RuntimeError("Prepare models first: python -m filinglens.ingest.models")
    entry = json.loads(lock.read_text(encoding="utf-8"))[kind]
    return MODEL_DIR / kind / entry["revision"]


def model_revision(kind: str) -> str:
    return model_path(kind).name


@lru_cache
def tokenizer(kind: str):
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(str(model_path(kind)), local_files_only=True)
    # Oversized text is intentionally tokenized to measure/split it; inference has hard guards.
    tok.deprecation_warnings["sequence-length-is-longer-than-the-specified-maximum"] = True
    return tok


@lru_cache
def embedder():
    import torch
    from sentence_transformers import SentenceTransformer
    from transformers.utils import logging

    logging.disable_progress_bar()
    torch.set_num_threads(4)
    return SentenceTransformer(str(model_path("embed")), device="cpu", local_files_only=True)


@lru_cache
def reranker():
    import torch
    from sentence_transformers import CrossEncoder
    from transformers.utils import logging

    logging.disable_progress_bar()
    torch.set_num_threads(4)
    return CrossEncoder(
        str(model_path("rerank")), device="cpu", max_length=512, local_files_only=True
    )


def prepare() -> None:
    from huggingface_hub import snapshot_download

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = MODEL_DIR / "revisions.json"
    lock = json.loads(lock_path.read_text()) if lock_path.exists() else {}
    for kind, repo in MODELS.items():
        revision = lock.get(kind, {}).get("revision") or REVISIONS[kind]
        # Save the revision before downloading: an interrupted download resumes that revision.
        lock[kind] = {"model": repo, "revision": revision}
        lock_path.write_text(json.dumps(lock, indent=2), encoding="utf-8")
        snapshot_download(
            repo,
            revision=revision,
            local_dir=MODEL_DIR / kind / revision,
            allow_patterns=["*.json", "*.txt", "model.safetensors"],
            ignore_patterns=["onnx/*", "openvino/*"],
        )
        print(f"{kind}: {repo}@{revision}", flush=True)


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    prepare()
