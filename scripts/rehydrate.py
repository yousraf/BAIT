#!/usr/bin/env python3
"""Rebuild the full BAIT dataset from the text-free annotations and the
SemEval-2023 Task 3 English articles (obtain them from the task organisers).

Usage:
    python rehydrate.py --semeval-dir /path/to/semeval2023task3/data/en \
                        --annotations bait_annotations.jsonl \
                        --out bait_full.jsonl

The script searches --semeval-dir recursively for files named
article<article_id>.txt, checks each text against the stored length and
SHA-256, and adds the article text and every span's surface text.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def candidates(raw: str):
    """Yield the raw text plus light normalisations (line endings, BOM,
    trailing whitespace), in case the local copy differs only cosmetically."""
    seen = set()
    base = [raw, raw.lstrip("﻿")]
    for b in base:
        for t in (b, b.replace("\r\n", "\n")):
            for v in (t, t.rstrip("\n"), t.rstrip("\n") + "\n", t.rstrip("\n") + "\n\n"):
                if v not in seen:
                    seen.add(v)
                    yield v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--semeval-dir", required=True)
    ap.add_argument("--annotations", default="bait_annotations.jsonl")
    ap.add_argument("--out", default="bait_full.jsonl")
    args = ap.parse_args()

    index = {p.name: p for p in Path(args.semeval_dir).rglob("article*.txt")}
    n_ok, problems = 0, []
    with open(args.annotations, encoding="utf-8") as fin, \
         open(args.out, "w", encoding="utf-8") as fout:
        for line in fin:
            rec = json.loads(line)
            path = index.get(f"article{rec['article_id']}.txt")
            if path is None:
                problems.append(f"{rec['article_id']}: article file not found")
                continue
            raw = path.read_text(encoding="utf-8")
            text = next((c for c in candidates(raw) if sha(c) == rec["text_sha256"]), None)
            if text is None:
                problems.append(f"{rec['article_id']}: text does not match stored hash "
                                f"(len {len(raw)} vs {rec['text_length']}); skipped")
                continue
            rec["text"] = text
            for trig in rec["triggers"]:
                for sp in trig["spans"]:
                    sp["text"] = text[sp["start"]:sp["end"]]
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n_ok += 1

    print(f"rehydrated {n_ok} documents -> {args.out}")
    for p in problems:
        print("  WARNING", p, file=sys.stderr)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
