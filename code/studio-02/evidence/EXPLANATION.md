# 1. What we ran

This document is a reference example for teaching assistants (TAs) and students. The course tooling produced this file as a validation run for a university course studio ("Studio 02: Context Window Stress Test & Memory Architecture", Computer Science (COMS) W4995-009 Agentic Engineering, Columbia University). It is not written by a real three-person student team.

The test ran on pi. This is an open-source terminal coding agent. We checked its version with the command `pi --version`. The package is `@earendil-works/pi-coding-agent`, version 0.85.1.

The scripts default to the Codex spark model, which is `openai-codex/gpt-5.3-codex-spark`. This happens because the contract asks for that model as the default whenever it exists in pi's catalog. The model does exist under both the `openai-codex` provider and the plain `openai` Application Programming Interface (API) key provider. Its context window is 128,000 tokens.

This default model is untested on the machine used for this validation. The model requires an interactive ChatGPT/Codex login. Our machine does not have this login. The Codex quota of this machine was reported as exhausted anyway.

Every run of real evidence in this folder actually used `google/gemini-3.1-flash-lite`. We passed this model explicitly with the `--model` flag. We used a Google API key set in the environment variable `GEMINI_API_KEY`. Its context window is 1,048,576 tokens.

The instructions said to use the cheapest tool-capable OpenAI model in the `openai` catalog of pi whose context window fits the corpus. We identified `gpt-5-nano` as that model. It has a context window of 400,000 tokens. Its cost is $0.05 per million input tokens.

However, the OpenAI API key on our validation machine had no remaining credits. The agent returned the message "You have no credits remaining".

The instructions said to fall back to Gemini or DeepSeek if OpenAI failed. The DeepSeek API key also failed. The agent returned the message "402 Insufficient Balance".

The first Gemini model we tried was `gemini-2.5-flash-lite`. This model is deprecated. The API error message stated it is "no longer available to new users". The error message recommended `gemini-3.5-flash-lite`.

We used `google/gemini-3.1-flash-lite` instead. This model is cheaper than the recommended replacement. It costs $0.25 per million input tokens and $1.50 per million output tokens. The recommended model `gemini-3.5-flash-lite` costs $0.30 per million input tokens and $2.50 per million output tokens. We confirmed that `google/gemini-3.1-flash-lite` worked with real tool calls before the full run.

The corpus is a paper by Mei et al. 2025. Its title is "A Survey of Context Engineering for Large Language Models" (LLMs). The paper identifier is arXiv 2507.13334. We downloaded it from arXiv. We converted the document to text using `pdftotext`.

The corpus has 70,802 words. This is about 94,167 estimated tokens. We calculated this by multiplying the word count by 1.33. We split the corpus into six section files of about 12,000 words each for Part B.

The paper prose is only about the first third of the extracted text. This prose runs from the introduction through the conclusion. The remaining two-thirds of the text is the bibliography. The survey cites over 1,400 papers.

All five quiz questions come from the prose. They span the abstract, two places in the main body, and the conclusion.

We ran four commands in this specific order. First, we ran `bash setup.sh`.

Second, we ran `python3 part_a_stress.py --model google/gemini-3.1-flash-lite --sizes 8k,16k,32k,64k,full --out evidence`. We also ran this separately with `--sizes 2x,3x` to add two optional larger sizes.

Third, we ran `python3 part_b_isolate_compress.py --model google/gemini-3.1-flash-lite --out evidence`.

Fourth, we ran `python3 part_c_memory.py --model google/gemini-3.1-flash-lite --out evidence --fresh`.

The total real spend on the evidence in this folder was $0.3151. This cost was spread across 69 model calls. This does not count several earlier runs spent finding and fixing real bugs before this evidence was produced. The true total spent today across every run was under $0.70.

# 2. What degraded in Part A, and at what input length

