# BABILong qa1: full curve, 32K to 768K (contract addendum v7)

Extends the existing qa1 curve (32k/128k/256k, n=20 each, from `evidence/benchmark_sweep/`) with two new top-end points at 512K (native BABILong bucket) and 768K (constructed: 1M-bucket items truncated to 768,000 real tokens, keeping only items whose single qa1 supporting fact survives truncation). Same single-message method, same anaphora-fixed prompt, compaction off throughout, so all five points merge into one curve. n=10 at the two new points (marked); n=20 at the three existing points.

**New calls this run: 20/20 scored (2 initial 404s retried and completed; one 502 that still returned a valid, billed, correctly-scored answer was kept as data). Spend this run: $6.2468 (hard stop was $7.00). Wall time (summed, up to 3 concurrent): 2.5 min.**

## Full curve
| bucket | n | mean accuracy | 95% CI | mean real tokens |
| --- | --- | --- | --- | --- |
| 32k | 20 | 85.0% | [68.9%, 100.0%] | 30,549 |
| 128k | 20 | 75.0% | [55.5%, 94.5%] | 122,552 |
| 256k | 20 | 65.0% | [43.6%, 86.4%] | 241,380 |
| **512k** | **10 (new)** | 70.0% | [40.1%, 99.9%] | 481,833 |
| **768k** | **10 (new, constructed)** | 40.0% | [8.0%, 72.0%] | 766,944 |

## Does the 32K -> 768K decline exceed the confidence intervals?
32K mean 85.0% (95% CI [68.9%, 100.0%], n=20) vs. 768K mean 40.0% (95% CI [8.0%, 72.0%], n=10): a 45-point drop. **The two CIs overlap** -- at this n, this decline cannot be distinguished from sampling noise; it is consistent with a real decline but not confirmed by this data alone.

## Needle-depth distributions (both new buckets)
- **512k** (n=10): tokens min=23,738 median=293,247 max=480,498; as a fraction of the SERVED item length: min=0.050 median=0.591 max=0.982
- **768k** (n=10): tokens min=338,941 median=552,308 max=764,670; as a fraction of the SERVED item length: min=0.445 median=0.721 max=0.997

**Selection bias, stated plainly:** the 768K bucket is constructed by truncating 1M-token items and discarding any whose qa1 supporting fact falls after the 768,000-token cut (68/100 1M-bucket items survived this filter; n=10 sampled from those 68, seed 7). This selects for needles in the earlier part of the original document: as a fraction of the ORIGINAL (pre-truncation, ~952K-token median) item length, the surviving needles fall at min=0.355 median=0.580 max=0.799 -- i.e. never beyond ~80% of the way through the original text, by construction. The native 512k bucket carries no such bias (needles range up to 98% of item length -- see the table above). This means the 768K point is not a clean 'same task, longer haystack' comparison to 512k: it is drawn from a population whose needle placement is structurally biased toward the front, which if anything should make 768K *easier* than an unbiased 768K sample would be -- so the observed decline is, if anything, an underestimate of the true effect of length on this task.

See `qa1_curve.png` for the full plotted curve with 95% CI error bars.
