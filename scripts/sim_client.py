"""A SIMULATED model, used only to exercise the evaluation tooling without an API key.

It starts from the gold answer and injects known kinds of mistakes. Numbers produced from it
say NOTHING about real extraction accuracy - they only show that run_dataset / evaluate /
the confidence scoring react sensibly to errors of known type. Always label such runs SIMULATED.

Injected error types (each with probability `rate` per pass, x3 on scans):
  misread     a line amount is changed in the VALUE but the quoted evidence is left original
              (a transcription slip: caught by value-not-in-evidence + arithmetic)
  wrong_total the total is wrong in both value and quote (caught by arithmetic only)
  swap_date   day/month swapped on an ambiguous date (caught by the ambiguity flag)
  drop_field  a present field reported as null (caught by the absence hint)
  drop_item   a line item is omitted (caught by sum mismatch)
Pass 2 (temperature > 0) draws independent errors, which is what creates disagreement.
"""
from __future__ import annotations

import random
import re
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from co_extract.llm import MockClient  # noqa: E402

DROPPABLE = ["schedule_impact_days", "status", "currency", "reason", "markup_amount", "new_contract_sum"]


class SimClient(MockClient):
    def __init__(self, gold_path, scan: bool = False, rate: float = 0.10, seed: int = 7):
        super().__init__(gold_path)
        self.scan, self.rate, self.seed = scan, rate, seed
        self.name = "SIMULATED model (tooling demo - not a real accuracy measurement)"

    def extract(self, system, document, schema, temperature=0.0):
        out = super().extract(system, document, schema, temperature)
        rng = random.Random(f"{self.seed}-{zlib.crc32(document.encode())}-{temperature}")
        p = min(0.9, self.rate * (3 if self.scan else 1))

        items = out["line_items"]
        if items and rng.random() < p:                                   # misread
            it = rng.choice(items)
            it["amount"] = round(it["amount"] * rng.choice([1.1, 0.9, 10, 0.1]) + rng.choice([0, 1, 100]), 2)
        if out["total"]["value"] is not None and rng.random() < p / 2:   # wrong_total (consistent lie)
            old = out["total"]["value"]
            new = round(old + rng.choice([-500.0, 250.0, 1000.0]), 2)
            out["total"]["value"] = new
            if out["total"]["evidence"]:
                out["total"]["evidence"] = re.sub(re.escape(f"{abs(old):,.2f}"), f"{abs(new):,.2f}", out["total"]["evidence"])
        d = out["co_date"]["value"]
        if d and rng.random() < p * 3:                                   # swap_date (only if swappable)
            y, m, dd = d.split("-")
            if int(dd) <= 12 and dd != m:
                out["co_date"]["value"] = f"{y}-{dd}-{m}"
        if rng.random() < p:                                             # drop_field
            f = rng.choice(DROPPABLE)
            out[f] = {"value": None, "evidence": None}
        if len(items) > 2 and rng.random() < p / 2:                      # drop_item
            items.pop(rng.randrange(len(items)))
        return out