| Size | Estimated Tokens | Real Input Tokens | Score Out of 5 | Questions Wrong or Missing |
| :--- | :--- | :--- | :--- | :--- |
| 8k | ~7,993 | 10,842 | 2 out of 5 | questions 2, 3, 4 wrong |
| 16k | ~16,000 | 21,140 | 3 out of 5 | questions 3, 4 wrong |
| 32k | ~31,997 | 21,248 | 5 out of 5 | none wrong |
| 64k | ~63,994 | 59,652 | 5 out of 5 | none wrong |
| full | ~94,167 | 159,142 | 5 out of 5 | none wrong |
| 2x (optional, not part of default) | ~188,341 | 317,611 | 5 out of 5 | none wrong |
| 3x (optional, not part of default) | ~282,516 | 164,807 real input plus 311,273 real cached tokens (about 476,080 total real tokens) | 5 out of 5 | none wrong |

The 2x and 3x sizes represent the whole corpus followed by extra rounds of distractor padding. The 2x size has one extra round of the corpus's own six section files. The 3x size has two extra rounds of the corpus's own six section files. Each round is reshuffled into a different order and appended as distractor padding.

These optional sizes exist because this model's context window of 1,048,576 tokens is much larger than the full corpus of 159,142 real tokens. The full size alone was never going to threaten it. The 2x and 3x sizes push the total real context to roughly a third and a half of the context window.

Even at 3x, with about 476,080 total tokens of context (real input plus real cached tokens), the score held at a perfect 5 out of 5. A large fraction of that context was padding that the model had already seen once before in a different order.

No degradation and no overflow were observed at this scale on this model. This is a real, informative result. It does not mean context rot cannot happen. It only means that this particular model handled this particular amount and kind of padding without any visible cost to the five-question score.

The score did not drop at any size in this run from 8k through 3x. This means the studio's strict "first failure" rule did not fire. This rule checks for the first size where the score drops below an earlier best, or the call errors.

This does not mean there was no interesting effect. The real reason scores climbed from 8k to 32k is because of where the facts appear in the document. A small slice simply does not contain some facts yet. This is a "not enough context" effect, not "attention failure."

The facts appear at different estimated token points into the document. Question 1 asks how many papers the survey analyzes. Its fact appears at about 330 tokens in the abstract.

Question 5 asks about the four categories of System Implementations. Its fact appears at about 170 tokens in the abstract. It is also restated in the conclusion.

Question 3 asks about Self-Refine's 20% improvement. Its fact appears at about 10,650 tokens. It is restated at three more points later in the document.

Question 2 asks about LongRoPE's 2048K token context window. This fact is stated only once anywhere in the whole document. It appears at about 11,190 tokens.

Question 4 asks about the GAIA benchmark. It mentions 92% human accuracy versus 15% for Generative Pre-trained Transformer 4 (GPT-4). This fact appears at about 29,400 tokens.

This distribution lines up with the observed table. At 8k tokens, only questions 1 and 5 are in the window. This matches the score of 2.

At 16k tokens, question 2 and an earlier restatement of question 3 should be in the window. However, this run's model still missed question 3 at 16k. The model scored 3, not 4. This is a small, real variability that you see in a live model even when the necessary text is technically present.

By 32k tokens, the fact for question 4 is also in the window. The run reached a perfect score. The model held this score at every larger size tested, all the way through 3x.

The real token count reported by pi for the full corpus size was 159,142 tokens. This is notably more than the 94,167-token estimate from the words-times-1.33 rule.

The gap is explained by the corpus's large bibliography of over 1,400 citations. The bibliography tokenizes far less efficiently than ordinary prose. Author names, Digital Object Identifiers (DOIs), and arXiv identifiers (IDs) split into many more tokens per word. The smaller slices of 8k through 64k only cover the prose section. They matched the estimate much more closely.

# 3. Which operation fixed what in Part B

| Method | Score Out of 5 | Tokens in the Final Scored Call | Cost |
| :--- | :--- | :--- | :--- |
| Part A's Best Run (32k) | 5/5 | 21,248 | $0.0074 |
| Isolate | 5/5 | 1,231 | $0.0342 |
| Compress (Summary Artifact) | 5/5 | 910 | $0.0013 |
| Compress (Auto-Compaction) | 4/5 | 17,275 | $0.0300 |

