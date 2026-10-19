# Results

One folder per workflow, model, set and run: `<workflow>/<model>/<set>/<run>/`, e.g. `span-detection/jev/all/run-1/` or `span-detection/jev/xgsz/run-1/`. See the main README for what each script writes.

## All GSZ, 2026-10-18

Every workflow ran three times on all 227 GSZ biographies (`--split all`), for both codes: Jev 1.14 (`jev-1.14.0`) for sentence and span detection, Claude Sonnet 5.5 (`claude-sonnet-5-5`) and GPT-6.1 Sol (`gpt-6.1-sol`) at effort `low` for the LLM workflows. Scores are against `gsz/gold/` (458 Scholarship and 107 Asceticism spans) and are the mean of the three runs.

Cost per run is for both codes together, from the token usage each request recorded, at list prices: Jev $0.042 per million input tokens (output free); Claude and GPT $2 per million input tokens, $0.20 (Claude) or $0.10 (GPT) per million cached tokens read, $2.50 per million written to the cache, and $10 per million output tokens. Without caching, every input token is charged at the full input price: the cost when no part of the prompt is reused, which does not depend on how the requests are timed (Jev has no caching). GPT's first run wrote its prompt cache and its later runs read it, so its cost is the mean of unequal runs (sentence detection $1.830, $0.372, $0.370; span detection $1.443, $0.622, $0.622). Time per run is the scripts' own timing summed over their steps; the three passes of sentence detection ran in parallel, so their wall-clock time was about a third of the figure.

### Span workflows

κ (Cohen's kappa) is agreement with gold on which sentences are in a span, adjusted for chance (1 = identical, 0 = chance). γ (gamma; Mathet, Widlöcher and Métivier 2015, not Goodman and Kruskal's gamma) is agreement on the spans themselves, after aligning model and gold spans: it penalizes shifted or resized spans and missing or extra ones, adjusted for chance. A missed gold span has none of its sentences in a model span; an extra span has no gold sentence in it.

| Workflow | Code | κ | γ | Missed gold spans | Extra spans | Cost per run | Without caching | Time per run |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Jev span detection | Scholarship | 0.790 | 0.802 | 33.7 of 458 (7.4%) | 33.3 | $0.224 | $0.224 | 220 s |
| | Asceticism | 0.690 | 0.897 | 6.7 of 107 (6.2%) | 7.0 | | | |
| Claude low, LLM span | Scholarship | 0.720 | 0.731 | 5.0 of 458 (1.1%) | 132.7 | $1.310 | $3.035 | 138 s |
| | Asceticism | 0.694 | 0.851 | 0.3 of 107 (0.3%) | 19.3 | | | |
| GPT low, LLM span | Scholarship | 0.759 | 0.734 | 2.3 of 458 (0.5%) | 102.0 | $0.896 | $2.462 | 364 s |
| | Asceticism | 0.829 | 0.882 | 0 of 107 (0%) | 6.0 | | | |

### Sentence workflows

A place is a spot a reviewer goes to read: a run of flagged sentences, two runs with one unflagged sentence between them counting as one. A gold span is hit when at least one of its sentences is flagged; a false place holds no gold sentence.

| Workflow | Code | Gold spans hit | Places | False places | Cost per run | Without caching | Time per run |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Jev sentence detection | Scholarship | 453.3 of 458 (99.0%) | 534 | 116 (22%) | $0.125 | $0.125 | 197 s |
| | Asceticism | 105.7 of 107 (98.8%) | 117 | 12 (11%) | | | |
| Claude low, LLM sentence | Scholarship | 453.0 of 458 (98.9%) | 525 | 119 (23%) | $1.269 | $2.510 | 92 s |
| | Asceticism | 107 of 107 (100%) | 126 | 21 (16%) | | | |
| GPT low, LLM sentence | Scholarship | 454.7 of 458 (99.3%) | 510 | 99 (19%) | $0.857 | $1.981 | 270 s |
| | Asceticism | 107 of 107 (100%) | 115 | 9 (8%) | | | |

### Cost of each run

| Workflow / model | Run 1 | Run 2 | Run 3 | Without caching, per run | Input tokens per run | Output tokens per run |
| --- | --- | --- | --- | --- | --- | --- |
| Jev sentence detection | $0.125 | $0.125 | $0.125 | $0.125 | 2.98M | 1.23M (free) |
| Jev span detection | $0.224 | $0.224 | $0.224 | $0.224 | 5.34M | 0.62M (free) |
| Claude low, LLM sentence | $1.297 | $1.255 | $1.255 | $2.510 | 1.20M | 10k |
| GPT low, LLM sentence | $1.830 | $0.372 | $0.370 | $1.981 | 0.85M | 28k |
| Claude low, LLM span | $1.348 | $1.292 | $1.289 | $3.035 | 1.39M | 26k |
| GPT low, LLM span | $1.443 | $0.622 | $0.622 | $2.462 | 0.97M | 52k |

Total for the 18 runs: $14.05 (TypeSafe $1.05, Anthropic $7.74, OpenAI $5.26); without caching $31.01 (TypeSafe $1.05, Anthropic $16.63, OpenAI $13.33).

## All XGSZ, 2026-10-18

Jev span detection (`jev-1.14.0`) ran once on all 472 XGSZ biographies (`--corpus xgsz`), for both codes: `span-detection/jev/xgsz/run-1/`. There is no gold for the XGSZ. A biography counts as having a code when at least one span of it is kept.

| | Asceticism | No Asceticism | Total |
| --- | --- | --- | --- |
| Scholarship | 105 | 242 | 347 |
| No Scholarship | 39 | 86 | 125 |
| Total | 144 | 328 | 472 |

The run cost $0.763 (18.2M input tokens; Jev has no caching) and took 558 s, the scripts' own timing summed over their steps.
