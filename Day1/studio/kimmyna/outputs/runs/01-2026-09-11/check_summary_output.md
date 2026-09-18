# check_summary.py output — lecture 01 (2026-09-11, session 2)

Command actually run (see note below):

    python3 ../code/scripts/check_summary.py 01

Exit code: **0** (pass)

Note: `spot_check_sample` is a random sample drawn fresh on each invocation, so it
differs between runs. The block below and `check_summary_report.md` in this directory
come from the same, final invocation and are the authoritative sample.

```json
{
  "lecture": "01",
  "passed": true,
  "coverage_missing": [],
  "traceability_untagged": [],
  "traceability_untagged_count": 0,
  "flow": {
    "exists": true,
    "missing_core": [],
    "order_ok": true,
    "missing_page_tags": []
  },
  "spot_check_sample": [
    "also want to apply Pruning to make the search space smaller [p.12]",
    "- Its time and space complexity is 𝑂(𝑏^(1+⌊𝐶*/𝜖⌋)) [p.21]",
    "**Depth-First Search** [p.14] makes it a stack an",
    "different amounts. **Uniform-Cost Search** [p.19] closes the lecture ",
    "h-Limited Search prevents DFS from going past a set depth 𝑙 [p.18]"
  ]
}
```

## Note on the command path

PROMPT.md specifies `python3 scripts/check_summary.py 01`, and `.claude/settings.json`
allow-lists that exact prefix. In this repository, however, `scripts/` lives under
`code/` while `approved/`, `summaries/` and `course-materials/` live under `outputs/`.
The checker resolves `approved/` and `summaries/` relative to the current working
directory, so it must be run with cwd = `outputs/`, where `scripts/` does not exist.

Resolution: run the same unmodified file via `../code/scripts/check_summary.py` with cwd
= `outputs/`. No file under `scripts/` was created, modified, moved, or symlinked, and no
alternative `scripts/` directory was created inside the run root. The checker's behaviour
is identical; only the path used to invoke it differs.