We chose Part A's best run at 32k tokens because it was the smallest run that already scored 5 out of 5. This is true even when counting the optional 2x and 3x sizes, which also scored 5 but used far more tokens.

We did not re-run Part B for this update. This is because Part A's best run is still 32k.

The Isolate and the summary artifact methods both reached full marks. These are both forms of Compress and Select/Write in the lecture's vocabulary. They accomplished this using a small fraction of the tokens that Part A needed.

For the Isolate method, we used one pi sub-agent per corpus section. Each sub-agent returned only short findings. Then one lead pi process answered the questions using only those combined findings. No raw corpus text was passed to the lead process.

For the summary artifact form of Compress, pi wrote a 161-token briefing from the answers of Part A's best run. We then re-asked the five questions using only that briefing.

The auto-compaction form of Compress reached 4 out of 5. It lost exactly question 2, the LongRoPE fact, every single time this was tried.

For this method, the agent read the corpus section files one by one through tool calls. We configured the work directory so compaction would trigger around 50,000 tokens. One compaction fired at 83,909 tokens.

This compaction fired late because pi only checks the threshold between batches of tool calls. In this run, the agent read all six section files back to back before the next check.

Question 2 is the one fact in the entire corpus that is stated only once. The other four facts are each restated at least twice elsewhere in the document.

When pi's compaction summarizes older turns to free up space, a fact that was only ever said once is more likely to be left out of the summary. A fact that keeps reappearing is more likely to survive.

This is a direct, concrete answer to which facts survive the summary. Redundant facts survive. One-off facts do not.

This is the main lesson of Part B. Isolation and compression both recovered the degraded score of the Part A stress test. They did this at a much lower token cost.

However, compression is not free. It can silently drop a fact that was only stated once.

# 4. What the memory file got right and wrong in Part C

The directory `work/part_c/with-memory/` has an `AGENTS.md` file. Its real, repository-relative path is `studio/studio-02/starter/AGENTS.md`. This file tells the agent to check `decisions.md` before starting any task. It also instructs the agent to append a dated entry whenever it makes a decision. It explicitly says to never delete or rewrite entries.

Every pi call in Part C is run with pi's own parent-directory `AGENTS.md` and `CLAUDE.md` discovery turned off. This is done with the `--no-context-files` flag.

This machine has unrelated personal `AGENTS.md` files above the repository root. These files would otherwise be loaded into every call's system prompt. This was confirmed directly to change model behavior. In one earlier attempt, it leaked unrelated personal content into an answer. This is not safe to ship in a public course repository.

To make sure the with-memory condition still reliably receives its `AGENTS.md` instructions, the same text is passed a second way. It is passed via pi's `--append-system-prompt` flag.

Today's real date of 2026-09-17 is read from the system clock in International Organization for Standardization (ISO) format. It is appended to that same system-prompt text because the model has no clock of its own. An earlier run without this fix dated every entry 2025-05-14, which is a plausible-looking but wrong guess.

Session 1 in the with-memory directory was told to plan a small command-line note-taking tool and record three specific decisions, each with a reason. These decisions were the storage format for notes, the command name, and the date format.

Session 1 recorded all three correctly, each dated 2026-09-17. The storage format was Markdown (.md) files. The command name was `memo`. The date format was ISO 8601 (Year-Month-Day, or YYYY-MM-DD).

Session 2 was a separate new pi session in the same directory. We gave it an unrelated task to write `fib.py`, which prints the first 20 Fibonacci numbers. We told it to record at least one decision of its own.

Session 2 added a fourth dated entry about its iterative implementation choice. It did this without disturbing the first three entries.

Session 3 asked what we decided in session 1 about the note-taking tool, and why. In the with-memory directory, it correctly recalled all three decisions. It recalled the storage format, command name, and date format, each with its original reason.

