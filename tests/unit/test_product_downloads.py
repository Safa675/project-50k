from __future__ import annotations

import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from p50k.product.downloads import (
    Counts, DownloadStopped, MAX_REDIRECTS, PacedSession, Response, ResponseError, TEFAS,
    allowed_url, archive_codes,
    atomic_json, cached, download_kap, download_kap_list, download_prices, download_profiles,
    download_spk,
    host_lock, kap_listing, parse_kap_directory, parse_spk_index, profile_links, spk_index_url,
    main, store_response, tefas_envelope, validate_out_root, wait_for_processes,
)


def envelope(rows: list[dict]) -> Response:
    return Response(200, "application/json", json.dumps(
        {"errorCode": None, "errorMessage": None, "resultList": rows}).encode())


class ProductDownloadTests(unittest.TestCase):
    def test_redirect_hops_are_individually_paced_logged_and_bound_to_original_url(self) -> None:
        events = []
        responses = iter([
            Response(302, "text/html", b"", location="/second"),
            Response(301, "text/html", b"", location="https://www.kap.org.tr/final"),
            Response(200, "application/json", b"[]"),
        ])

        def transport(method, url, body, headers):
            events.append(("request", url))
            return next(responses)

        def sleep(seconds):
            events.append(("pause", seconds))

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            session = PacedSession("kap.org.tr", 6, root / "requests.jsonl", transport=transport, sleep=sleep)
            original_url = "https://kap.org.tr/first"
            response = session.request("GET", original_url, validate=kap_listing)
            self.assertIsNotNone(response)
            self.assertEqual(events, [
                ("request", original_url), ("pause", 6),
                ("request", "https://kap.org.tr/second"), ("pause", 6),
                ("request", "https://www.kap.org.tr/final"), ("pause", 6),
            ])
            records = [json.loads(line) for line in (root / "requests.jsonl").read_text().splitlines()]
            self.assertEqual([item["status"] for item in records], [302, 301, 200])
            self.assertEqual(session.requests, 3)
            path = root / "listing.json"
            store_response(path, response, session)
            self.assertTrue(cached(path, kap_listing, expected_url=original_url))
            self.assertFalse(cached(path, kap_listing, expected_url="https://www.kap.org.tr/final"))

    def test_redirect_to_foreign_host_is_never_requested_and_loop_is_bounded(self) -> None:
        calls, pauses = [], []

        def foreign(method, url, body, headers):
            calls.append(url)
            return Response(302, "text/html", b"", location="https://example.invalid/private")

        session = PacedSession("kap.org.tr", 6, transport=foreign, sleep=pauses.append)
        self.assertIsNone(session.request("GET", "https://kap.org.tr/public"))
        self.assertEqual(calls, ["https://kap.org.tr/public"])
        self.assertEqual(pauses, [6])
        calls.clear()
        pauses.clear()

        def loop(method, url, body, headers):
            calls.append(url)
            return Response(302, "text/html", b"", location="/loop")

        session = PacedSession("kap.org.tr", 6, transport=loop, sleep=pauses.append)
        self.assertIsNone(session.request("GET", "https://kap.org.tr/loop"))
        self.assertEqual(len(calls), MAX_REDIRECTS + 1)
        self.assertEqual(pauses, [6] * (MAX_REDIRECTS + 1))

    def test_post_redirect_does_not_silently_change_method_or_drop_payload(self) -> None:
        calls = []

        def transport(method, url, body, headers):
            calls.append((method, body))
            return Response(303, "text/html", b"", location="/different")

        session = PacedSession("tefas.gov.tr", 1.5, transport=transport, sleep=lambda _: None)
        self.assertIsNone(session.request("POST", TEFAS + "/fonProfilBilgiGetir", payload={"fonKodu": "THF"}))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "POST")
        self.assertIsNotNone(calls[0][1])

    def test_pacing_on_success_and_failure_and_stop(self) -> None:
        calls, pauses = [], []

        def transport(method, url, body, headers):
            calls.append(url)
            return Response(503, "text/html", b"unavailable")

        session = PacedSession("kap.org.tr", 6, transport=transport, sleep=pauses.append)
        for _ in range(2):
            self.assertIsNone(session.request("GET", "https://kap.org.tr/example"))
        with self.assertRaises(DownloadStopped):
            session.request("GET", "https://kap.org.tr/example")
        with self.assertRaises(DownloadStopped):
            session.request("GET", "https://kap.org.tr/example")
        self.assertEqual(len(calls), 3)
        self.assertEqual(pauses, [6, 6, 6])

    def test_malformed_success_counts_as_failure(self) -> None:
        session = PacedSession("tefas.gov.tr", 1.5,
                               transport=lambda *args: Response(200, "application/json", b"[]"),
                               sleep=lambda _: None)
        for _ in range(2):
            self.assertIsNone(session.request("POST", "https://www.tefas.gov.tr/api/funds/example",
                                             validate=tefas_envelope))
        with self.assertRaises(DownloadStopped):
            session.request("POST", "https://www.tefas.gov.tr/api/funds/example", validate=tefas_envelope)

    def test_request_log_contains_provenance_without_body_or_exception_message(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / "requests.jsonl"

            def failing(*args):
                raise OSError("do not log this private exception detail")

            session = PacedSession("kap.org.tr", 6, log, transport=failing, sleep=lambda _: None)
            session.request("GET", "https://kap.org.tr/public")
            text = log.read_text(encoding="utf-8")
            self.assertNotIn("private exception detail", text)
            entry = json.loads(text)
            self.assertEqual(entry["error_class"], "OSError")
            self.assertNotIn("body", entry)
            self.assertNotIn("payload", entry)

    def test_success_resets_failure_count(self) -> None:
        responses = iter([Response(500, "text/html", b"x"), envelope([])])
        session = PacedSession("tefas.gov.tr", 1.5, transport=lambda *args: next(responses),
                               sleep=lambda _: None)
        session.request("GET", "https://tefas.gov.tr/example")
        self.assertEqual(session.failures, 1)
        session.request("GET", "https://tefas.gov.tr/example", validate=tefas_envelope)
        self.assertEqual(session.failures, 0)

    def test_unsafe_pace_and_host_are_rejected(self) -> None:
        for host, pace in [("kap.org.tr", 1.5), ("tefas.gov.tr", 0), ("other.example", 6)]:
            with self.assertRaises(ValueError):
                PacedSession(host, pace)
        for url in ["http://kap.org.tr/", "https://kap.org.tr.evil.example/",
                    "https://user:password@kap.org.tr/", "https://kap.org.tr:8443/",
                    "https://kap.org.tr:notaport/", "https://[invalid-ipv6/"]:
            self.assertFalse(allowed_url(url, "kap.org.tr"))
        self.assertTrue(allowed_url("https://www.kap.org.tr/example", "kap.org.tr"))

    def test_profiles_are_atomic_restartable_and_keep_source_bytes(self) -> None:
        calls = []
        response = envelope([{"fonKodu": "THF", "kapLink": "https://kap.org.tr/public"}])

        def transport(*args):
            calls.append(args)
            return response

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            session = PacedSession("tefas.gov.tr", 1.5, transport=transport, sleep=lambda _: None)
            self.assertEqual(download_profiles(session, ["THF"], root), Counts(saved=1))
            self.assertEqual(download_profiles(session, ["THF"], root), Counts(reused=1))
            self.assertEqual(len(calls), 1)
            path = root / "tefas/profiles/THF.json"
            self.assertEqual(path.read_bytes(), response.body)
            self.assertEqual(list(path.parent.glob("*.tmp")), [])
            self.assertTrue(path.with_suffix(".json.meta.json").exists())
            path.with_suffix(".json.meta.json").unlink()
            self.assertFalse(cached(path, tefas_envelope, expected_url=TEFAS + "/fonProfilBilgiGetir",
                                    expected_method="POST"))
            path.write_text("{}", encoding="utf-8")
            self.assertFalse(cached(path, tefas_envelope, expected_url=TEFAS + "/fonProfilBilgiGetir",
                                    expected_method="POST"))

    def test_cache_rejects_matching_bytes_with_wrong_source_method_status_or_payload(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            session = PacedSession("tefas.gov.tr", 1.5, transport=lambda *args: envelope([]),
                                   sleep=lambda _: None)
            download_profiles(session, ["THF"], root)
            path = root / "tefas/profiles/THF.json"
            meta_path = path.with_suffix(".json.meta.json")
            original = json.loads(meta_path.read_text())
            url, payload = TEFAS + "/fonProfilBilgiGetir", {"fonKodu": "THF", "dil": "TR"}
            for alteration in [
                {"url": "https://example.invalid/public"},
                {"url": TEFAS + "/other", "original_url": TEFAS + "/other"},
                {"method": "GET"}, {"status": 503}, {"status": True},
                {"payload_sha256": "different"},
            ]:
                with self.subTest(alteration=alteration):
                    atomic_json(meta_path, {**original, **alteration})
                    self.assertFalse(cached(path, tefas_envelope, expected_url=url,
                                            expected_method="POST", expected_payload=payload))
            atomic_json(meta_path, original)
            self.assertTrue(cached(path, tefas_envelope, expected_url=url,
                                   expected_method="POST", expected_payload=payload))

    def test_direct_tefas_cli_fails_closed_without_legacy_collector_gate(self) -> None:
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as result:
                main(["tefas", "--archive-root", "synthetic-archive"])
        self.assertEqual(result.exception.code, 2)

    @unittest.skipUnless(os.name == "nt", "Windows launcher integration")
    def test_default_launcher_discovers_snapshot_and_does_not_print_command_line(self) -> None:
        launcher = Path(__file__).resolve().parents[2] / "ops/local/start-product-downloads.ps1"
        command = """function Get-CimInstance { param($ClassName, $ErrorAction)
            [PSCustomObject]@{Name='python.exe'; ProcessId=42;
              CommandLine='python.exe -m p50k.jobs.fund_snapshots --db private-command-detail'}
        }
        & '""" + str(launcher).replace("'", "''") + """' -ArchiveRoot 'synthetic-archive'
          -PythonExecutable 'synthetic-python' -DryRun
        """
        # Keep the invocation together; PowerShell does not implicitly continue a new parameter line.
        command = command.replace("'synthetic-archive'\n", "'synthetic-archive' ")
        result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", command],
                                capture_output=True, text=True, check=True)
        records = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        tefas = next(item for item in records if item["Source"] == "tefas")
        self.assertIn("--wait-pid", tefas["Arguments"])
        self.assertIn("42", tefas["Arguments"])
        self.assertNotIn("--no-existing-collector", tefas["Arguments"])
        self.assertNotIn("private-command-detail", result.stdout + result.stderr)

    @unittest.skipUnless(os.name == "nt", "Windows launcher integration")
    def test_launcher_inventory_failure_aborts_without_launching_or_asserting_no_collector(self) -> None:
        launcher = Path(__file__).resolve().parents[2] / "ops/local/start-product-downloads.ps1"
        command = """function Get-CimInstance { param($ClassName, $ErrorAction); throw 'inventory failed' }
        & '""" + str(launcher).replace("'", "''") + """' -ArchiveRoot 'synthetic-archive' -PythonExecutable 'synthetic-python' -DryRun
        """
        result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", command],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("--no-existing-collector", result.stdout)
        self.assertNotIn('"Source"', result.stdout)

    def test_price_refresh_keeps_null_and_decimal_digits(self) -> None:
        response = envelope([{"tarih": "2026-10-01", "fiyat": 0},
                             {"tarih": "2026-10-02", "fiyat": 1.234567}])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            session = PacedSession("tefas.gov.tr", 1.5, transport=lambda *args: response,
                                   sleep=lambda _: None)
            counts = download_prices(session, ["THF"], root)
            self.assertEqual(counts.saved, 1)
            data = json.loads((root / "tefas/prices/THF.json").read_text())
            self.assertEqual(data["periyod"], 12)
            self.assertEqual(data["rows"], [["2026-10-01", None], ["2026-10-02", "1.234567"]])
            self.assertEqual(download_prices(session, ["THF"], root).reused, 1)

    def test_kap_report_list_fetches_only_page_and_list(self) -> None:
        calls = []
        responses = iter([Response(200, "text/html", b'objId":"abcdef0123456789abcdef0123456789"'),
                          Response(200, "application/json", b'[{"disclosureBasic":{"disclosureIndex":123}}]')])

        def transport(method, url, body, headers):
            calls.append(url)
            return next(responses)

        with tempfile.TemporaryDirectory() as folder:
            session = PacedSession("kap.org.tr", 6, transport=transport, sleep=lambda _: None)
            self.assertTrue(download_kap_list(session, "THF", "https://kap.org.tr/public", Path(folder)))
            self.assertEqual(len(calls), 2)
            self.assertTrue(calls[1].endswith("/8aca490d502e34b801502e380044002b/365"))
            self.assertFalse(any("file/download" in url for url in calls))

    def test_profile_mapping_ignores_untrusted_links(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            atomic_json(root / "tefas/profiles/THF.json", {"resultList": [
                {"fonKodu": "THF", "kapLink": "https://kap.org.tr/public"}]})
            atomic_json(root / "tefas/profiles/TP2.json", {"resultList": [
                {"fonKodu": "TP2", "kapLink": "https://example.invalid/private"}]})
            self.assertEqual(profile_links(root / "archive", root), {"THF": "https://kap.org.tr/public"})

    def test_spk_discovers_only_approved_year_and_same_index_pagination(self) -> None:
        url = spk_index_url(2024)
        body = b'''<a href="/data/example/2024-60.pdf">PDF</a>
            <a href="?s=2">Next</a><a href="?s=2">Duplicate</a>
            <a href="https://example.invalid/data/2024-1.pdf">Foreign</a>
            <a href="/data/example/2023-1.pdf">Other year</a>
            <a href="?s=200">Unbounded</a>'''
        pdfs, pages = parse_spk_index(body, url, 2024)
        self.assertEqual(pdfs, ["https://spk.gov.tr/data/example/2024-60.pdf"])
        self.assertEqual(pages, [url + "?s=2"])
        self.assertIn("gecmis-yillara-ait-bultenler", url)
        with self.assertRaises(ValueError):
            spk_index_url(2023)

    def test_spk_download_traverses_pages_and_resumes_pdf_files(self) -> None:
        index = spk_index_url(2026)
        calls = []
        bodies = {
            index: b'<a href="/data/example/2026-2.pdf">PDF</a><a href="?s=2">Next</a>',
            index + "?s=2": b'<a href="/data/example/2026-1.pdf">PDF</a><a href="?s=1">First</a>',
            "https://spk.gov.tr/data/example/2026-1.pdf": b"%PDF-1.7\nsynthetic document",
            "https://spk.gov.tr/data/example/2026-2.pdf": b"%PDF-1.7\nsynthetic document",
        }

        def transport(method, url, body, headers):
            calls.append(url)
            return Response(200, "application/pdf" if url.endswith(".pdf") else "text/html", bodies[url])

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            session = PacedSession("spk.gov.tr", 6, transport=transport, sleep=lambda _: None)
            self.assertEqual(download_spk(session, root, years=[2026]), Counts(saved=2))
            counts = download_spk(session, root, years=[2026])
            self.assertEqual(counts, Counts(reused=2))
            self.assertEqual(sum(url.endswith(".pdf") for url in calls), 2)
            self.assertEqual(len(json.loads((root / "spk/manifest.json").read_text())), 2)

    def test_kap_waiter_reads_new_profiles_and_stops_when_profile_stage_finishes(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            response_list = b'[{"disclosureBasic":{"disclosureIndex":123}}]'
            responses = iter([Response(200, "text/html", b'objId":"abcdef0123456789abcdef0123456789"'),
                              Response(200, "application/json", response_list)])
            waits = []

            def finish_profiles(seconds):
                waits.append(seconds)
                atomic_json(root / "tefas/profiles/THF.json", {"resultList": [
                    {"fonKodu": "THF", "kapLink": "https://kap.org.tr/public"}]})
                atomic_json(root / "status/tefas-profiles.json", {"state": "complete"})

            session = PacedSession("kap.org.tr", 6, transport=lambda *args: next(responses),
                                   sleep=lambda _: None)
            counts = download_kap(session, root / "archive", root, watch=True,
                                  smoke=False, sleep=finish_profiles, use_directory=False)
            self.assertEqual(counts.saved, 1)
            self.assertEqual(waits, [30])
            self.assertEqual(session.requests, 2)

    def test_public_kap_directory_json_excludes_ambiguous_identities(self) -> None:
        records = [
            {"fundCode": "THF", "fundOid": "a" * 32, "title": "Synthetic fund"},
            {"fundCode": "THF", "fundOid": "a" * 32},
            {"fundCode": "TP2", "fundOid": "b" * 32},
            {"fundCode": "TP2", "fundOid": "c" * 32},
            {"fundCode": "TLY", "fundOid": "not-an-identifier"},
        ]
        flight = json.dumps([1, "payload:" + json.dumps(records)])
        html = ("<script>self.__next_f.push(" + flight + ")</script>").encode()
        self.assertEqual(parse_kap_directory(html), {"THF": "a" * 32})

    def test_kap_download_cohort_is_only_authorized_tefas_traded_funds(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            atomic_json(root / "tefas/responses/fonGetiriBazliBilgiGetir_YAT.body", {"resultList": [
                {"fonKodu": "THF", "tefasDurum": True},
                {"fonKodu": "DFI", "tefasDurum": False},
                {"fonKodu": "DOH"},
            ]})
            self.assertEqual(archive_codes(root, tefas_only=True), ["THF"])
            self.assertEqual(archive_codes(root), ["DFI", "DOH", "THF"])

    def test_wait_gate_and_exclusive_host_lock(self) -> None:
        checks, waits = [], []

        def running(pid):
            checks.append(pid)
            return len(checks) == 1

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            wait_for_processes([42], root, running=running, sleep=waits.append)
            self.assertEqual(waits, [30])
            with host_lock(root, "kap.org.tr"):
                with self.assertRaises(OSError):
                    with host_lock(root, "kap.org.tr"):
                        self.fail("duplicate host stream acquired a lock")
            with host_lock(root, "kap.org.tr"):
                pass

    def test_output_cli_guard_rejects_repository_paths(self) -> None:
        with self.assertRaises(ValueError):
            validate_out_root(Path.cwd() / "raw")

    def test_empty_kap_list_is_retained_without_claiming_no_event(self) -> None:
        self.assertEqual(kap_listing(Response(200, "application/json", b"[]")), [])
        with self.assertRaises(ResponseError):
            kap_listing(Response(200, "application/json", b"{}"))


if __name__ == "__main__":
    unittest.main()
