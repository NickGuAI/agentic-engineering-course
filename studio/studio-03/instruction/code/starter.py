"""Student-owned Responses loop and plan-first condition."""

import json
import shlex
import subprocess
import time

from support import (
    BASH_TOOL,
    FINAL_REPORT_POLICY,
    MAX_OUTPUT_TOKENS,
    MAX_TOOL_OUTPUT,
    TOOL_TIMEOUT_SECONDS,
    prepare_bash_argv,
    tool_environment,
)


def run_agent(question, context):
    """Return the final report text, or None when the run stops."""
    loop_question = question
    if context.mode == "plan":
        plan = context.plan_text
        if plan is None:
            planning_request = {
                "model": context.model,
                "input": [{
                    "role": "user",
                    "content": (
                        "Create a numbered research plan. Do not use tools or answer.\n\n"
                        + question
                    ),
                }],
                "tools": [],
                "tool_choice": "none",
                "parallel_tool_calls": False,
                "store": False,
                "max_output_tokens": MAX_OUTPUT_TOKENS,
                "reasoning": {"effort": "none"},
            }
            # TODO: Count, send, and record this planning request.
            plan_response = None
            # TODO: Stop safely for an incomplete or refused plan.
            plan = ""
            # TODO: Extract and save the numbered plan.
            context.write_plan(plan, "model_generated")
        loop_question = f"Use this plan to research and answer the question.\n\n{plan}\n\n{question}"

    return run_research_loop(loop_question, context)


def run_research_loop(question, context):
    """Run the same sequential tool loop in both conditions."""
    history = [{"role": "user", "content": f"{question}\n\n{FINAL_REPORT_POLICY}"}]
    while True:
        final_only = context.call_budget - context.calls_used == 1
        phase = "final_synthesis" if final_only else "research"
        tools = [] if final_only else [BASH_TOOL]
        tool_choice = "none" if final_only else "auto"
        if final_only:
            history.append({"role": "user", "content": FINAL_REPORT_POLICY})
        request = {
            "model": context.model,
            "input": history,
            "tools": tools,
            "tool_choice": tool_choice,
            "parallel_tool_calls": False,
            "store": False,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "reasoning": {"effort": "none"},
        }
        if not context.start_model_call(phase, request):
            return None
        # TODO: Call client.responses.create and record errors or responses.
        response = None
        # TODO: Stop before dispatch unless status is completed.
        # TODO: Stop if the response contains a refusal.
        # TODO: Preserve response.output in the next request history.
        function_calls = []
        if final_only and function_calls:
            # TODO: Stop and escalate if synthesis asks for a tool.
            return None
        if not function_calls:
            # TODO: Return the final response text.
            return None
        for call in function_calls:
            # TODO: Parse arguments and run the student-owned Bash tool.
            result = ""
            # TODO: Pair each result with that call's call_id.
            history.append({
                "type": "function_call_output",
                "call_id": "",
                "output": result,
            })
    return None


def run_bash(context, command, call_id):
    """Execute one validated research command and save its result."""
    started = time.monotonic()
    try:
        argv = prepare_bash_argv(command)
    except (ValueError, TypeError, IndexError) as error:
        # TODO: Record the rejection with this call_id.
        return ""

    # TODO: Run argv through Bash using shlex.join.
    # TODO: Use filtered env, evidence cwd, and timeout.
    result = None
    # TODO: Handle failures and bound combined output.
    # TODO: Record output, exit code, call_id, and elapsed time.
    return ""
