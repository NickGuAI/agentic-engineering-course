"""Shared, thread-safe, cross-process budget guard for contract addendum v10
(the n=20 grid). Used by both run_part_a_extend.py (step 1) and
part_b_grid.py (step 2), which run as separate Python processes but must be
checked against the SAME $20.1 target / $24.00 hard stop -- so the ledger is
persisted to evidence/grid_budget.json and re-loaded at start of each script.

This budget covers ONLY the new v10 work (Part A's 20 new 512K/768K items +
Part B's full 60-item grid). It does not include money already spent under
earlier contract versions (Part A's original 32K/128K/256K/512K/768K runs,
the old 3-item Part B demo) -- that is sunk cost from a different budget.

Concurrency: up to 6 pi calls may be in flight at once (contract: "Six
concurrent max"). The hard-stop check must therefore account for calls
already admitted but not yet recorded, not just completed spend -- otherwise
6 calls admitted in the same instant could jointly blow past the stop even
though each one individually looked fine. check_before() reserves an
estimated cost under a lock BEFORE the caller launches the subprocess;
record() (success) or release() (the call was never launched, or errored
before any cost should be attributed) removes that reservation. The
constraint enforced before every admission is:
    completed_spend + sum(reservations in flight) + this_call_estimate <= hard_stop
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

TARGET_USD = 20.1
HARD_STOP_USD = 24.00

# Empirical pricing for openai/gpt-5.6-luna observed directly in
# evidence/part_a/results.json: ~$0.25/M input tokens under 272,000 input
# tokens, ~$0.50/M at or above it (the model's own context-window pricing
# tier -- a single 768K call bills at 2x, $0.38/item, matching this exactly:
# 767000/1e6*0.50 = $0.383). Output priced at ~$1.8/M (part_b_isolate_compress.py's
# same constant), immaterial next to input cost at this scale.
INPUT_RATE_LOW = 0.25
INPUT_RATE_HIGH = 0.50
INPUT_RATE_THRESHOLD = 272_000
OUTPUT_RATE = 1.8


def estimate_call_cost_usd(input_tokens: int, output_tokens_guess: int = 200) -> float:
    rate = INPUT_RATE_HIGH if input_tokens > INPUT_RATE_THRESHOLD else INPUT_RATE_LOW
    return input_tokens / 1e6 * rate + output_tokens_guess / 1e6 * OUTPUT_RATE


class BudgetExceeded(RuntimeError):
    pass


class GridBudget:
    """Persists to `ledger_path` (JSON) so state survives across separate
    script invocations (run_part_a_extend.py, then part_b_grid.py). Every
    process that touches the same ledger_path shares one real spend total."""

    def __init__(self, ledger_path: str, hard_stop: float = HARD_STOP_USD, target: float = TARGET_USD):
        self.ledger_path = Path(ledger_path)
        self.hard_stop = hard_stop
        self.target = target
        self._lock = threading.Lock()
        self._in_flight = {}  # reservation_id -> estimated cost
        self._load()

    def _load(self):
        if self.ledger_path.exists():
            data = json.loads(self.ledger_path.read_text(encoding="utf-8"))
            self.log = data.get("calls", [])
            self.spent = data.get("total_spent_usd", sum(c["cost_usd"] for c in self.log))
        else:
            self.log = []
            self.spent = 0.0
            self._persist()

    def _persist(self):
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger_path.write_text(json.dumps({
            "target_usd": self.target, "hard_stop_usd": self.hard_stop,
            "total_spent_usd": round(self.spent, 6), "n_calls": len(self.log), "calls": self.log,
        }, indent=2), encoding="utf-8")

    def check_before(self, label: str, input_tokens: int, output_tokens_guess: int = 200) -> str:
        """Reserve an estimated cost for one call. Returns a reservation id to
        pass to record()/release(). Raises BudgetExceeded (nothing reserved)
        if admitting this call would project completed+in-flight+this-call
        spend past hard_stop."""
        est = estimate_call_cost_usd(input_tokens, output_tokens_guess)
        with self._lock:
            in_flight_total = sum(self._in_flight.values())
            projected = self.spent + in_flight_total + est
            if projected > self.hard_stop:
                raise BudgetExceeded(
                    f"refusing to submit '{label}' (~{input_tokens:,} est. input tokens, est ${est:.4f}): "
                    f"completed=${self.spent:.4f} + in_flight=${in_flight_total:.4f} + this=${est:.4f} "
                    f"= ${projected:.4f} > hard stop ${self.hard_stop:.2f}."
                )
            rid = uuid.uuid4().hex
            self._in_flight[rid] = est
            return rid

    def record(self, reservation_id: str, label: str, actual_cost_usd: float) -> None:
        with self._lock:
            self._in_flight.pop(reservation_id, None)
            self.spent += actual_cost_usd or 0.0
            self.log.append({
                "label": label, "cost_usd": round(actual_cost_usd or 0.0, 6),
                "running_total_usd": round(self.spent, 6), "ts": time.time(),
            })
            self._persist()
            flag = "  *** OVER TARGET ***" if self.spent > self.target else ""
            print(f"    [budget] {label}: cost=${actual_cost_usd or 0.0:.4f} running_total=${self.spent:.4f}{flag}",
                  flush=True)

    def release(self, reservation_id: str) -> None:
        """Drop a reservation without recording any spend (call was never
        launched, e.g. an earlier BudgetExceeded in the same batch)."""
        with self._lock:
            self._in_flight.pop(reservation_id, None)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "target_usd": self.target, "hard_stop_usd": self.hard_stop,
                "completed_spend_usd": round(self.spent, 6),
                "in_flight_usd": round(sum(self._in_flight.values()), 6),
                "n_calls": len(self.log),
            }
