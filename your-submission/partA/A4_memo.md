# Part A4 — Recommendation Memo

## Recommendation

Do not budget 6x serving cost for Indic traffic. That figure is an
artifact of measuring with gpt2, whose vocabulary is
Latin-script-dominated — 83–91% of the gap disappears when the same
corpus is tokenized with a multilingual tokenizer, with nothing else
changed. The real, content-normalized premium is ~1.2–1.4x.

The leverage is in tokenizer coverage, not routing. Rather than
splitting Indic traffic to a specialized stack, prefer a model whose
tokenizer already has real Indic coverage — that closes most of the
gap before any routing work is done.

**Cost of doing this:** a tokenizer isn't a config flag. It's tied to
the model's embedding matrix, so "use a better tokenizer" means
selecting or retraining a model, not swapping a component on the
current one. The realistic decision is therefore at model-selection
time; for an already-deployed model, the 6x figure is still wrong but
the near-term options are narrower. Recommend evaluating Indic
tokenizer coverage as an explicit criterion in the next model
decision.

## Corrected headline numbers

250 parallel FLORES-200 sentences, English/Hindi/Kannada/Tamil,
xlm-roberta-base vs gpt2:

| metric (vs English) | hin | kan | tam |
|---|---|---|---|
| tok/word, gpt2 | 6.29x | 18.48x | 20.46x |
| tok/word, xlm-r | 1.06x | 1.86x | 1.78x |
| **tok/parallel sentence, xlm-r** | **1.24x** | **1.38x** | **1.35x** |

The bottom row is the one to plan against — it's the only denominator
holding content constant across languages (A3).

## Biggest caveat

FLORES is formal, professionally translated encyclopedic prose. It
says nothing about how these numbers behave on short conversational
queries, on code-mixed input (Hinglish/Tanglish, ubiquitous in real
Indian-market traffic and entirely absent here), or on product and
support vocabulary. It also measures input text only — output tokens
were never measured, and they carry the larger share of serving cost.
Treat 1.2–1.4x as a formal-text baseline, not a costing input, until
it's checked against real traffic.

## Metric to monitor

**Input tokens per request, segmented by detected language, as a
ratio against English.** This is the production analogue of
tokens-per-parallel-sentence: real requests instead of matched
sentences, same content-normalized logic.

Expected: ~1.2–1.4x under a multilingual tokenizer. If it lands
materially above ~1.5x, this analysis was wrong about
representativeness — most likely because code-mixing or domain
vocabulary tokenizes worse than FLORES's clean formal text — and the
cost model needs rebuilding on traffic samples rather than a public
benchmark.
