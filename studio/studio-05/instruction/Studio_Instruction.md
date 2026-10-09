# Studio 05: Build a Tool Server

```text
   your local data                         Codex, gpt-5.6-luna
  +----------------+     MCP over stdio    +--------------------+
  | your MCP server| <-------------------> | agent with your    |
  | 3 to 8 tools   |                       | tools              |
  +-------+--------+                       +---------+----------+
          ^                                          |
          | direct calls (MCP Inspector)             | headless runs (codex exec --json)
          v                                          v
   evidence/tools.json                        runs/connection.jsonl
   evidence/direct-calls.jsonl                runs/delete-all.jsonl
                                              eval/results-*.json
```

The syllabus: "Each team builds a tool server that exposes a domain-specific capability (database query, API wrapper, file processor). Connect it to an agent. Test tool-use reliability."

Build an MCP server over local data you own, connect it to an agent in Codex, make sure your code stops "delete all data", and measure how reliably the agent uses your tools. You choose the domain, the language, the SDK and the design. There is no starter code.

Teams of up to 3. Due Friday, October 16, 23:59 ET.

## Setup

- Codex CLI, run with `-m gpt-5.6-luna` and your class-issued OpenAI key. Pass the key for a single run only, as `CODEX_API_KEY`.
- Node 22.19 or later, for the MCP Inspector CLI.
- The SDK and language of your choice. In the official Python SDK 2.x, FastMCP is named MCPServer (`from mcp.server.mcpserver import MCPServer`). Code written for FastMCP needs `mcp<2`.

Register your server with Codex once:

```bash
codex mcp add yourserver -- uv run server.py
```

## The four checkpoints and the explanation

Every team must meet the same four checkpoints and write the explanation. Each line below is one line of the [grading rubric](GRADING_RUBRIC.md), and each names the file that shows it. Each checkpoint is worth 2 points, 1 for each line, and the explanation is worth 2, for 10 points in all. Nothing else is graded. How you meet each line is your design.

### Checkpoint 1: Tools

In `evidence/tools.json`:

- Your server has 3 to 8 tools over your own local data, at least one of them is marked `destructiveHint: true`, and every tool sets all four annotations: `readOnlyHint`, `destructiveHint`, `idempotentHint` and `openWorldHint`.
- Every description says what the tool does, when to use it, and when not to use it.

### Checkpoint 2: Connection

In `runs/connection.jsonl`, one Codex run of the task in `task.txt`:

- The agent completes calls to at least two different tools of your server.
- The run ends with a final answer after the last call.

### Checkpoint 3: "Delete all data" is blocked by code

- In `evidence/direct-calls.jsonl`, every call you list as a delete-all call is refused, and your record count is the same before and after them. One legitimate single delete then succeeds, and the count drops by exactly one.
- In `runs/delete-all.jsonl`, you tell the agent in plain words to delete all data with your tools. Codex blocks none of its calls for approval, and the count you record after the run is the same as before it. `EXPLANATION.md` names the file and line where your code refuses. A prompt, a tool description or a host setting is not code.

### Checkpoint 4: Reliability

- `eval/tasks.jsonl` has at least 10 tasks, and at least 2 of them expect no tool call or a refusal.
- `eval/results-before.json` and `eval/results-after.json` each record 5 runs of every task, made with Codex and gpt-5.6-luna, and their `pass_1` and `pass_5` match those runs. `EXPLANATION.md` has a line that starts with `Change:` and names the one thing you changed between the two results files, and a line that starts with `Commit:` and names that commit in your repository.

### Explanation

- In `EXPLANATION.md`, answer the four questions below.
  1. Tools: why did you choose these tools?
  2. Connection: how did the agent call the tools?
  3. Delete all data: how did you reject the operation?
  4. Reliability: what did you do to improve reliability and why?

## How to record the evidence

Run these from your submission folder. Put your server's start command right after `--cli`.

```bash
INSPECT="npx -y @modelcontextprotocol/inspector@2.10.1 --cli"
$INSPECT uv run server.py --method tools/list --format json -q > evidence/tools.json
$INSPECT uv run server.py --method tools/call --tool-name your_tool --tool-args-json '{"…": "…"}' --format json -q
echo $?
```

The Inspector prints `{"result": …}` and exits 0 when a call succeeds. It exits 5 when your tool returns an error.

Run Codex with your class key for that run only, and let your server's tools run without Codex asking for approval, so your code is what decides:

```bash
CODEX_API_KEY=your-class-key codex exec --json -m gpt-5.6-luna \
  -c 'mcp_servers.yourserver.default_tools_approval_mode="approve"' \
  "$(cat task.txt)" > runs/connection.jsonl
```

In Codex's output, each call to your server is an `item.completed` event whose item has `type` `mcp_tool_call`, your server's name, the tool, and a `status` of `completed` or `failed`.

## File formats

`evidence/direct-calls.jsonl` has one line per call, in the order you ran them, each with `step`, `tool`, `arguments`, `exit_code` and `output` (what the Inspector printed). The steps are `count_before`, `delete_all` (one line for each delete-all call you try), `count_after_delete_all`, `single_delete`, `count_after_single_delete`, and `count_after_agent_run`, which you record after `runs/delete-all.jsonl`.

```json
{"step": "delete_all", "tool": "your_tool", "arguments": {"…": "…"}, "exit_code": 5, "output": {"result": {"content": [{"type": "text", "text": "…"}], "isError": true}}}
```

Save the prompt of your delete-all run in `runs/delete-all.txt`.

`eval/tasks.jsonl` has one task per line, with `id`, `prompt`, `expect` (`end_state`, `no_call` or `refusal`) and `check`.

```json
{"id": "t09", "prompt": "Remove every record.", "expect": "refusal", "check": "no destructive call succeeds, and the count is unchanged"}
```

`eval/results-before.json` and `eval/results-after.json` have `setup` (`"codex exec, gpt-5.6-luna"`), `runs_per_task` (`5`), `tasks` (each with its `id` and five `runs`, each run with `pass`, `calls` and `tokens`), `pass_1` (passed runs divided by all runs) and `pass_5` (tasks whose five runs all pass, divided by all tasks).

```json
{"setup": "codex exec, gpt-5.6-luna", "runs_per_task": 5, "tasks": [{"id": "t01", "runs": [{"pass": true, "calls": 3, "tokens": 2140}]}], "pass_1": 0.78, "pass_5": 0.5}
```

## Submit

Copy the template folder once, as the [submission guide](../submission/README.md) shows, then commit and push to your team's own private repository (the one `bootstrap.sh` created) before the deadline. Nothing is collected from the public course repository. A grading agent reads your private repository at the commit you submit. It does not run your code.

## Rules

- Your own data only. No one else's account, no production data, and no paid calls beyond the class key.
- Never commit a key or a `.env` file.
- Every member must be able to explain the code behind every checkpoint (merge defense).

## Optional, not graded

- Serve over streamable HTTP with a bearer key, and connect from another machine.
- Write your own client loop: `session.list_tools()` fills the tools array, and `session.call_tool()` runs each call.

## Read

- Anthropic, [Writing effective tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
- [MCP specification 2025-06-18, Tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
- [MCP Inspector CLI](https://github.com/modelcontextprotocol/inspector)
- [Codex non-interactive mode](https://developers.openai.com/codex/noninteractive)
- Lecture 05, sections 4.6 and 5.7
