# BAIT: cognitive bias trigger detection benchmark

BAIT annotates the passages in news articles that can trigger nine cognitive
biases in a reader. It covers 50 English articles from the SemEval-2023 Task 3
corpus (Piskorski et al., 2023), with 398 gold triggers (143 of them made of
several spans) and 592 spans. This repository contains the annotations, the
annotation codebook, the evaluation code and the model predictions reported in
the paper.

The article texts are **not** redistributed. Obtain the SemEval-2023 Task 3
data from the task organisers and rebuild the full dataset with
`scripts/rehydrate.py`. Scoring needs only the released offsets.

## Contents

```
CODEBOOK.md                  definitions, trigger signals, examples, annotation rules
data/bait_annotations.jsonl  gold annotations (character offsets, no text)
predictions/run_seed*.jsonl  aligned predictions of the six models in the paper
                             (one zero-shot run and one k=10 run per seed; no text)
prompts/bait_fewshot_prompt.md  prompt template used in the paper
models.json                  model registry used in the paper (no API keys)
bait/data.py                 gold loader
bait/prompts.py              zero-shot and leave-one-out few-shot prompts
bait/backends.py             API calls (Anthropic Messages, OpenAI-compatible)
bait/parse.py                parse and validate model outputs
bait/align.py                align span strings to character offsets
bait/evaluate.py             Task 1 and Task 2 metrics
scripts/rehydrate.py         rebuild the full dataset from the SemEval articles
scripts/run_models.py        query models and save raw completions
scripts/align_outputs.py     parse raw completions and align spans to offsets
scripts/score.py             corpus-level scores, per-article scores, paired tests
```

## Quick start

```bash
pip install -r requirements.txt

# Reproduce the main results table from the released predictions
python scripts/score.py predictions/*.jsonl

# Rebuild the dataset with article text (needed to prompt models and align spans)
python scripts/rehydrate.py --semeval-dir path/to/semeval2023task3/data/en \
                            --annotations data/bait_annotations.jsonl --out bait_full.jsonl

# Run models (set the API key variables named in models.json)
python scripts/run_models.py --gold bait_full.jsonl --models models.json \
                             --model gpt-5.6 --k 10 --seeds 17 23 29 --out outputs.jsonl

# Parse, align and score
python scripts/align_outputs.py --outputs outputs.jsonl --gold bait_full.jsonl --out preds.jsonl
python scripts/score.py preds.jsonl --out results_mine
```

`run_models.py` runs, per seed, one zero-shot pass and one pass with `k`
examples. Examples are drawn per target article from the other 49 articles,
seeded by the run seed and the article; one example always contains a
multi-span trigger. Requests use temperature 0 plus any `extra_params` set for the
model in `models.json`; the run can be restarted and skips completions already saved. The `mock-gold` and
`mock-none` backends need no API key and check the pipeline offline
(`mock-gold` scores 1.0 everywhere).

To score outputs from your own setup, write one line per article and run:
`{"model": "...", "k": 0, "seed": 0, "doc_id": 1, "output": "<raw completion>"}`
and start from `align_outputs.py`. Runs with the same `model` and `k` but a
different `seed` are averaged, and paired tests compare each `k > 0` with
`k = 0`.

## Data format

`data/bait_annotations.jsonl`, one article per line:

| field | description |
|---|---|
| `doc_id` | BAIT article id (1–50) |
| `article_id` | SemEval-2023 Task 3 article id (file `article<id>.txt`) |
| `split` | SemEval split the article comes from (`train` / `dev`) |
| `text_length`, `text_sha256` | length and SHA-256 (UTF-8) of the exact text the offsets refer to |
| `biases_present` | article-level labels (B01–B09) |
| `triggers` | list of `{trigger_id, bias, bias_name, spans: [{start, end}]}` |

Offsets are Python character offsets, end-exclusive. A trigger with several
spans is one discontinuous trigger. A passage labelled with two biases appears
as a span in one trigger of each bias.

Bias codes: B01 Illusory Truth, B02 Negativity Bias, B03 Bandwagon Effect,
B04 Authority Bias, B05 Stereotyping, B06 Declinism, B07 Identifiable Victim
Effect, B08 Illusory Correlation, B09 Hindsight Bias. See
[`CODEBOOK.md`](CODEBOOK.md).

## Evaluation

**Task 1, detection.** Which biases are triggered anywhere in the article:
micro-F1, macro-F1 and subset accuracy over B01–B09. If a model's
`biases_present` disagrees with the biases among its triggers, the union is
used.

**Task 2, localisation.** Model spans are strings, aligned to the article with
a four-step cascade (exact, case-folded, whitespace-flexible, fuzzy at
difflib ratio ≥ 0.80; see `bait/align.py`). When a string occurs several
times, a position not yet used by the same bias in that output is preferred,
then one overlapping a gold span of that bias, then the leftmost. Spans that cannot be placed are kept and count as false
positives. Three scores:

- *char-F1*: overlap of character masks, per bias;
- *span-F1*: one-to-one matching of spans of the same bias at IoU ≥ 0.5;
- *trigger-F1*: one-to-one matching of triggers of the same bias, with
  similarity the character-overlap F1 between their span unions, at ≥ 0.5.
  This is the only score that rewards grouping spans correctly.

Unparseable outputs are scored as empty predictions. Corpus-level scores pool
counts over all articles and biases within a run and are averaged over runs.
Significance tests use per-article scores (an article with no gold trigger and
no predicted trigger scores 1), two-sided paired t-tests over articles, and
Holm correction within each task.

Running `scripts/score.py` on `predictions/` reproduces the paper's main table,
its run-to-run standard deviations and its tests against zero-shot.

## License

Code, annotations and codebook are released under the MIT License (see
`LICENSE`). The SemEval-2023 Task 3 articles are not part of this release and
remain under the terms set by the task organisers.

## Citation

TODO
