#!/usr/bin/env python3
"""Parse raw model completions and align their spans to the article text.

Input  (--outputs): JSONL, one line per (model, k, seed, doc):
    {"model": "...", "k": 10, "seed": 17, "doc_id": 1, "output": "<raw completion>"}
Gold   (--gold):    bait_full.jsonl from scripts/rehydrate.py (article text needed)
Output (--out):     JSONL in the format of predictions/*.jsonl, ready for score.py.
                    Span strings are dropped unless --keep-text is given.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bait import align_prediction, load_documents, parse_completion  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outputs", required=True)
    ap.add_argument("--gold", default="bait_full.jsonl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--keep-text", action="store_true")
    args = ap.parse_args()

    docs = {d.doc_id: d for d in load_documents(args.gold)}
    if not all(d.text for d in docs.values()):
        sys.exit("--gold has no article text; run scripts/rehydrate.py first")

    n = 0
    with open(args.outputs, encoding="utf-8") as fin, open(args.out, "w", encoding="utf-8") as fout:
        for line in fin:
            r = json.loads(line)
            doc = docs[r["doc_id"]]
            parsed = parse_completion(r["output"])
            aligned, _ = align_prediction(doc.text, parsed.triggers, doc.gold_spans_by_bias())
            for t in aligned:
                for sp in t["spans"]:
                    if sp["start"] < 0:
                        sp["length"] = len(sp["text"])
                    if not args.keep_text:
                        del sp["text"]
            rec = {"model": r["model"], "k": r["k"], "seed": r.get("seed", 0), "doc_id": r["doc_id"],
                   "parse_ok": parsed.parse_ok, "issues": parsed.issues,
                   "pred_biases": sorted(parsed.biases), "triggers": aligned}
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    print(f"aligned {n} outputs -> {args.out}")


if __name__ == "__main__":
    main()
