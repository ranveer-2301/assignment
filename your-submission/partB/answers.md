# Part B — Capacity Reconciliation

All numbers below are derived directly from `bench/model_spec.md` and
`bench/bench_log.csv` -- no external tools needed. 

## B1 — KV-cache bytes/token and max concurrent sequences

**KV-cache bytes per token:**

    bytes/token = 2 (K and V) x num_layers x num_kv_heads x head_dim x bytes_per_element
                = 2 x 28 x 8 x 128 x 2
                = 114,688 bytes
                = 112.0 KiB / token

(2 bytes/element because KV cache precision is fp16; the leading 2x is
because we store both the K and V projections per layer.)

**Max concurrent 4096-token sequences:**

    usable memory  = gpu_memory_utilization x GPU memory
                   = 0.92 x 24 GB = 22.08 GB
    KV budget      = usable - model_weights - overhead
                   = 22.08 GB - (4.2B params x 2 bytes) - 1.6 GB
                   = 22.08 - 8.40 - 1.60
                   = 12.08 GB
    bytes/sequence = 114,688 bytes/token x 4096 tokens = 469.8 MB
    max sequences  = 12.08 GB / 469.8 MB = 25.7 -> 25

**Check against the log:** rows where `prompt_len + gen_len = 4096`
(the 3584-prompt sweep) show `preempted_seqs` exactly equal to
`batch_size - 25` once batch exceeds capacity:

| batch | kv_cache_util | preempted_seqs | predicted (batch-25) |
|---|---|---|---|
| 4  | 0.16 | 0 | 0 |
| 8  | 0.31 | 0 | 0 |
| 16 | 0.62 | 0 | 0 |
| 24 | 0.93 | 0 | 0 |
| 32 | 0.97 | 7 | 7 |
| 48 | 0.97 | 23 | 23 |

Exact match. This is strong confirmation the arithmetic is right --
**but it's conditional on one unstated assumption**: that "24 GB" in
the spec means decimal gigabytes (24 x 10^9 bytes), not binary
gibibytes (24 x 2^30 = ~25.77 x 10^9 bytes). The spec doesn't say
which. I used decimal GB throughout (matching how GPU nameplate specs
are usually quoted) and it reconciled exactly with the log, which is
reasonable evidence for that choice -- Decimal GB is assumed throughout; 
the exact reconciliation with the log supports that reading.

## B2 — The long-context throughput anomaly

Naive expectation: throughput scales with batch size, or at worst
plateaus once compute/bandwidth-bound. Instead, in the 3584-prompt
sweep, `reported_tok_s` **falls** from batch 24 to 48:

    batch 16: 1311.4 tok/s
    batch 24: 1607.4 tok/s   <- peak
    batch 32: 1384.0 tok/s   <- drop, despite +8 more requests
    batch 48: 1298.5 tok/s   <- drops further

This inflection point (24->32) is exactly where `kv_cache_util` hits
0.93->0.97 and `preempted_seqs` goes from 0 to 7 -- i.e. exactly where
concurrency exceeds the ~25-sequence KV-cache ceiling from B1.

**Mechanism** the log directly shows preemption count and
KV utilization rising in lockstep with the throughput drop -- that
correlation is measured fact. The specific *why* -- that vLLM-style
schedulers preempt by evicting KV cache and recomputing prefill on
reschedule, which is wasted work -- is standard, well-documented
serving-scheduler behavior, not something this particular log proves
directly (bench_log.csv has no "recompute" column). State it as the
best available explanation consistent with the data, not as
independently confirmed: once batch size x per-sequence KV footprint
exceeds physical KV-cache capacity, the scheduler preempts in-flight
sequences -- evicting their KV cache and (under the standard
preemption model) forcing prefill to be recomputed when they're
rescheduled. That recompute would be pure wasted GPU work: it
consumes compute/bandwidth without producing any new generated
tokens, which would explain why *measured* throughput falls even
though nominal batch size rose. `e2e_ms_p95` corroborates the general
"requests are stalling" picture: 69,221ms (batch 24) -> 97,466ms
(batch 32) -> 105,428ms (batch 48).

