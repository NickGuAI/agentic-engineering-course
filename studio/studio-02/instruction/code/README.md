- `setup.sh` — prepares the environment: checks prerequisites, downloads the benchmark data, builds the 768K bucket, samples items, and applies the model context-window override.
- `part_a_stress.py` — runs the Part A context-window stress test (single call per item at 256K/512K/768K).
- `plot_qa1_curve.py` — plots the Part A accuracy curve from its results.
- `part_b_isolate_compress.py` — runs Part B's two mitigation strategies (Isolate and Targeted summary) against the same items as Part A.
- `part_c_memory.py` — runs Part C's three-session, file-based memory test against a memoryless baseline.
- `lib/` — shared helper code used by the scripts above.
- `benchmarks/` — the benchmark data and the scripts that build/sample it.
- `part_c/AGENTS.md` — the memory instructions given to the agent during Part C's "with-memory" sessions.

Run scripts from this directory; see `../Studio_Instruction.md` for full instructions.
