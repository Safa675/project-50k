"""The public runner cannot use future calibration for an earlier cutoff."""
from __future__ import annotations

from datetime import timedelta
from unittest import TestCase
from unittest.mock import patch

from p50k.product.detector_runner import CALIBRATION_CUTOFF, run


class DetectorRunnerTests(TestCase):
    def test_prior_cutoff_is_rejected_before_any_database_call(self) -> None:
        with patch("p50k.product.detector_runner.run_detectors") as compute:
            with self.assertRaises(ValueError):
                run(None, CALIBRATION_CUTOFF - timedelta(microseconds=1), "HISTORICAL_REPLAY")
            compute.assert_not_called()

    def test_calibration_boundary_passes_to_immutable_runtime(self) -> None:
        with patch("p50k.product.detector_runner.run_detectors", return_value={"reused": True}) as compute:
            self.assertEqual(run(None, CALIBRATION_CUTOFF, "HISTORICAL_REPLAY"), {"reused": True})
            compute.assert_called_once_with(None, CALIBRATION_CUTOFF, "HISTORICAL_REPLAY")
