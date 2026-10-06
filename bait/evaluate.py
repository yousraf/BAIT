"""Metrics for the two BAIT tasks.

Task 1 - document-level bias trigger detection (multilabel over B01-B09):
  per-bias P/R/F1, micro-F1, macro-F1, subset (exact-set) accuracy.

Task 2 - trigger span detection, three granularities:
  * char-level: per-bias character masks, micro P/R/F1 summed over docs.
    Unlocated predicted spans add their length to FP.
  * span-level: greedy one-to-one matching of predicted to gold spans of the
    same bias, match iff character IoU >= 0.5.
  * trigger-level (grouping): greedy one-to-one matching of predicted to gold
    triggers of the same bias; similarity = char-overlap F1 between the unions
    of their spans, match iff >= 0.5.

Predicted spans are dicts with "start"/"end" (start < 0 = unlocated). The length
of an unlocated span is read from "length" if present, else from "text".
Documents whose output could not be parsed are scored as empty predictions.
"""
from __future__ import annotations

from dataclasses import dataclass

from .data import BIAS_CODES, Document


def prf(tp: float, fp: float, fn: float) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


# ---------------------------------------------------------------- task 1 --

def doc_level_metrics(rows: list[tuple[set[str], set[str]]]) -> dict:
    """rows: [(gold_biases, pred_biases)] per document."""
    per = {b: {"tp": 0, "fp": 0, "fn": 0} for b in BIAS_CODES}
    exact = 0
    for gold, pred in rows:
        if gold == pred:
            exact += 1
        for b in BIAS_CODES:
            g, p = b in gold, b in pred
            per[b]["tp"] += g and p
            per[b]["fp"] += (not g) and p
            per[b]["fn"] += g and (not p)
    out = {"per_bias": {}, "n_docs": len(rows), "subset_accuracy": exact / len(rows) if rows else 0.0}
    tps = fps = fns = 0
    fs = []
    for b in BIAS_CODES:
        c = per[b]
        p, r, f = prf(c["tp"], c["fp"], c["fn"])
        out["per_bias"][b] = {"p": p, "r": r, "f1": f, "support": c["tp"] + c["fn"]}
        tps += c["tp"]; fps += c["fp"]; fns += c["fn"]
        fs.append(f)
    out["micro_p"], out["micro_r"], out["micro_f1"] = prf(tps, fps, fns)
    out["macro_f1"] = sum(fs) / len(fs)
    return out


# ---------------------------------------------------------------- task 2 --

def _unloc_len(sp: dict) -> int:
    return sp["length"] if "length" in sp else len(sp.get("text", ""))


