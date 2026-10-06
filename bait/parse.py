"""Parse and validate model completions against the prompt's output schema.

Tolerant to common failure modes: markdown fences, preamble text, bias
labels written with names ("B01 Illusory Truth"), trailing commas,
biases_present inconsistent with triggers (reconciled from triggers, per
the prompt rule; the inconsistency is recorded), NONE handling.

Every recoverable deviation is recorded in `issues` so parse robustness can
be reported per model - it is itself an interesting eval signal.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .data import BIAS_CODES, bias_code


@dataclass
class Prediction:
    biases: set[str]                     # document-level predicted biases
    triggers: list[dict]                 # [{trigger_id, bias, spans:[str]}]
    issues: list[str] = field(default_factory=list)
    parse_ok: bool = True                # False => unusable output (treated as NONE)


def _extract_json(text: str) -> str | None:
    """Return the first balanced top-level JSON object in the text."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.M)
    start = text.find("{")
    while start != -1:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            c = text[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        return text[start:i + 1]
        start = text.find("{", start + 1)
    return None


def _loads_lenient(blob: str, issues: list[str]):
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        pass
    fixed = re.sub(r",\s*([}\]])", r"\1", blob)  # trailing commas
    try:
        obj = json.loads(fixed)
        issues.append("trailing commas removed")
        return obj
    except json.JSONDecodeError:
        return None


def parse_completion(text: str) -> Prediction:
    issues: list[str] = []
    blob = _extract_json(text or "")
    if blob is None:
        return Prediction(set(), [], ["no JSON object found"], parse_ok=False)
    if blob.strip() != (text or "").strip():
        issues.append("extra text around JSON")
    obj = _loads_lenient(blob, issues)
    if not isinstance(obj, dict):
        return Prediction(set(), [], issues + ["invalid JSON"], parse_ok=False)

    raw_triggers = obj.get("triggers")
    if not isinstance(raw_triggers, list):
        issues.append("missing/invalid 'triggers'")
        raw_triggers = []

    triggers: list[dict] = []
    for i, t in enumerate(raw_triggers):
        if not isinstance(t, dict):
            issues.append(f"trigger {i} not an object; dropped")
            continue
        code = bias_code(str(t.get("bias", "")))
        if code is None or code not in BIAS_CODES:
            issues.append(f"trigger {i} has invalid bias {t.get('bias')!r}; dropped")
            continue
        spans_raw = t.get("spans")
        if isinstance(spans_raw, str):
            spans_raw = [spans_raw]
            issues.append(f"trigger {i} spans given as string; wrapped")
        if not isinstance(spans_raw, list):
            issues.append(f"trigger {i} has no spans; dropped")
            continue
        spans = [s for s in spans_raw if isinstance(s, str) and s.strip()]
        if len(spans) != len(spans_raw):
            issues.append(f"trigger {i}: non-string/empty spans removed")
        if not spans:
            issues.append(f"trigger {i} has no usable spans; dropped")
            continue
        triggers.append({
            "trigger_id": str(t.get("trigger_id", f"T{len(triggers) + 1}")),
            "bias": code,
            "spans": spans,
        })

    # document-level set
    declared: set[str] = set()
    none_declared = False
    bp = obj.get("biases_present")
    if isinstance(bp, list):
        for b in bp:
            s = str(b)
            if s.upper().startswith("NONE"):
                none_declared = True
                continue
            code = bias_code(s)
            if code:
                declared.add(code)
            else:
                issues.append(f"unparseable biases_present entry {b!r}")
    else:
        issues.append("missing/invalid 'biases_present'")

    from_triggers = {t["bias"] for t in triggers}
    if declared != from_triggers:
        if declared or from_triggers or not none_declared:
            if not (none_declared and not from_triggers):
                issues.append(
                    f"biases_present {sorted(declared)} != trigger biases "
                    f"{sorted(from_triggers)}; union used for the document-level task"
                )
    # Per the prompt rule, biases_present must equal the trigger set; the
    # trigger list is the substantive prediction, so it wins. If the model
    # declared biases but produced no triggers for them, keep the declared
    # set for the document-level task (that task does not require spans).
    biases = from_triggers | declared

    return Prediction(biases=biases, triggers=triggers, issues=issues, parse_ok=True)
