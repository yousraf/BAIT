"""Load the BAIT gold standard.

Works on either file:
  data/bait_annotations.jsonl  (released, offsets only)  -> enough for scoring
  bait_full.jsonl              (after scripts/rehydrate.py) -> adds article and span text,
                                                              needed for alignment and prompting
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

BIAS_CODES = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B09"]
BIAS_NAMES = {
    "B01": "Illusory Truth",
    "B02": "Negativity Bias",
    "B03": "Bandwagon Effect",
    "B04": "Authority Bias",
    "B05": "Stereotyping",
    "B06": "Declinism",
    "B07": "Identifiable Victim Effect",
    "B08": "Illusory Correlation",
    "B09": "Hindsight Bias",
}
_CODE_RE = re.compile(r"\bB0[1-9]\b")


def bias_code(label: str) -> str | None:
    """Extract 'B01'..'B09' from strings like 'B01 Illusory Truth'."""
    m = _CODE_RE.search(label or "")
    return m.group(0) if m else None


@dataclass
class Span:
    start: int
    end: int
    text: str = ""  # empty when loaded from the text-free release


@dataclass
class Trigger:
    trigger_id: str
    bias: str
    spans: list[Span]


@dataclass
class Document:
    doc_id: int
    article_id: str
    text: str
    split: str
    gold_biases: set[str]
    gold_triggers: list[Trigger]
    warnings: list[str] = field(default_factory=list)

    def gold_spans_by_bias(self) -> dict[str, list[tuple[int, int]]]:
        out: dict[str, list[tuple[int, int]]] = {}
        for t in self.gold_triggers:
            out.setdefault(t.bias, []).extend((s.start, s.end) for s in t.spans)
        return out


def load_documents(path: str) -> list[Document]:
    docs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            text = r.get("text", "")
            docs.append(Document(
                doc_id=r["doc_id"],
                article_id=str(r["article_id"]),
                text=text,
                split=r.get("split", ""),
                gold_biases=set(r["biases_present"]),
                gold_triggers=[
                    Trigger(t["trigger_id"], t["bias"],
                            [Span(s["start"], s["end"], s.get("text", text[s["start"]:s["end"]]))
                             for s in t["spans"]])
                    for t in r["triggers"]
                ],
            ))
    docs.sort(key=lambda d: d.doc_id)
    return docs


def gold_output_json(doc: Document) -> str:
    """A document's gold annotation in the output format the prompt asks for
    (used for few-shot examples; needs the rehydrated file)."""
    obj = {
        "biases_present": sorted({t.bias for t in doc.gold_triggers}) or ["NONE"],
        "triggers": [
            {
                "trigger_id": t.trigger_id,
                "bias": t.bias,
                "spans": [s.text for s in t.spans],
                "rationale": f"These span(s) jointly trigger {t.bias} {BIAS_NAMES[t.bias]}.",
            }
            for t in doc.gold_triggers
        ],
    }
    return json.dumps(obj, ensure_ascii=False, indent=2)
