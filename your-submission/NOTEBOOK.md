# Lab Notebook

## Initial read

Read REPORT_v0, fertility.py, model_spec.md, bench_log.csv. Two claims
look wrong:
1. "Hindi 5.89x worse — property of the script, not the tokenizer."
   gpt2's vocab is almost all Latin script, so an Indic-aware
   tokenizer should close most of this. If it does, the cause is
   training data, not the script.
2. "Longer prompts give better throughput" + a linear extrapolation to
   ~3200 tok/s at batch 48. Smells like a metric-definition bug.

## Part B

**B1.** KV bytes/token = 2 × 28 × 8 × 128 × 2 (fp16) = 114,688.
Budget = 0.92×24GB − 8.4GB weights − 1.6GB overhead = 12.08GB.
Max 4096-token sequences = 12.08GB / 469.8MB = 25.7 → 25.

Checked against the log (prompt 3584 + gen 512 = 4096 = max_model_len):
`preempted_seqs == batch − 25` exactly — 0 at batch 24, 7 at 32, 23 at
48. Exact match twice.

**B2.** reported_tok_s peaks at batch 24 (1607.4) then *falls* — 1384.0
at 32, 1298.5 at 48. Not a plateau, a regression, and it starts exactly
where kv_cache_util goes 0.93→0.97 and preemptions start. e2e_p95
blows up alongside (69s→97s→105s).

**B3.** Tested `num_requests × (prompt_len + gen_len) / wall_clock_s`
against all 13 rows — matches every one. So the column counts prefill
tokens as equivalent to decode tokens, which inflates long-prompt rows
more. Honest goodput at batch 24, two ways: 24×512/61.16 = 200.9 tok/s;
24×(1000/96.07) = 249.8 tok/s. Both ~85% below the headline 1607.4.

**B4.** preempted_seqs + kv_cache_util move with the collapse — using
those, no new instrumentation needed. *(Revised later — see final pass.)*

## Part A2 — corpus-level checks, before any tokenizer

`split(" ")` (line 62): found deliberate double spaces in eng line 6
and hin line 9 of the toy corpus. Each produces a phantom empty-string
word — 78→79 (eng), 61→62 (hin). Deflates fertility slightly. Open
question: does it move the 5.89x ratio, or is it immaterial? Need the
tokenizer to know.

`random.seed(1337)` (line 25): grep shows `random` imported and seeded,
never used. Looks like the planted red herring. To confirm by diffing
output with the line removed.

## Dead end — blocked on tooling

Wanted GPT-2 deltas for the lowercasing and mean-of-ratios hypotheses.
No tiktoken/transformers, no network in that environment. A2's
quantitative evidence and all of A3 deferred to a machine with
internet.

## A1 corpus

Wrote build_corpus.py against `Muennighoff/flores200`, config "all" —
one row per sentence with a column per language, so parallel by row
index. eng/hin/kan/tam, 250 sentences, seed 42. Not yet run.

## Part C — written while installs ran

Installs were slow (~150–290 KB/s), so used the time on C, which has no
tokenizer dependency. Key call: the binding constraint isn't GPU time
or the deadline, it's native review covering only 2 of 6 languages. So
I picked the approach that fails safest where nobody's checking (small
rewriter, per-language kill switch) over the one with the highest
ceiling. Still need to sanity-check the GPU-hour arithmetic and confirm
the "casual" definition with product.

## Dead end — FLORES loader broke