def _mask_intervals(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge intervals; ignore invalid ones."""
    ivs = sorted((s, e) for s, e in spans if 0 <= s < e)
    merged: list[tuple[int, int]] = []
    for s, e in ivs:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    return merged


def _overlap(a: list[tuple[int, int]], b: list[tuple[int, int]]) -> int:
    total = 0
    i = j = 0
    while i < len(a) and j < len(b):
        s = max(a[i][0], b[j][0])
        e = min(a[i][1], b[j][1])
        if s < e:
            total += e - s
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return total


def _length(ivs: list[tuple[int, int]]) -> int:
    return sum(e - s for s, e in ivs)


@dataclass
class SpanCounts:
    char_tp: float = 0.0
    char_fp: float = 0.0
    char_fn: float = 0.0
    span_tp: int = 0
    span_fp: int = 0
    span_fn: int = 0
    trig_tp: int = 0
    trig_fp: int = 0
    trig_fn: int = 0


def _iou(a: tuple[int, int], b: tuple[int, int]) -> float:
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    union = (a[1] - a[0]) + (b[1] - b[0]) - inter
    return inter / union if union else 0.0


def _greedy_match(pairs: list[tuple[float, int, int]], threshold: float) -> int:
    """pairs: (score, pred_idx, gold_idx). One-to-one greedy by score desc."""
    used_p: set[int] = set()
    used_g: set[int] = set()
    tp = 0
    for score, pi, gi in sorted(pairs, key=lambda x: -x[0]):
        if score < threshold:
            break
        if pi in used_p or gi in used_g:
            continue
        used_p.add(pi)
        used_g.add(gi)
        tp += 1
    return tp


def accumulate_span_counts(doc: Document, aligned_triggers: list[dict],
                           counts: dict[str, SpanCounts], iou_threshold: float = 0.5,
                           trigger_threshold: float = 0.5) -> None:
    """Add one document's contribution to per-bias SpanCounts."""
    for b in BIAS_CODES:
        c = counts.setdefault(b, SpanCounts())
        gold_trigs = [t for t in doc.gold_triggers if t.bias == b]
        pred_trigs = [t for t in aligned_triggers if t["bias"] == b]

        gold_spans = [(s.start, s.end) for t in gold_trigs for s in t.spans]
        pred_spans_all = [(sp["start"], sp["end"]) for t in pred_trigs for sp in t["spans"]]
        pred_valid = [(s, e) for s, e in pred_spans_all if s >= 0 and e > s]
        unmatched = [sp for t in pred_trigs for sp in t["spans"] if sp["start"] < 0]
        unmatched_len = sum(_unloc_len(sp) for sp in unmatched)

        # char-level
        gmask = _mask_intervals(gold_spans)
        pmask = _mask_intervals(pred_valid)
        inter = _overlap(gmask, pmask)
        c.char_tp += inter
        c.char_fp += _length(pmask) - inter + unmatched_len
        c.char_fn += _length(gmask) - inter

        # span-level (IoU >= threshold, one-to-one)
        pairs = [(_iou(p, g), pi, gi)
                 for pi, p in enumerate(pred_valid)
                 for gi, g in enumerate(gold_spans)]
        tp = _greedy_match(pairs, iou_threshold)
        c.span_tp += tp
        c.span_fp += len(pred_valid) + len(unmatched) - tp
        c.span_fn += len(gold_spans) - tp

        # trigger-level: similarity = char-overlap F1 between span unions
        tpairs = []
        for pi, pt in enumerate(pred_trigs):
            pmask_t = _mask_intervals([(sp["start"], sp["end"]) for sp in pt["spans"]
                                       if sp["start"] >= 0])
            plen = _length(pmask_t) + sum(_unloc_len(sp) for sp in pt["spans"] if sp["start"] < 0)
            for gi, gt in enumerate(gold_trigs):
                gmask_t = _mask_intervals([(s.start, s.end) for s in gt.spans])
                inter_t = _overlap(pmask_t, gmask_t)
                _, _, f_ = prf(inter_t, plen - inter_t, _length(gmask_t) - inter_t)
                tpairs.append((f_, pi, gi))
        ttp = _greedy_match(tpairs, trigger_threshold)
        c.trig_tp += ttp
        c.trig_fp += len(pred_trigs) - ttp
        c.trig_fn += len(gold_trigs) - ttp


def span_metrics(counts: dict[str, SpanCounts]) -> dict:
    out = {"per_bias": {}}
    agg = SpanCounts()
    for b in BIAS_CODES:
        c = counts.get(b, SpanCounts())
        cp, cr, cf = prf(c.char_tp, c.char_fp, c.char_fn)
        sp, sr, sf = prf(c.span_tp, c.span_fp, c.span_fn)
        tp_, tr_, tf_ = prf(c.trig_tp, c.trig_fp, c.trig_fn)
        out["per_bias"][b] = {
            "char": {"p": cp, "r": cr, "f1": cf},
            "span": {"p": sp, "r": sr, "f1": sf, "support": c.span_tp + c.span_fn},
            "trigger": {"p": tp_, "r": tr_, "f1": tf_, "support": c.trig_tp + c.trig_fn},
        }
        for k in ("char_tp", "char_fp", "char_fn", "span_tp", "span_fp", "span_fn",
                  "trig_tp", "trig_fp", "trig_fn"):
            setattr(agg, k, getattr(agg, k) + getattr(c, k))
    cp, cr, cf = prf(agg.char_tp, agg.char_fp, agg.char_fn)
    sp, sr, sf = prf(agg.span_tp, agg.span_fp, agg.span_fn)
    tp_, tr_, tf_ = prf(agg.trig_tp, agg.trig_fp, agg.trig_fn)
    out["micro"] = {
        "char": {"p": cp, "r": cr, "f1": cf},
        "span": {"p": sp, "r": sr, "f1": sf},
        "trigger": {"p": tp_, "r": tr_, "f1": tf_},
    }
    out["macro_f1"] = {
        k: sum(v[k]["f1"] for v in out["per_bias"].values()) / len(BIAS_CODES)
        for k in ("char", "span", "trigger")
    }
    return out
