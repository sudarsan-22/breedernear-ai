"""Structured logs: one JSON object per line on stdout, which Cloud Logging reads as a structured entry."""

import json
import sys


def emit(severity: str, **fields) -> None:
    print(json.dumps({"severity": severity, "logger": "breedernear", **fields}, default=str), file=sys.stdout,
          flush=True)
