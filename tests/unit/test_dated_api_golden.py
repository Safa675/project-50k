"""Cross-language golden bodies of the dated D1 API (synthetic data only).

The Python API and the frontend Zod contract are checked against one committed
fixture, frontend/tests/fixtures/dated-api-golden.json: this test regenerates the
bodies from a hermetic sealed index and requires them to equal the fixture, and
frontend/tests/dated-api-golden.test.ts validates the same bodies with the browser
schemas and loaders. Set P50K_UPDATE_GOLDEN=1 to rewrite the fixture after an
intended contract change; review the diff before committing it.

Normalisation (machine-specific values only; everything else is the served body):
- every 64-hex value that is derived from absolute temp paths is replaced by
  ``sha256("p50k-golden:" + label)`` so that the placeholder still matches the
  ``^[a-f0-9]{64}$`` contract: ``index`` for the index ID, ``bundle:<date>`` for each
  bundle ID and ``source:<kind>:<fund code or ->:<file name>`` for each source ID,
  inside bodies and request paths alike;
- a source's ``sha256`` becomes ``sha256:<kind>:<fund code or ->:<file name>``, since
  the synthetic price files render floats with the platform's libm;
- ``evidence`` lists and ``sources`` lists are re-sorted by the placeholder IDs,
  because the API sorts both by source ID and the frontend requires that order.
No other value is rewritten; the run has no wall-clock timestamps (the synthetic
snapshot and calibration instants are fixed constants), and any other 64-hex value
must be a content digest listed in the threshold provenance or snapshot.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import unittest

try:
    import httpx2  # noqa: F401 - Starlette's current optional TestClient dependency
    from fastapi.testclient import TestClient
    from p50k.api.dated_app import create_dated_app
except ImportError:
    API_AVAILABLE = False
else:
    API_AVAILABLE = True

from tests.unit.test_dated_research_api import PREFIX, seal_index
from tests.unit.test_fund_review_dated_bundle import CODES, OUTPUT, Workspace

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "frontend/tests/fixtures/dated-api-golden.json"
SCHEMA = "p50k.dated-api-golden.v1"
DATES = ("2025-10-31", "2026-09-16")
# Z00 eligible crossing, Z01 eligible no crossing, Z02 stale, Z99 unavailable without a price.
CODES_SHOWN = ("Z00", "Z01", "Z02", "Z99")
HEX64 = re.compile(r"[a-f0-9]{64}")


def placeholder(label: str) -> str:
    return hashlib.sha256(f"p50k-golden:{label}".encode("utf-8")).hexdigest()


def source_label(source: dict) -> str:
    return f"{source['kind']}:{source['fund_code'] or '-'}:{source['file_name']}"


class Normaliser:
    """Maps the path-derived IDs of one sealed index to stable placeholders."""

    def __init__(self, index: dict, payloads: list[dict]):
        self.ids: dict[str, str] = {index["index_id"]: placeholder("index")}
        for entry in index["entries"]:
            self.ids[entry["bundle_id"]] = placeholder(f"bundle:{entry['date']}")
        labels: dict[str, str] = {}
        for payload in payloads:
            for source in payload["sources"]:
                label = source_label(source)
                if labels.setdefault(label, source["source_id"]) != source["source_id"]:
                    raise AssertionError(f"Two sources share the golden label {label}")
                self.ids[source["source_id"]] = placeholder(f"source:{label}")
        if len(set(self.ids.values())) != len(self.ids):
            raise AssertionError("Golden placeholders are not distinct")
        self.known = {*self.ids.values(), *(placeholder(f"sha256:{label}") for label in labels),
                      index["snapshot"]["projection_sha256"],
                      *(value for key, value in index["threshold_provenance"].items() if key.endswith("_sha256"))}

    def path(self, value: str) -> str:
        for raw, stable in self.ids.items():
            value = value.replace(raw, stable)
        return value

    def body(self, value):
        if isinstance(value, str):
            return self.ids.get(value, value)
        if isinstance(value, list):
            return [self.body(item) for item in value]
        if not isinstance(value, dict):
            return value
        result = {key: self.body(item) for key, item in value.items()}
        if isinstance(result.get("evidence"), list):
            result["evidence"] = sorted(result["evidence"])
        if isinstance(result.get("sources"), list):
            for source in result["sources"]:
                if isinstance(source, dict) and "sha256" in source and "kind" in source:
                    source["sha256"] = placeholder(f"sha256:{source_label(source)}")
            result["sources"] = sorted(result["sources"], key=lambda source: source["source_id"])
        return result

    def unexplained_hex(self, value) -> set[str]:
        """64-hex strings that are neither placeholders nor listed content digests."""
        return set(HEX64.findall(json.dumps(value))) - self.known


def requests_for(index: dict) -> list[dict]:
    bundles = {entry["date"]: entry["bundle_id"] for entry in index["entries"]}
    plan = [{"name": "dates", "kind": "dates", "date": None, "code": None, "path": PREFIX + "/dates"}]
    for day in DATES:
        plan.append({"name": f"summary {day}", "kind": "summary", "date": day, "code": None,
                     "path": f"{PREFIX}/dates/{day}/summary"})
        plan.append({"name": f"funds {day}", "kind": "funds", "date": day, "code": None,
                     "path": f"{PREFIX}/dates/{day}/funds?bundle={bundles[day]}"})
        for code in CODES_SHOWN:
            plan.append({"name": f"detail {day} {code}", "kind": "detail", "date": day, "code": code,
                         "path": f"{PREFIX}/dates/{day}/funds/{code}"})
    plan.append({"name": "error FUND_NOT_FOUND", "kind": "error", "date": DATES[1], "code": "ZZZ",
                 "path": f"{PREFIX}/dates/{DATES[1]}/funds/ZZZ"})
    plan.append({"name": "error CONTEXT_MISMATCH", "kind": "error", "date": DATES[1], "code": None,
                 "path": f"{PREFIX}/dates/{DATES[1]}/summary?bundle={bundles[DATES[0]]}"})
    return plan


def golden_document(responses: list[dict]) -> dict:
    return {"schema": SCHEMA,
            "generator": "tests/unit/test_dated_api_golden.py; P50K_UPDATE_GOLDEN=1 rewrites this file",
            "data": "Synthetic sealed index (codes Z00..Z99, invented values); not TEFAS or KAP data.",
            "normalisation": "Path-derived IDs are sha256('p50k-golden:' + label) placeholders: 'index', "
                             "'bundle:<date>', 'source:<kind>:<fund code or ->:<file name>'; source sha256 "
                             "values use 'sha256:<same label>'; evidence and sources are re-sorted by "
                             "placeholder ID. See the generator's docstring.",
            "responses": responses}


@unittest.skipUnless(API_AVAILABLE, "Optional API dependencies missing; run locked .venv API suite")
class DatedApiGoldenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.space = Workspace(cls.root)
        cls.index, cls.index_dir, cls.payloads = seal_index(cls.space, cls.root / OUTPUT)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def regenerate(self) -> dict:
        normaliser = Normaliser(self.index, self.payloads)
        app = create_dated_app(self.index_dir, universe_codes=frozenset(CODES), repo_root=self.root)
        responses = []
        with TestClient(app, base_url="http://127.0.0.1:8768") as client:
            for request in requests_for(self.index):
                response = client.get(request["path"])
                text = response.text
                self.assertNotIn(str(self.root), text)
                self.assertNotIn(self.root.name, text)
                body = response.json()
                if request["kind"] == "error":
                    self.assertGreaterEqual(response.status_code, 400, request["name"])
                else:
                    self.assertEqual(response.status_code, 200, request["name"])
                normalised = normaliser.body(body)
                self.assertEqual(normaliser.unexplained_hex(normalised), set(), request["name"])
                responses.append({**request, "path": normaliser.path(request["path"]),
                                  "status": response.status_code, "body": normalised})
        return golden_document(responses)

    def test_served_bodies_equal_the_committed_golden_fixture(self):
        document = self.regenerate()
        statuses = [(item["name"], item["status"]) for item in document["responses"]]
        self.assertIn(("error FUND_NOT_FOUND", 404), statuses)
        self.assertIn(("error CONTEXT_MISMATCH", 409), statuses)
        states = {item["body"]["fund"]["d1_state"] for item in document["responses"] if item["kind"] == "detail"}
        self.assertEqual(states, {"ELIGIBLE_CROSSING", "ELIGIBLE_NO_CROSSING", "STALE", "UNAVAILABLE"})
        if os.environ.get("P50K_UPDATE_GOLDEN") == "1":
            FIXTURE.parent.mkdir(parents=True, exist_ok=True)
            FIXTURE.write_bytes((json.dumps(document, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
        self.assertTrue(FIXTURE.is_file(), "Run once with P50K_UPDATE_GOLDEN=1 to create the golden fixture")
        committed = json.loads(FIXTURE.read_bytes().decode("utf-8"))
        self.assertEqual(committed["schema"], SCHEMA)
        self.assertEqual([item["name"] for item in committed["responses"]],
                         [item["name"] for item in document["responses"]])
        for expected, actual in zip(committed["responses"], document["responses"]):
            with self.subTest(expected["name"]):
                self.assertEqual(expected, actual,
                                 "The dated API drifted from the golden fixture; if intended, rerun with "
                                 "P50K_UPDATE_GOLDEN=1 and re-run the frontend golden test")
        self.assertEqual(committed, document)
        self.assertNotIn(b"\r\n", FIXTURE.read_bytes())

    def test_normalisation_is_independent_of_the_temp_path(self):
        # A second sealed index in another temp directory yields identical normalised values.
        with tempfile.TemporaryDirectory() as other:
            space = Workspace(Path(other))
            index, _, payloads = seal_index(space, Path(other) / OUTPUT)
        self.assertNotEqual(index["index_id"], self.index["index_id"])
        first, second = Normaliser(self.index, self.payloads), Normaliser(index, payloads)
        for mine, theirs in zip(self.payloads, payloads):
            fields = ("funds", "sources", "summary", "threshold_provenance", "snapshot")
            self.assertEqual(first.body({key: mine[key] for key in fields}),
                             second.body({key: theirs[key] for key in fields}))
        self.assertEqual(first.body(self.index["entries"]), second.body(index["entries"]))
        self.assertEqual(first.body(self.index["index_id"]), second.body(index["index_id"]))


if __name__ == "__main__":
    unittest.main()
