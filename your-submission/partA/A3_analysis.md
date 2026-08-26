# Part A3 — Corrected Cross-Language Analysis

Corpus: 250 parallel FLORES-200 sentences, eng/hin/kan/tam (A1).
A2 fixes applied throughout — no lowercasing, `.split()`, pooled
aggregation. Tokenizers: gpt2 (Latin-dominated) and xlm-roberta-base
(multilingual). Denominators: whitespace word, UTF-8 byte, grapheme
cluster, parallel sentence.

## Measurements

**gpt2**

| lang | tok/word | tok/byte | tok/grapheme | tok/sentence |
|---|---|---|---|---|
| eng | 1.231 | 0.2048 | 0.205 | 26.48 |
| hin | 7.741 | 0.5942 | 2.327 | 193.67 |
| kan | 22.752 | 0.9794 | 4.076 | 362.40 |
| tam | 25.198 | 0.9966 | 4.217 | 411.43 |

**xlm-roberta-base**

| lang | tok/word | tok/byte | tok/grapheme | tok/sentence |
|---|---|---|---|---|
| eng | 1.393 | 0.2318 | 0.232 | 29.97 |
| hin | 1.484 | 0.1139 | 0.446 | 37.13 |
| kan | 2.591 | 0.1116 | 0.464 | 41.28 |
| tam | 2.476 | 0.0979 | 0.414 | 40.42 |

## It's the tokenizer, not the script

| lang | gpt2 tok/word | xlm-r tok/word | gap closed |
|---|---|---|---|
| hin | 6.29x | 1.06x | 83.1% |
| kan | 18.48x | 1.86x | 89.9% |
| tam | 20.46x | 1.78x | 91.3% |

REPORT_v0 calls the gap "a property of the script, not the tokenizer."
Falsified: swapping tokenizers, changing nothing else, closes 83–91%
of it. gpt2's 18–20x for Kannada and Tamil measures how little Indic
vocabulary its BPE merges hold, not anything about those languages.

**Not just a bigger vocabulary.** XLM-R has ~250k tokens vs gpt2's
~50k, so more slots should shorten tokenizations for everything.
English instead gets *worse* on all four denominators (tok/word
1.231→1.393, tok/byte 0.205→0.232, tok/grapheme 0.205→0.232,
tok/sentence 26.48→29.97) while the Indic languages improve sharply.
That asymmetry points at multilingual training coverage, not vocab
size.

## Which denominator, and why

The denominator has to hold **content** constant — we're asking "what
does it cost to serve the same request in another language," so
anything that varies with the language's own packaging of that content
is a confound.

- **Word** — fails. Indic morphology, and Dravidian agglutination
  especially, packs more meaning per whitespace word than English, so
  the ratio mixes tokenizer quality with word-packaging.
- **Byte** — fails. Devanagari, Kannada and Tamil characters are 3
  bytes in UTF-8 against 1 for ASCII (`len("क".encode("utf-8"))` = 3),
  so the denominator is pre-inflated for these scripts. This is why
  xlm-r's byte ratios fall *below* 1.0 (0.42–0.49x) — an encoding
  artifact, not evidence Indic text is cheaper to serve.
- **Grapheme cluster** — fails, more subtly. It holds *visual
  characters* constant, not content: conjuncts and matras let one
  Indic grapheme carry a whole syllable where a Latin one carries a
  phoneme, so the same sentence is far fewer graphemes in Kannada than
  in English.
- **Parallel sentence** — works. The corpus is parallel, so one line
  is the same content in every language by construction. No morphology
  confound, no encoding confound.

**The single number: tokens per parallel sentence, under a
multilingual tokenizer — 1.24x (hin), 1.38x (kan), 1.35x (tam)
against English.** That is what a routing-and-cost decision should be
built on. Note it is *not* the smallest available number — under gpt2
the same metric reads 7.31x/13.68x/15.54x — the point is that it is
the only one holding content constant.

## Implication for the report's recommendation

REPORT_v0 recommends routing Indic traffic to a separate stack and
budgeting 6x for Hindi. Both need revising:

- 6x is a gpt2 artifact, not a property of Hindi. Content-normalized,
  with a multilingual tokenizer, the real premium is ~1.2–1.4x.
- The higher-leverage fix isn't routing Indic traffic away — it's not
  serving it through a Latin-centric tokenizer to begin with. That
  closes most of the gap before any routing work.