We also asked the identical question in a completely separate, fresh directory with no `AGENTS.md` and no `decisions.md`. This was our memoryless baseline.

The baseline tried many plausible filenames within its own current directory. It tried `README.md`, `notes.md`, `session_1.md`, `decisions.md`, and about two dozen others. It found nothing and correctly said it could not locate any record of session 1. It did not invent an answer.

With memory, 3 of 3 decisions were correctly recalled. Without memory, 0 of 3 decisions were recalled, and the baseline was honest about not knowing.

Getting a clean, honest baseline took two separate fixes, not one.

The first attempt gave the recall-query pi process both a "read" tool and a directory-listing ("ls") tool. Without being told to, the no-memory baseline used "ls" to look around the filesystem. It discovered the sibling with-memory directory and read its `decisions.md` directly. This produced a perfect, word-for-word match. It looked like flawless recall, but the baseline was actually cheating by finding the other run's file.

Removing the "ls" tool and leaving only "read" was not enough by itself. A later attempt showed the no-memory baseline still finding the sibling's `decisions.md` file. It accomplished this by guessing plausible relative paths with plain "read" calls alone.

It climbed one guess at a time all the way up to this project's own `README.md` file, which is three directories up. This file documents the with-memory and no-memory folder layout in plain text. Once it knew the name, the baseline read the sibling directory directly.

The fix that actually closed this off was adding an explicit instruction telling the recall step in both conditions to only use information in its own current working directory. The instruction told the agent not to read, open, or guess the contents of any parent, sibling, or other directory. We delivered this instruction the same way as the date, using the `--append-system-prompt` flag.

This is a genuine, useful lesson about isolation. A capable agent given any file-reading tool at all will try plausible paths. It can climb through parent directories on nothing but plain guesses. This is especially true when a nearby file spells out exactly what to look for.

Giving a sub-agent or session narrow tools is necessary but not sufficient. You may also need to tell it explicitly to stay inside its own working directory.

# 5. What remains unknown

We do not know whether Part A's score would ever show a same-run drop with a smaller or weaker model, or with even more distractor padding than 3x. This is the "context rot" effect from the lecture, where quality falls purely from more surrounding text even though the needed fact is still present. The model `gemini-3.1-flash-lite` held a perfect score through 3x, which is about 476,080 total real tokens and still well under its 1,048,576-token context window. This model and this amount of padding were not enough to trigger the effect. A model with a smaller context window relative to the corpus, or a much larger padding multiplier, would be the natural next thing to try.

We do not know whether a stricter automatic scorer that checks meaning instead of keyword overlap would change any of the Part A or Part B scores. The keyword check in `questions.json` is deliberately simple. It can be fooled by a close paraphrase that drops a required word. It can also miss a correct answer that uses a different word for the same thing. This limitation happened during scoring development. An answer that said "Tool Name: memo" was at one point marked as not recalling the "command name" decision in Part C because the automatic checker was only looking for the phrase "command name".

We do not know whether the same result holds with the Codex subscription model families, such as `gpt-5.3-codex` or `gpt-5.3-codex-spark`. These are now the scripts' default models. They could not be validated on this machine because the ChatGPT/Codex login is an interactive browser flow that cannot complete headlessly. This machine's Codex quota was also reported as exhausted.

We do not know whether pi's automatic compaction would also lose a redundant fact, instead of just a one-off one, if the compaction threshold were set even lower to force more aggressive summarization.

We do not know whether the "stay in your own directory" instruction added to Part C's recall step would hold up against a more determined or more capable model than the one used here. It worked in the runs shipped in this folder. However, it is a prompted instruction and not a hard technical sandbox, so it is not a guarantee.

# 6. Who did what

This document is a reference run produced by the course's own tooling to validate the studio before students run it. It is not a real three-person team submission.

A real team's EXPLANATION.md should replace this section with one paragraph per team member in their own words. Each paragraph should describe specifically what that person built, ran, or checked. This matches the syllabus principle that each student must be able to explain what they built and delivered, since teaching assistants (TAs) spot-check one member per team.
