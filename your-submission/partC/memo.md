# Part C — Casual Tone in 6 Indic Languages

**Recommendation: (b) a ≤1B inference-time rewriter**, with (c)
prompt-engineering as the pre-committed fallback.

## Assumptions

- The production model can be run in-house on the A100 to few-shot
  generate casualized pairs. That's local inference, not external API
  spend, so it's within constraints.
- "No external API budget" rules out paid third-party LLMs for both
  data generation and LLM-as-judge evaluation.
- "Casual" means reduced formality register — contractions,
  colloquial particles, shorter sentences — not slang or code-mixing.
  This needs product confirmation; it moves the eval bar materially.
- The A100 is dedicated and is a *development* resource. Production
  serving capacity for (b) is not part of this budget (see below).

## Why (b)

The binding constraint isn't GPU time or the deadline — it's that
native review covers **2 of 6** languages. Tamil, Telugu, Bengali and
Marathi ship unvalidated regardless of approach. So the deciding
question is which approach fails safest where nobody is looking.

- **(a) SFT** changes the shared model's weights across all languages
  and tasks. A regression in an unreviewed language is hard to detect
  and can't be rolled back per-language.
- **(b) rewriter** is a discrete post-step with a per-language kill
  switch: if Telugu looks wrong, disable it there and fall back to
  today's trusted output. Nothing else regresses.
- **(c) prompt-only** is cheapest but weakest — formal register in
  under-represented Indic languages is largely a base-model
  training-data property, not a decoding-time framing choice.

## Arithmetic

**Reviewer throughput.** 10 h/wk × 3 wks = 30 h, Hindi + Kannada
only. At ~1 min/pair ≈ 1,800 ratings, ~900/language. Zero for the
other four.

**Data volume.** ~5–10k pairs/language × 6 = 30–60k pairs, few-shot
generated in-house. At ~2–3 s/pair unbatched ≈ 20–40 GPU-hours,
inside a 2-week budget (~140 usable GPU-hours at 10 h/day).

**Training.** LoRA on a ≤1B model over 30–60k short pairs is a
few-hour run — room for several iterations.

**Serving cost — the real trade-off with (b).** The rewriter runs on
every Indic response, adding a second decode pass over the full
reply. A ≤1B model at fp16 is ~2 GB of weights; decode is
memory-bandwidth-bound, so a ~200-token reply adds roughly **0.5–1 s
p50 latency** and consumes a permanent GPU slice that **is not in
this budget**. (a) has zero marginal serving cost by comparison.
This is the strongest argument against (b) and should be priced
before launch, not after — if product won't accept ~1 s added
latency on Indic replies, (b) is dead on arrival and (c) becomes the
recommendation by default.

## Success metric

Hindi + Kannada: reviewer preference for rewritten over current
output **≥70%**, with **no increase** in incorrect/nonsensical flag
rate. Unreviewed four: after a limited-exposure soft launch,
negative-feedback rate within **+1 pp** of baseline over one week.

## Kill criterion — end of week 2

Abandon (b) and ship (c) if preference is **<55%**, or the
incorrect/nonsensical rate rises **>3 pp**, or measured added latency
exceeds the product-agreed budget. Between 55% and 70%: ship (b)
behind a flag for Hindi + Kannada only, hold the other four on (c) —
a partial result shouldn't force an all-or-nothing call.

## Day 1

Few-shot generate ~50 casual Hindi pairs with the in-house model and
get them reviewer-rated the same day (~1 h session). This tests the
riskiest assumption — whether the in-house model can produce good
casual Indic rewrites at all without external API help — before
committing two weeks of GPU time.
