"""Publication-safe entry point around the immutable calibrated v2 runtime."""
from __future__ import annotations

from datetime import datetime
from typing import Any

import psycopg

from p50k.product.detector_pipeline import CALIBRATION_CUTOFF, run_detectors


def run(connection: psycopg.Connection, cutoff: datetime, origin: str = "DELAYED") -> dict[str, Any]:
    # A calibrated version must not be used to describe a date preceding its
    # complete reference window. The calibrated implementation stays unchanged.
    if cutoff.tzinfo is None or cutoff < CALIBRATION_CUTOFF:
        raise ValueError("Cutoff precedes the fixed calibration window")
    return run_detectors(connection, cutoff, origin)
