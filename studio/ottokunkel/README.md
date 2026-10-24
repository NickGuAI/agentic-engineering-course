# AI news job

This folder implements the research update described in `delegation-card.md`. Each pass asks the locally installed Codex CLI to inspect Anthropic News, Anthropic Engineering, OpenAI News, and public first-party posts on X. The wrapper accepts no more than five recent stories and rejects unverified output before publishing it.

## Run one pass

From this folder:

```bash
python3 code/news_job.py once
```

The command writes the briefing, execution trace, stderr log, and run record to `outputs/`. It also updates `outputs/latest.md` only after the response passes validation.

## Run daily while the process is alive

```bash
python3 code/news_job.py loop
```

The foreground process starts each pass at 7:59 a.m. in `America/New_York` and targets publication by 8:01. The one-minute lead comes from the measured live-run time. Daylight-saving changes are handled by the timezone database. Press Ctrl-C or stop the process to end the schedule. The code does not install a cron job, launch agent, login item, or background service.

The wrapper overrides the local profile's reasoning effort to `low` for this narrow scan while retaining the profile's chosen model. Each run record reports `duration_seconds` and `delivery_budget_met` against the 120 seconds between the 7:59 start and the 8:01 deadline. A run that fails, exceeds its 110-second bound, or returns invalid evidence leaves `outputs/latest.md` unchanged.

## Verify

```bash
python3 -m unittest discover -s code -v
```

No API keys belong in this folder. Codex uses the account already configured for the local CLI.
