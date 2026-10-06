"""Align predicted span strings (verbatim per the prompt, but often not in
practice) to character offsets in the source article.

Cascade, recording the method used per span:
  1. exact       - exact substring
  2. casefold    - exact after lowercasing (length-preserving guard)
  3. whitespace  - whitespace-flexible regex on the escaped span
  4. fuzzy       - difflib anchor + window ratio >= 0.80
  5. unmatched   - span cannot be located; counted against precision

Occurrence disambiguation: when the SAME string matches at several
positions (typical for B01, where an identical claim repeats), candidates
are ranked by (a) not already consumed by an earlier span of this
prediction, (b) overlapping a gold span of the same bias, (c) leftmost.
Criterion (b) only breaks ties between character-identical matches - the
model committed to the string, not the position - so it cannot reward a
wrong string; without it the aligner's arbitrary pick, not the model, would
be measured. Verified: echoing gold spans scores char-F1 = 1.0.

Alignment statistics per (model, condition) are reported: faithful span
copying is part of what the eval measures.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass

FUZZY_MIN_RATIO = 0.80


@dataclass
class AlignedSpan:
    start: int
    end: int
    method: str
    pred_text: str


def _overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return max(a[0], b[0]) < min(a[1], b[1])


def _pick(cands: list[tuple[int, int]], consumed: list[tuple[int, int]],
          gold: list[tuple[int, int]]) -> tuple[int, int] | None:
    if not cands:
        return None

    def rank(c):
        free = not any(_overlaps(c, x) for x in consumed)
        on_gold = any(_overlaps(c, g) for g in gold)
        return (not free, not on_gold, c[0])  # free first, then on-gold, then leftmost

    return min(cands, key=rank)


def _all_occurrences(hay: str, needle: str) -> list[tuple[int, int]]:
    out = []
    idx = hay.find(needle)
    while idx != -1:
        out.append((idx, idx + len(needle)))
        idx = hay.find(needle, idx + 1)
    return out


def align_span(text: str, low_text: str, pred: str, consumed: list[tuple[int, int]],
               gold: list[tuple[int, int]]) -> AlignedSpan | None:
    # try the raw string first: spans may legitimately include leading or
    # trailing whitespace/newlines that stripping would misalign
    c = _pick(_all_occurrences(text, pred), consumed, gold) if pred else None
    if c:
        return AlignedSpan(c[0], c[1], "exact", pred)
    pred = pred.strip()
    if not pred:
        return None

    c = _pick(_all_occurrences(text, pred), consumed, gold)
    if c:
        return AlignedSpan(c[0], c[1], "exact", pred)

    low = pred.lower()
    if len(low) == len(pred):
        c = _pick(_all_occurrences(low_text, low), consumed, gold)
        if c:
            return AlignedSpan(c[0], c[1], "casefold", pred)

    # whitespace-flexible match (also bridges real newlines vs single spaces)
    tokens = pred.split()
    if tokens:
        pattern = r"\s+".join(re.escape(t) for t in tokens)
        cands = [(m.start(), m.end()) for m in re.finditer(pattern, text)]
        if not cands:
            cands = [(m.start(), m.end()) for m in re.finditer(pattern, text, re.IGNORECASE)]
        c = _pick(cands, consumed, gold)
        if c:
            return AlignedSpan(c[0], c[1], "whitespace", pred)

    # fuzzy: anchor on the longest common block, score a window around it
    sm = difflib.SequenceMatcher(None, text, pred, autojunk=False)
    m = sm.find_longest_match(0, len(text), 0, len(pred))
    if m.size >= max(10, int(0.5 * len(pred))):
        start = max(0, m.a - m.b)
        end = min(len(text), start + len(pred))
        window = text[start:end]
        ratio = difflib.SequenceMatcher(None, window, pred, autojunk=False).ratio()
        if ratio >= FUZZY_MIN_RATIO:
            return AlignedSpan(start, end, "fuzzy", pred)
    return None


def align_prediction(text: str, triggers: list[dict],
                     gold_by_bias: dict[str, list[tuple[int, int]]] | None = None
                     ) -> tuple[list[dict], dict]:
    """Attach offsets to every predicted span.

    gold_by_bias maps bias code -> gold span intervals, used ONLY to break
    ties between character-identical candidate positions.

    Returns (aligned_triggers, stats). aligned_triggers mirrors the input
    triggers with spans as dicts {text, start, end, method}; unmatched spans
    get start=end=-1 and method='unmatched'.
    """
    gold_by_bias = gold_by_bias or {}
    low_text = text.lower() if len(text.lower()) == len(text) else text
    # consumption is tracked PER BIAS: annotations of different biases may
    # legitimately overlap (even coincide), so a span of one bias must not
    # block another bias from its correct position. Within a bias it
    # distributes repeated identical claims (B01) across their occurrences.
    consumed: dict[str, list[tuple[int, int]]] = {}
    stats = {"exact": 0, "casefold": 0, "whitespace": 0, "fuzzy": 0, "unmatched": 0}
    out = []
    for t in triggers:
        gold = gold_by_bias.get(t["bias"], [])
        cons = consumed.setdefault(t["bias"], [])
        aligned = []
        for s in t["spans"]:
            a = align_span(text, low_text, s, cons, gold)
            if a is None:
                stats["unmatched"] += 1
                aligned.append({"text": s, "start": -1, "end": -1, "method": "unmatched"})
            else:
                stats[a.method] += 1
                cons.append((a.start, a.end))
                aligned.append({"text": s, "start": a.start, "end": a.end, "method": a.method})
        out.append({**t, "spans": aligned})
    return out, stats
