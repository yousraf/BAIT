#!/usr/bin/env python3
"""Score aligned predictions against the BAIT gold standard.

    python scripts/score.py --gold data/bait_annotations.jsonl predictions/*.jsonl

Writes to --out (default results/):
  table_main.csv        corpus-level scores per (model, k), mean over runs (paper Table 1)
  table_seed_sd.csv     standard deviation over runs
  per_bias_corpus.csv   per-bias Task 1 F1 and Task 2 trigger-F1, mean over runs
  per_document.csv      per-article scores, averaged over runs (used by the tests)
  tests_vs_zeroshot.csv paired t-tests of each k > 0 against k = 0 over articles,
                        95% CI, Holm correction within each task

Corpus-level scores pool TP/FP/FN over all articles and biases within one run.
Per-article scores give 1 to an article with no gold trigger for which the
model also predicts none.
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as tdist
from scipy.stats import ttest_rel

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bait import (BIAS_CODES, accumulate_span_counts, doc_level_metrics,  # noqa: E402
                  load_documents, span_metrics)

TASK1 = ["doc_f1", "exact_set"]
TASK2 = ["char_f1", "span_f1", "trigger_f1"]


def holm(p):
    p = np.asarray(p, float)
    adj = np.full(len(p), np.nan)
    ok = np.where(~np.isnan(p))[0]
    prev = 0.0
    for rank, i in enumerate(ok[np.argsort(p[ok])]):
        prev = adj[i] = min(1.0, max(prev, (len(ok) - rank) * p[i]))
    return adj


def paired(x, y):
    d = np.asarray(x, float) - np.asarray(y, float)
    n, m, sd = len(d), d.mean(), d.std(ddof=1)
    if n < 3 or sd == 0:
        return m, m, m, np.nan, np.nan
    h = tdist.ppf(.975, n - 1) * sd / np.sqrt(n)
    tt = ttest_rel(x, y)
    return m, m - h, m + h, tt.statistic, tt.pvalue


def corpus_level(preds, docs):
    by = defaultdict(list)
    for p in preds:
        by[(p["model"], p["k"], p["seed"])].append(p)
    rows, brows = [], []
    for (m, k, s), items in by.items():
        dm = doc_level_metrics([(docs[p["doc_id"]].gold_biases, set(p["pred_biases"])) for p in items])
        counts = {}
        for p in items:
            accumulate_span_counts(docs[p["doc_id"]], p["triggers"], counts)
        sm = span_metrics(counts)
        rows.append({"model": m, "k": k, "seed": s, "micro_f1": dm["micro_f1"], "macro_f1": dm["macro_f1"],
                     "subset_acc": dm["subset_accuracy"], "char_f1": sm["micro"]["char"]["f1"],
                     "span_f1": sm["micro"]["span"]["f1"], "trigger_f1": sm["micro"]["trigger"]["f1"]})
        for b in BIAS_CODES:
            brows.append({"model": m, "k": k, "seed": s, "bias": b, "t1_f1": dm["per_bias"][b]["f1"],
                          "t2_trigger_f1": sm["per_bias"][b]["trigger"]["f1"]})
    ov = pd.DataFrame(rows).drop(columns="seed")
    pb = pd.DataFrame(brows).drop(columns="seed")
    return (ov.groupby(["model", "k"]).mean(), ov.groupby(["model", "k"]).std(ddof=1),
            pb.groupby(["model", "k", "bias"]).mean())


def per_document(preds, docs):
    rows = []
    for p in preds:
        d = docs[p["doc_id"]]
        gold, pred = d.gold_biases, set(p["pred_biases"])
        dm = doc_level_metrics([(gold, pred)])
        counts = {}
        accumulate_span_counts(d, p["triggers"], counts)
        sm = span_metrics(counts)
        e1 = not gold and not pred
        e2 = not d.gold_triggers and not p["triggers"]
        rows.append({"model": p["model"], "k": p["k"], "doc_id": p["doc_id"],
                     "doc_f1": 1.0 if e1 else dm["micro_f1"], "exact_set": float(dm["subset_accuracy"]),
                     "char_f1": 1.0 if e2 else sm["micro"]["char"]["f1"],
                     "span_f1": 1.0 if e2 else sm["micro"]["span"]["f1"],
                     "trigger_f1": 1.0 if e2 else sm["micro"]["trigger"]["f1"]})
    return pd.DataFrame(rows).groupby(["model", "k", "doc_id"], as_index=False).mean()


def tests_vs_zeroshot(pdoc):
    rows = []
    doc_ids = sorted(pdoc.doc_id.unique())
    vec = lambda m, k, c: pdoc[(pdoc.model == m) & (pdoc.k == k)].set_index("doc_id").loc[doc_ids, c].values
    for task, mets in (("task1", TASK1), ("task2", TASK2)):
        for met in mets:
            for m in sorted(pdoc.model.unique()):
                ks = sorted(pdoc[pdoc.model == m].k.unique())
                if 0 not in ks:
                    continue
                for k in [k for k in ks if k > 0]:
                    d, lo, hi, t, p = paired(vec(m, k, met), vec(m, 0, met))
                    rows.append({"task": task, "metric": met, "model": m, "k": k, "delta": d,
                                 "ci_lo": lo, "ci_hi": hi, "t": t, "p": p})
    res = pd.DataFrame(rows)
    if len(res):
        res["p_holm"] = res.groupby("task")["p"].transform(lambda s: pd.Series(holm(s.values), index=s.index))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("predictions", nargs="+")
    ap.add_argument("--gold", default="data/bait_annotations.jsonl")
    ap.add_argument("--out", default="results")
    args = ap.parse_args()

    docs = {d.doc_id: d for d in load_documents(args.gold)}
    preds = [json.loads(l) for f in args.predictions for l in open(f, encoding="utf-8")]
    missing = {p["doc_id"] for p in preds} - set(docs)
    if missing:
        sys.exit(f"predictions for unknown doc_ids: {sorted(missing)}")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    mean, sd, pb = corpus_level(preds, docs)
    pdoc = per_document(preds, docs)
    tests = tests_vs_zeroshot(pdoc)
    mean.round(4).to_csv(out / "table_main.csv")
    sd.round(4).to_csv(out / "table_seed_sd.csv")
    pb.round(4).to_csv(out / "per_bias_corpus.csv")
    pdoc.to_csv(out / "per_document.csv", index=False)
    tests.to_csv(out / "tests_vs_zeroshot.csv", index=False)

    pd.set_option("display.width", 200)
    print("Corpus-level scores, mean over runs:\n")
    print(mean.round(3).to_string())
    print(f"\nwrote {', '.join(sorted(p.name for p in out.iterdir()))} to {out}/")


if __name__ == "__main__":
    main()
