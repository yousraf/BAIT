#!/usr/bin/env python3
"""Query models on BAIT and save their raw completions.

    python scripts/run_models.py --gold bait_full.jsonl --models models.json \
        --model claude-opus-4.8 gpt-5.6 --k 10 --seeds 17 23 29 --out outputs.jsonl

For every seed this runs one zero-shot pass and one few-shot pass with k
leave-one-out examples (drawn per target article, seeded by the run seed), as
in the paper. Lines already in --out are skipped, so an interrupted run can be
restarted with the same command. Requests that fail after retries are logged to
stderr and left out; rerun to fill them in.

The output feeds scripts/align_outputs.py.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bait import load_documents  # noqa: E402
from bait.backends import BackendError, complete, load_registry  # noqa: E402
from bait.data import gold_output_json  # noqa: E402
from bait.prompts import build_prompt, load_template, prompt_fingerprint  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default="bait_full.jsonl")
    ap.add_argument("--template", default=str(ROOT / "prompts" / "bait_fewshot_prompt.md"))
    ap.add_argument("--models", default="models.json")
    ap.add_argument("--model", nargs="+", required=True, help="names from the registry")
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--seeds", type=int, nargs="+", default=[17, 23, 29])
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    docs = load_documents(args.gold)
    if not all(d.text for d in docs):
        sys.exit("--gold has no article text; run scripts/rehydrate.py first")
    template = load_template(args.template)
    registry = load_registry(args.models)

    done = set()
    if Path(args.out).exists():
        for line in open(args.out, encoding="utf-8"):
            r = json.loads(line)
            done.add((r["model"], r["k"], r["seed"], r["doc_id"]))

    n_new = n_fail = 0
    with open(args.out, "a", encoding="utf-8") as fout:
        for name in args.model:
            entry = registry[name]
            for seed in args.seeds:
                for k, condition in ((0, "zeroshot"), (args.k, "fewshot")):
                    for doc in docs:
                        key = (name, k, seed, doc.doc_id)
                        if key in done:
                            continue
                        prompt = build_prompt(template, doc, docs, condition, k, seed)
                        try:
                            text = complete(entry, prompt["system"], prompt["user"],
                                            max_tokens=args.max_tokens, gold_json=gold_output_json(doc))
                        except BackendError as e:
                            print(f"FAILED {key}: {e}", file=sys.stderr)
                            n_fail += 1
                            continue
                        fout.write(json.dumps({
                            "model": name, "k": k, "seed": seed, "doc_id": doc.doc_id,
                            "example_ids": prompt["example_ids"],
                            "prompt_fingerprint": prompt_fingerprint(prompt),
                            "output": text,
                        }, ensure_ascii=False) + "\n")
                        fout.flush()
                        n_new += 1
    print(f"{n_new} new completions -> {args.out}" + (f"; {n_fail} failed (rerun to retry)" if n_fail else ""))


if __name__ == "__main__":
    main()
