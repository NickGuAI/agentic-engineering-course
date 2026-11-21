# Daily AI news briefing

`briefing.py` reads the official Anthropic news page and OpenAI RSS feed, selects dated posts from today and yesterday, and writes Markdown, HTML preview, and a run log under `outputs/`. Anthropic summaries use the linked article. OpenAI summaries use the official RSS description because article pages may reject automated requests. Unavailable sources are labeled unavailable. The briefing is capped below 800 words.

Run a preview with `python3 code/briefing.py`. To submit one email per calendar day, set `BRIEFING_TO` to one or two comma-separated addresses in the process environment and run `python3 code/briefing.py --send`. The email contains an HTML body with a plain text fallback. Delivery uses the machine's local `/usr/sbin/sendmail`; it needs to be configured by the machine administrator. No credentials are stored here. A daily marker in `outputs/` prevents a second submission attempt that day. A successful sendmail exit means local submission, not confirmed inbox delivery.

To inspect the email again without changing the daily marker, run `BRIEFING_TO="address@example.com" python3 code/briefing.py --test-send`. This sends immediately, prefixes the subject with `[TEST]`, and writes `outputs/test-send-YYYY-MM-DD.log`. It still requires a runtime recipient address.

`crontab.txt` contains the 8:00 AM New York schedule. It is a schedule template inside this folder; it has not been installed. Before installing it, provide `BRIEFING_TO` through the scheduler's runtime environment and confirm the host cron supports `CRON_TZ` or use an equivalent New York time schedule. The computer must be awake and cron must be running at 8:00 AM.
