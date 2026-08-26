# Part A1 — Eval Corpus Construction

Reproducible: `python build_corpus.py --n 250 --seed 42 --outdir corpus`
→ `partA/corpus/`

**Source: FLORES-200 devtest** (DGME/FLORES-200 mirror, raw text files).
Chosen because it's *parallel* — same sentence, professionally
translated, same line number = same content. That's what makes the
tokens-per-parallel-sentence denominator in A3 valid; it's the only
denominator holding content constant across languages. Used the DGME
mirror rather than `Muennighoff/flores200` because the latter loads via
a dataset script, unsupported in `datasets` >= 4.0 (see NOTEBOOK.md).

**Languages (4):** eng (Latin), hin (Devanagari), **kan** and **tam**
(both Dravidian). Kannada/Tamil chosen arbitrarily among the Dravidian
options; nothing in the analysis depends on that choice.

**Size:** 250 sentences/language, sampled seeded (42) from devtest's
1012 (builder asserts equal line counts across files and aborts
otherwise). Same 250 indices for all four languages, so the sample
stays parallel. Big enough to beat the 10-sentence toy corpus, small
enough to re-run across tokenizers repeatedly.

**Alignment verified:** line 5 spot-checked — English reads
"Throughout 1960s, Brzezinski worked for John F. Kennedy…"; Hindi,
Kannada and Tamil all carry "Brzezinski", "Kennedy", "Lyndon B.
Johnson", "1960" transliterated. Proper nouns and digits survive
translation, so alignment is checkable without script fluency.

**Preprocessing:** build time — `.strip()` only. Analysis time — NFC
normalization (Indic text can encode the same character precomposed or
decomposed, and the two tokenize differently), blank lines skipped, and
**no lowercasing** in A3, since A2 showed `.lower()` is a no-op for
Indic scripts but alters English tokenization — an asymmetric transform
inside a supposedly controlled comparison.

**Domain:** per FLORES documentation, English source sentences come
from Wikinews, Wikijunior and Wikivoyage. Documented, not measured —
this mirror carries no per-sentence domain column, so the breakdown of
this particular subsample is unverified.

## What this corpus cannot tell us

This is formal encyclopedic prose — complete, well-formed, ~20-30 word
sentences — so the numbers are a formal-text baseline, not a production
estimate. It says nothing about short conversational queries (where
fixed per-message overhead dominates), code-mixed input (Hinglish and
Latin-script transliteration are ubiquitous in real Indian-market
traffic and wholly absent here), domain vocabulary, or output tokens,
since fertility is measured on input only. And 250 sentences is small:
enough to establish the gpt2-vs-XLM-R gap is large and directional
(A3's effects are multiples, not percentage points, so sampling noise
can't explain them), not enough to pin the content-normalized ratio
precisely — treat A4's 1.2-1.4x as order-of-magnitude, not a costing
input.
