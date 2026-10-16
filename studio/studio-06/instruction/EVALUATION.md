# Evaluate the six research reports

Use the original [DeepResearchBench RACE evaluator](https://github.com/Ayanami0730/deep_research_bench/tree/f2735b5c3636759c22f9e936c0232de8bf545b67). The revision is fixed so every team uses the same criteria, reference reports, scoring prompts, and weights.

The course helper packages your reports and invokes that evaluator. It does not change the scoring formula or the evaluator's retry and token settings.

## 1. Save one report per task in each mode

Use the exact [three prompts](TASKS.md). The helper expects these example paths under your submission folder:

```text
reports/single/99.md     reports/multi/99.md
reports/single/93.md     reports/multi/93.md
reports/single/100.md    reports/multi/100.md
```

Your own report locations are fine. Copy or map the reports to these paths for the helper, or prepare native JSONL yourself.

Keep your research agents away from the benchmark's reference reports and scoring criteria. The evaluator reads those files after research is complete.

## 2. Install the pinned evaluator

Run these commands from your private course repository root. Replace `your-team` with your team folder.

```bash
TEAM='your-team'
STUDIO='studio/studio-06'
SUBMISSION="$STUDIO/submission/$TEAM"
BENCHMARK="$SUBMISSION/work/deep-research-bench"
PYTHON="$SUBMISSION/work/evaluator-venv/bin/python"

mkdir -p "$SUBMISSION/work"
git clone https://github.com/Ayanami0730/deep_research_bench.git "$BENCHMARK"
git -C "$BENCHMARK" checkout --detach f2735b5c3636759c22f9e936c0232de8bf545b67
python3 -m venv "$SUBMISSION/work/evaluator-venv"
"$PYTHON" -m pip install -r "$BENCHMARK/requirements.txt"
```

Keep this checkout unchanged. The helper verifies its revision and rejects tracked edits, including changes to `utils/api.py`.

## 3. Run RACE with your class OpenAI key

These commands use Bash. Enter your key at the hidden prompt. The key stays in the process environment.

```bash
read -rsp 'Class OpenAI API key: ' OPENAI_API_KEY
export OPENAI_API_KEY

LLM_BACKEND=openai RACE_MODEL=gpt-5.5 CLEAN_MODEL=gpt-5.6-luna \
"$PYTHON" "$STUDIO/instruction/code/evaluate.py" \
  --submission "$SUBMISSION" \
  --benchmark "$BENCHMARK"

unset OPENAI_API_KEY
```

This step makes paid model calls through your class key. The pinned evaluator uses `gpt-5.5` as the judge and `gpt-5.6-luna` to clean reports. It supports OpenAI directly. RACE needs no Jina key.

The helper preserves the native model settings: medium reasoning for scoring and low reasoning for cleaning. Your research agent can use its own model settings.

The helper creates a fresh `eval/race-01/` directory. It packages the reports as `input/single.jsonl` and `input/multi.jsonl`. Each row contains `id`, the original `prompt`, `language: "en"`, and the report in `article`.

It passes the selected three-task query file to RACE. The benchmark matches reports, criteria, and references by exact prompt text.

The helper runs RACE from the benchmark checkout because its criteria and reference paths are relative constants. It uses these native arguments:

| Argument | Value or purpose |
|---|---|
| `target_model` | `single` or `multi`, the input filename stem, not a model API ID |
| `--only_en` | Evaluate the selected English tasks |
| `--query_file` | The exact three-task query JSONL |
| `--raw_data_dir` | This run's packaged report directory |
| `--cleaned_data_dir` | This run's fresh cleaned-report directory |
| `--output_dir` | A separate result directory for each mode |

It leaves `--max_workers` at the native default of 5. Do not use `--skip_cleaning`: in this revision, it also skips scoring.

## 4. Read the six scores

Open these files:

| File under `eval/race-01/` | What it contains |
|---|---|
| `single/raw_results.jsonl` | Three native single-agent scores |
| `multi/raw_results.jsonl` | Three native multi-agent scores |
| `single/race_result.txt`, `multi/race_result.txt` | Native summaries |
| `comparison.csv` | The three score pairs, differences, and means |
| `evaluation.json` | Evaluator revision, source hashes, input hashes, commands, and completion status |

Each raw score row includes `overall_score` and four normalized dimension scores. RACE gives both reports 0–10 scores for each criterion. It applies the original weights to obtain total `T` for your report and total `R` for the official reference report.

When `T + R > 0`, the overall score is `T / (T + R)`. A score of `0.5` means equal weighted totals. If both totals are zero, this evaluator returns zero. For example, `7 / (7 + 8) = 0.4667`.

A higher score is better. It is not a percentage of correct answers.

The native process can exit successfully with missing task scores. Verify exactly three successful expected task IDs in each mode. Check all four dimensions and `overall_score` for missing values. The helper performs these checks before it writes `comparison.csv`.

Compare the three pairs in `EXPLANATION.md`. Link to the original RACE outputs. The CSV is an optional convenience. There is no minimum RACE score.

## If an evaluation fails

Read `single/evaluator.log` or `multi/evaluator.log`. Correct the reported API, dependency, or input problem.

Use a fresh output directory for a new evaluation:

```bash
read -rsp 'Class OpenAI API key: ' OPENAI_API_KEY
export OPENAI_API_KEY
"$PYTHON" "$STUDIO/instruction/code/evaluate.py" \
  --submission "$SUBMISSION" \
  --benchmark "$BENCHMARK" \
  --output "$SUBMISSION/eval/race-02"
unset OPENAI_API_KEY
```

Each new run gets fresh input, cleaned-report, and result paths. Keep separate result directories for single and multi: existing task IDs cause RACE to skip evaluation. Fresh cleaned paths also prevent cached reports from being reused. Do not turn a failed or missing score into zero.

If all six native scores already exist, regenerate the comparison without model calls:

```bash
"$PYTHON" "$STUDIO/instruction/code/evaluate.py" \
  --submission "$SUBMISSION" \
  --output "$SUBMISSION/eval/race-01" \
  --summarize-only
```

Repeated research runs are optional. Give each repeat its own report and evaluation directories, and state which results you compare.

## Upstream source and license

The pinned repository's `LICENSE` file is [Apache 2.0](third-party/DeepResearchBench-LICENSE.txt). The three task records are copied unchanged from its task file. The course helper is separate code that invokes the original evaluator.

- [Original task file](https://github.com/Ayanami0730/deep_research_bench/blob/f2735b5c3636759c22f9e936c0232de8bf545b67/data/prompt_data/query.jsonl)
- [RACE entrypoint](https://github.com/Ayanami0730/deep_research_bench/blob/f2735b5c3636759c22f9e936c0232de8bf545b67/deepresearch_bench_race.py)
- [API and model settings](https://github.com/Ayanami0730/deep_research_bench/blob/f2735b5c3636759c22f9e936c0232de8bf545b67/utils/api.py)
- [Scoring prompt](https://github.com/Ayanami0730/deep_research_bench/blob/f2735b5c3636759c22f9e936c0232de8bf545b67/prompt/score_prompt_en.py)
- [Weighted score calculation](https://github.com/Ayanami0730/deep_research_bench/blob/f2735b5c3636759c22f9e936c0232de8bf545b67/utils/score_calculator.py)
