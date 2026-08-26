# AI Usage

I used Claude (Opus 5) heavily. It wrote most of the code
(`build_corpus.py`, `fertility_variants.py`, `fertility_a3.py`) and
first drafts of the writeups. I ran everything myself — every number
in this repo is output I saw on my machine, not something quoted from
the model.

**Where it was wrong:**

- It compared my corrected 6.286 against the report's 5.89 as if the
  bug fixes explained the gap. They don't — 5.89 was on the toy
  corpus, 6.040 on mine. Different data. Caught this on review; the
  clean same-corpus effect is 6.040 → 6.286.
- It missed the report's biggest flaw on the first pass — that
  tok/char can't "confirm" tok/word when they share a numerator. That
  only came out on a second read of the source file, and it's the
  reason the original author stopped measuring.
- It stated the B2 preemption mechanism as if the log proved it. The
  log shows the correlation; the recompute explanation is inferred.
  Fixed in B2, and B4 now proposes a counter that would tell the two
  apart.
- Asserted the UTF-8 byte-width and `random.seed` claims from memory.
  I checked both — the seed one by diffing runs with the line
  commented out.
- Its first `build_corpus.py` used a HuggingFace loader that no
  longer exists in `datasets` ≥ 4.0. Broke on my machine, rewritten.
- My alignment check (`sed -n '5p'` over four files) silently checked
  only one file and still exited cleanly. Re-ran with `-s`.

**Where I didn't take its suggestion:** it initially framed the
`split(" ")` bug as significant. Measured, it's 0.02% — reported as
immaterial. And `random.seed` is explicitly not claimed as a bug.

**What I actually understand vs. what I'd need notes for:** the
tokenizer result is the part I worked through myself — including why
English getting *worse* under XLM-R rules out vocab size as the
explanation. I can defend that cold. Part B I understand structurally
but verified by running commands and checking consistency, not by
re-deriving the arithmetic by hand — I'd want the spec table in front
of me to rebuild 114,688 from scratch, and I'd recompute B4's 1.22×
/ 1.48× live rather than quote them. Stating that plainly rather than
overclaiming.
