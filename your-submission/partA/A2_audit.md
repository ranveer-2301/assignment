# Part A2 — Script & Metric Audit

Corpus: 250 parallel FLORES-200 sentences (eng/hin), seed=42.
Tokenizer: gpt2. All numbers reproducible via `fertility_variants.py`.

**Tooling check first.** Ran the unmodified original on the new corpus:
eng 1.29, hin 7.78, ratio 6.04, tok/char 0.215/1.528.
`fertility_variants.py` with no flags gives 1.2878 / 7.7787 / 6.040 and
0.2148 / 1.5278 — identical at the original's printed precision. So
every delta below is caused by the toggled flag, nothing else.

## Code bugs (measured)

| # | Bug | Baseline → fixed | Effect |
|---|---|---|---|
| 1 | `split(" ")` (line 62) — double spaces create empty-string "words" | 6.040 → 6.041 | +0.02%, immaterial |
| 2 | `.lower()` (line 60) — no-op on Devanagari, alters English BPE | 6.040 → 6.266 | **+3.7%, material** |
| 3 | mean-of-ratios (lines 66–67) vs pooled sum/sum | 6.040 → 6.059 | +0.3%, small |
| — | all three together | 6.040 → **6.286** | +4.1% |

**Bug 2 is the one that matters.** Lowercasing is applied to a
supposedly controlled comparison but only affects one side, and
removing it makes the gap *larger* — the original script was making
Hindi look better than it is.

Bug 1 is worth fixing despite its size: line 5 of the Kannada FLORES
file has a naturally occurring double space, so this isn't only an
artifact of the doctored toy corpus.

**Direction of all three: the bugs understate the gap.** Corrected,
Hindi is 6.29x English, not 6.04x — the opposite of the usual
assumption that an audit finds the report too alarmist.

**Do not compare 6.286 to REPORT_v0's 5.89.** That figure came from the
10-sentence toy corpus; everything here is on the 250-sentence corpus.
The clean same-corpus bug effect is 6.040 → 6.286.

## Conceptual bug — tokens/word is the wrong thing to compute

The code computes `tokens/words` correctly. It's the wrong quantity for
the decision it drives. A whitespace word isn't content-controlled
across languages: Indic morphology packs more into one word than
English, so the metric mixes tokenizer quality with word-packaging.

Evidence — same tokenizer, same 250 parallel sentences, identical
content, only the denominator changing:

    tok / whitespace word  :  6.286x
    tok / UTF-8 byte       :  2.901x
    tok / grapheme cluster : 11.346x
    tok / parallel sentence:  7.313x

A 3.9x swing with content held constant. If tokens/word measured a real
property of serving Hindi, the answer couldn't move 4x on a denominator
choice. It reports 6.29x where the content-controlled number is 7.31x —
understating real per-request cost ~14%, and too unstable to route on.
A3 settles the correct denominator.

## Conceptual flaw in the report's reasoning

REPORT_v0 Finding 2 says the tok/char column "agrees" with tok/word and
"confirms" it — its only stated reason for "No further measurement
needed." But both share the same numerator. If the tokenizer
over-fragments Hindi, both rise together mechanically: one piece of
evidence counted twice. That false confidence is why the much larger
tokenizer effect in A3 was never found.

Related: `chars = len(line)` (line 63) counts code points, not grapheme
clusters — `len("किताबें")` is 7 for a ~4-character word — inflating the
denominator for Indic scripts. A3 uses `regex.findall(r"\X", ...)`.

## Cleared — inspected, NOT claimed as bugs

**`random.seed(1337)` (line 25).** Imported and seeded, never used.
Verified rather than assumed — commented it out, diffed both runs:
byte-identical, empty diff. Inert.

**`unicodedata.normalize("NFC", ...)` (line 49).** Looks like it could
distort Indic text; it's necessary — the same character can encode
precomposed or decomposed, and those tokenize differently.

**`add_special_tokens=False` (line 33).** Correct: counting BOS/EOS
would add a constant per line, inflating fertility more on short lines.
