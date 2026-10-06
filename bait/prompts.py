"""Build zero-shot and leave-one-out few-shot prompts from the
bait_fewshot_prompt.md template.

- The system message is the template's "## System prompt" section
  (taxonomy, multi-span rule, output format) and is identical for both
  conditions, so zero-shot vs few-shot isolates the effect of examples.
- Few-shot (leave-one-out): for each target document, k worked examples are
  drawn from the OTHER documents only, deterministically seeded per target.
  At least one selected example contains a multi-span trigger whenever any
  candidate does, so the grouping convention is always demonstrated.
- Zero-shot: the user message is just the target article.
"""

from __future__ import annotations

import hashlib
import random
import re

from .data import Document, gold_output_json

SYSTEM_HEADER = "## System prompt"
FEWSHOT_HEADER = "## Few-shot examples"
TARGET_HEADER = "## Target"


def load_template(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def system_prompt(template: str) -> str:
    body = template.split(SYSTEM_HEADER, 1)[1]
    body = body.split(FEWSHOT_HEADER, 1)[0]
    return body.strip()


def _seed_for(target: Document, seed: int) -> int:
    h = hashlib.sha256(f"{seed}:{target.doc_id}:{target.article_id}".encode()).hexdigest()
    return int(h[:12], 16)


def select_examples(target: Document, pool: list[Document], k: int, seed: int) -> list[Document]:
    """Deterministic leave-one-out selection of k example documents."""
    candidates = [d for d in pool if d.doc_id != target.doc_id]
    rng = random.Random(_seed_for(target, seed))
    multi = [d for d in candidates if any(len(t.spans) > 1 for t in d.gold_triggers)]
    chosen: list[Document] = []
    if multi and k > 0:
        chosen.append(rng.choice(multi))
    remaining = [d for d in candidates if d.doc_id not in {c.doc_id for c in chosen}]
    rng.shuffle(remaining)
    chosen.extend(remaining[: max(0, k - len(chosen))])
    rng.shuffle(chosen)  # do not always lead with the multi-span example
    return chosen


def render_example(idx: int, doc: Document) -> str:
    return (
        f"### Example {idx}\n\n"
        f"ARTICLE:\n{doc.text}\n\n"
        f"OUTPUT:\n{gold_output_json(doc)}"
    )


def user_message(target: Document, examples: list[Document]) -> str:
    parts = []
    if examples:
        parts.append(FEWSHOT_HEADER + "\n")
        parts.extend(render_example(i, d) for i, d in enumerate(examples, 1))
    parts.append(TARGET_HEADER + "\n\nARTICLE:\n" + target.text + "\n\nOUTPUT:")
    return "\n\n".join(parts)


def build_prompt(template: str, target: Document, pool: list[Document],
                 condition: str, k: int, seed: int) -> dict:
    """Return {system, user, example_ids} for one (doc, condition)."""
    if condition == "zeroshot":
        examples: list[Document] = []
    elif condition == "fewshot":
        examples = select_examples(target, pool, k, seed)
    else:
        raise ValueError(f"unknown condition {condition!r}")
    return {
        "system": system_prompt(template),
        "user": user_message(target, examples),
        "example_ids": [d.doc_id for d in examples],
    }


def prompt_fingerprint(prompt: dict) -> str:
    h = hashlib.sha256()
    h.update(prompt["system"].encode())
    h.update(b"\x00")
    h.update(prompt["user"].encode())
    return h.hexdigest()[:16]


_ = re  # keep import for potential template checks