**Proposed change:** cap concurrency for long-context (near
max_model_len) requests at 24 — `max_num_seqs=24`, or admission
control keyed off estimated KV footprint rather than raw request
count.

**Predicted effect, in goodput (not `reported_tok_s`, which B3 shows
is not a valid throughput measure):** at batch 24 the honest decode
goodput is 24 × 512 / 61.16 = 200.9 tok/s with zero preemptions. At
batch 48 it is 48 × 512 / 151.41 = 162.3 tok/s — capping at 24
therefore *raises* real goodput by ~24% while serving fewer
concurrent requests, because the extra 23 sequences do net negative
work. Tail latency improves in the same direction: `e2e_ms_p95` 69.2s
at batch 24 vs 105.4s at batch 48.

## B3 — What `reported_tok_s` actually measures

Reverse-engineered formula (matches every row in the log to 1 decimal
place):

    reported_tok_s = num_requests x (prompt_len + gen_len) / wall_clock_s

e.g. batch 16, prompt 3584: 16 x (3584+512) / 49.97 = 1311.5 -> log
shows 1311.4. This holds across all 13 rows.

**The bug:** this counts prefill tokens (processed once, in parallel,
across the whole prompt -- cheap) as equivalent to decode tokens
(generated one at a time, sequentially -- expensive). Since the long
prompt sweep has a much higher prefill:decode ratio (3584:512) than
the short sweep (512:256), its `reported_tok_s` is inflated more --
that inflation *is* the "longer prompts give better throughput"
finding. It is a measurement artifact, not a real GPU efficiency gain.

**Honest goodput at batch 24 (report's implied best operating
point), two independent derivations:**

    Method 1 -- generated tokens / wall clock:
        24 x 512 / 61.16 = 200.9 tok/s

    Method 2 -- from steady-state decode latency:
        24 x (1000 / 96.07 ms) = 249.8 tok/s

Both land roughly an order of magnitude below the reported 1607.4
tok/s. (The two methods don't match exactly -- Method 1's wall_clock_s
includes prefill/queuing time that Method 2's steady-state itl
excludes -- but they agree on the order of magnitude, which is the
point.)

**What the report should have said:** `reported_tok_s` conflates
prefill and decode throughput and should never be used for capacity
planning. Real decode goodput at the best long-context operating
point is ~200-250 tok/s, not ~1600. The batch-48 extrapolation to
"~3200 tok/s" is wrong twice over: it linearly extrapolates the wrong
metric, and even that wrong metric falls (to 1298.5) at batch 48 in
the very log being cited -- the report's own data contradicts its
conclusion.

## B4 — Confirming counter

`preempted_seqs` is already in the log and was used to establish the
correlation in B1, so it cannot independently confirm the mechanism.
The mechanism claim is specifically that preempted sequences are
**recomputed**, not swapped to host memory — so the counter that
distinguishes them is the scheduler's **cumulative prefill token
count** (vLLM: `prompt_tokens_total`, or per-iteration prefill tokens
from `iteration_tokens_total`).

If no recompute occurs, prefill tokens for a run must equal
`num_requests × prompt_len` exactly, since each prompt is prefilled
once. If every preempted sequence is recomputed once, the count rises
by `preempted_seqs × prompt_len`.

| batch | no recompute | one recompute per preempted seq | ratio |
|---|---|---|---|
| 24 | 86,016 | 86,016 | 1.00x |
| 32 | 114,688 | 139,776 | **1.22x** |
| 48 | 172,032 | 254,464 | **1.48x** |

Expected observation: ~1.0x at batch 24, and prefill token counts
~1.2x and ~1.5x above the naive figure at batch 32 and 48. A ratio of
exactly 1.00x across all three would falsify the recompute
explanation and point to swap-based preemption instead — in which
case the throughput loss would be PCIe transfer time, not wasted
compute, and the fix would differ.