v1 failed: `RuntimeError: Dataset scripts are no longer supported, but
found flores200.py`. That repo loads via a Python script and
`datasets` ≥ 4.0 (I'm on 5.0.1) dropped support for those.

v2: switched to `DGME/FLORES-200`, which hosts plain .devtest text
files, fetched with `hf_hub_download`. No script, nothing to
deprecate. Cost: lost the `domain` column, so A1's domain claim is
documented rather than measured.

## A1 built

1012 parallel lines per language, matching FLORES devtest's documented
size. 250 sampled per language into corpus/.

## A2 measured (250 lines, gpt2)

baseline 6.040 | fix-split 6.041 | no-lowercase 6.266 | pooled 6.059 |
all three 6.286.

Lowercasing is the big one (+3.7%); the other two are near-noise.
Fixing everything makes the gap *larger*, not smaller — the bugs were
understating the problem.

## A3 — the main finding

gpt2 vs xlm-roberta-base, all four languages. Swapping tokenizers
closes 83% (hin), 90% (kan), 91% (tam) of the word-fertility gap.
That falsifies "property of the script, not the tokenizer" directly.

Surprise: xlm-r's tok/byte ratios go *below* 1.0 for all three Indic
languages. Looked like "Indic is cheaper" until I realised it's a UTF-8
artifact — 3 bytes/char vs 1 for ASCII. That's why I'm trusting
tok/parallel-sentence, not tok/byte or tok/word. Content-normalized:
hin 1.24x, kan 1.38x, tam 1.35x.

Cross-check: gpt2 eng/hin here (1.231 / 7.741 → 6.286) matches the A2
all-fixes run exactly. Two scripts agree.

## Review pass — hunting for overclaiming

- B1's decimal-GB vs GiB assumption was buried in a parenthetical.
  Stated explicitly.
- B2's mechanism was written as if measured. The correlation is
  measured; recompute is inferred. Reworded.
- random.seed rested on grep alone. Added the diff command.
- The "3 bytes/char" claim was from memory. Verified:
  `len("क".encode("utf-8"))` = 3.
- Real catch: could xlm-r's win just be a bigger vocab helping
  everything? No — English gets *worse* under xlm-r on all four
  denominators while Indic improves sharply. That asymmetry is the
  actual evidence. Added to A3.

Not done yet: never checked the four corpus files are semantically
aligned, only that line counts match.

## Second pass — re-read the source files

Verified every quote and line number against REPORT_v0 and fertility.py
directly rather than my own summaries. All check out. Found two
problems in my own work:

**1. Corpus confound (my error).** I'd compared my 6.040 baseline
against the report's 5.89 as if bug fixes explained it. They don't —
5.89 is the toy corpus, 6.040 is mine. The clean same-corpus effect is
6.040 → 6.286.

**2. Missed the report's biggest flaw.** Finding 2 says tok/char
"confirms" tok/word. They share a numerator — if the tokenizer
over-fragments Hindi, both rise together. One piece of evidence counted
twice, and it's the stated reason the original author stopped
measuring. Added to A2.

Also: `chars = len(line)` (line 63) counts code points, not graphemes —
`len("किताबें")` = 7 for a ~4-character word.

Ran the unmodified original on the new corpus: eng 1.29, hin 7.78,
ratio 6.04, tok/char 0.215/1.528. My variants script with no flags
gives the same at that precision. So every A2 delta is the flag, not a
rewrite artifact.

## random.seed — verified inert

Commented the line out, diffed both runs. Empty diff. Flagged as the
red herring, explicitly not claimed as a bug — claiming it would have
cost −5.

## Dead end — my alignment check silently checked nothing

`sed -n '5p'` over four files returned one line. sed concatenates
multiple files unless `-s` is passed, so it sampled line 5 of eng.txt
only. Exits 0, prints plausible output — a false pass, not a visible
error.

Re-ran with `-s`. Alignment confirmed: line 5 is the same sentence in
all four — "Throughout 1960s, Brzezinski worked for John F. Kennedy…"
with Brzezinski, Kennedy, Lyndon B. Johnson and 1960 all transliterated
in the other three. Proper nouns and digits survive translation, so
this is checkable without fluency.

Incidental: the Kannada line has a naturally occurring double space, so
the `split(" ")` bug isn't only an artifact of the doctored toy corpus.

## Final pass — against the brief, question by question

**B4 was circular.** I'd answered with preempted_seqs — already in the
log, already used in B1 to establish the correlation. It can't confirm
the mechanism it's the premise of. The claim is *recompute*, not swap,
so the distinguishing counter is cumulative prefill tokens: equal to
num_requests × prompt_len with no recompute, higher by preempted_seqs ×
prompt_len with it. Expected 1.00x at batch 24, 1.22x at 32, 1.48x at
48 — and a flat 1.00x everywhere would falsify me and mean swap-based
preemption instead.

**B2 predicted in units B3 debunks.** I'd said capping sustains ~1607
tok/s — that's reported_tok_s. Restated in goodput: 200.9 at batch 24
vs 162.3 at 48, so capping *raises* real throughput ~24% on fewer
requests.

**A4 contradicted A1.** Monitoring metric said "tokens-generated-per-
request" — output tokens — but I measured input fertility, and A1 says
output was never measured. Changed to input tokens. Also cut a
"~21-word average" I never computed.

**A4 assumed a free tokenizer swap.** It isn't — the tokenizer is tied
to the embedding matrix, so this is a model-selection decision, not a
config flag. Added.

**Part C had no serving cost.** The brief asks for training *or*
serving cost and I chose the option that runs on every request. Added
~2GB weights, ~0.5–1s added p50, permanent GPU slice outside the
budget — and noted it's the strongest argument against my own pick: if
product won't take the latency, (b) dies and (c) wins.

**A2 said "Bug 4" for random.seed.** Body said it wasn't a bug, but the
heading alone reads as a fourth claim — −5 risk. Renamed to "Cleared."
Added two more cleared items I'd checked but not written down: NFC
normalization (line 49, necessary — Indic text encodes precomposed or
decomposed) and add_special_tokens=False (line 33, correct — BOS/EOS
would inflate short lines more).

## Before submitting

- [x] Corpus alignment — confirmed
- [x] random.seed diff — empty, inert
- [x] AI_USAGE.md
- [ ] Rehearse cold: B1 arithmetic, why reported_tok_s is wrong, why
      the English control rules out "just a bigger vocab"
