"""Offline failure/resume tests. Run: python -m unittest discover -s . -v"""
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import unquote

import crw_downloader as crw


class DownloaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "fixture.csv"

    def fixture(self, year=2005, cell="northern"):
        return [crw.HEADER.copy(), crw.UNITS.copy()] + [
            [day + "T12:00:00Z", *crw.CELLS[cell], "0.0", "0", "0.0", "0", "25.2", "0.1", "0"]
            for day in crw.expected_dates(year)]

    def write(self, rows, path=None):
        path = path or self.path
        with path.open("w", encoding="utf-8", newline="") as stream:
            csv.writer(stream).writerows(rows)
        return path

    def check(self, rows, year=2005, allow=False):
        self.write(rows)
        return crw.validate_csv(self.path, "northern", year, allow)

    def test_normal_and_leap_year_raw_preservation(self):
        for year, expected in [(2005, 365), (2004, 366)]:
            self.write(self.fixture(year))
            before = self.path.read_bytes()
            result = crw.validate_csv(self.path, "northern", year)
            self.assertTrue(result["complete"], result)
            self.assertEqual(result["rows"], expected)
            self.assertEqual(self.path.read_bytes(), before)

    def test_missing_day_requires_explicit_policy(self):
        rows = self.fixture(2004)
        del rows[61]  # February 29
        result = self.check(rows, 2004)
        self.assertFalse(result["valid"])
        self.assertEqual(result["missing_dates"], ["2004-02-29"])
        allowed = self.check(rows, 2004, True)
        self.assertTrue(allowed["valid"])
        self.assertFalse(allowed["complete"])

    def test_duplicate_cannot_hide_missing_day(self):
        rows = self.fixture()
        rows[10] = rows[9].copy()
        for allow in (False, True):
            result = self.check(rows, allow=allow)
            self.assertFalse(result["valid"])
            self.assertEqual(len(result["duplicate_dates"]), 1)
            self.assertEqual(len(result["missing_dates"]), 1)

    def test_wrong_coordinate_even_single_row(self):
        for coordinate, value in [(1, "20.225"), (2, "-155.874999"), (1, "NaN")]:
            rows = self.fixture()
            rows[100][coordinate] = value
            self.assertFalse(self.check(rows)["valid"])

    def test_missing_variable_units_row_and_wrong_units(self):
        rows = self.fixture()
        self.assertFalse(self.check([r[:-1] for r in rows])["valid"])
        self.assertFalse(self.check([rows[0], *rows[2:]])["valid"])
        rows[1][7] = "Kelvin"
        self.assertFalse(self.check(rows)["valid"])

    def test_bad_width_time_order_year_and_numeric(self):
        for index, value in [(0, "2005-01-01T00:00:00Z"), (0, "2006-01-01T12:00:00Z"),
                             (7, "garbage"), (7, "inf"), (4, "3")]:
            rows = self.fixture()
            rows[2][index] = value
            self.assertFalse(self.check(rows)["valid"])
        rows = self.fixture()
        rows[4].append("extra")
        self.assertFalse(self.check(rows)["valid"])
        rows = self.fixture()
        rows[4], rows[5] = rows[5], rows[4]
        self.assertFalse(self.check(rows)["valid"])

    def test_missing_measurements_and_masks_reported(self):
        rows = self.fixture()
        rows[2][7], rows[2][4] = "NaN", "1"
        result = self.check(rows)
        self.assertTrue(result["complete"])
        self.assertEqual(result["missing_values"]["CRW_SST"], 1)
        self.assertEqual(result["mask_counts"]["CRW_DHW_mask"]["1"], 1)
        self.assertTrue(result["warnings"])

    def test_html_empty_and_header_only_rejected(self):
        for payload in ("<html>Service unavailable</html>", "", "Error { message=bad; }"):
            self.path.write_text(payload)
            self.assertFalse(crw.validate_csv(self.path, "northern", 2005)["valid"])
        self.assertFalse(self.check(self.fixture()[:2], allow=True)["valid"])

    def test_url_all_cells_and_full_scope(self):
        for cell, (lat, lon) in crw.CELLS.items():
            url = unquote(crw.build_url(cell, 2004))
            for variable in crw.VARIABLES:
                self.assertIn(f"{variable}[(2004-01-01T12:00:00Z):1:(2004-12-31T12:00:00Z)]"
                              f"[({lat}):1:({lat})][({lon}):1:({lon})]", url)
        args = crw.parse_args(["--full"])
        self.assertEqual(len(args.years) * len(args.cells), 69)

    def args(self, *extra):
        return crw.parse_args(["--output", str(self.root), "--pause", "0", "--backoff", "0", *extra])

    def successful_fetch(self, url, path, timeout):
        self.write(self.fixture(), path)
        return {"final_url": url}

    def test_retry_download_and_skip_without_network(self):
        calls = 0

        def flaky(url, path, timeout):
            nonlocal calls
            calls += 1
            if calls == 1:
                path.write_bytes(b"incomplete")
                raise URLError("simulated disconnect")
            return self.successful_fetch(url, path, timeout)

        with patch.object(crw, "fetch", side_effect=flaky), patch.object(crw.time, "sleep") as sleep:
            result = crw.process(self.root, "northern", 2005, self.args())
        self.assertEqual(result["status"], "downloaded")
        self.assertEqual(calls, 2)
        sleep.assert_called_once()
        self.assertTrue(list((self.root / "rejected").iterdir()))
        with patch.object(crw, "fetch", side_effect=AssertionError("network must not be called")):
            skipped = crw.process(self.root, "northern", 2005, self.args())
        self.assertEqual(skipped["status"], "skipped_valid")
        self.assertEqual(skipped["checksum"], result["checksum"])

    def test_invalid_existing_preserved_then_replaced(self):
        path = self.root / "northern" / "crw_northern_2005.csv"
        path.parent.mkdir()
        path.write_bytes(b"old schema")
        with patch.object(crw, "fetch", side_effect=self.successful_fetch):
            result = crw.process(self.root, "northern", 2005, self.args())
        self.assertEqual(Path(result["previous_invalid_file"]).read_bytes(), b"old schema")
        self.assertEqual(result["status"], "downloaded")

    def test_invalid_payload_retried_and_never_promoted(self):
        def bad_fetch(url, path, timeout):
            self.write(self.fixture()[:-1], path)
            return {}
        with patch.object(crw, "fetch", side_effect=bad_fetch), patch.object(crw.time, "sleep"):
            result = crw.process(self.root, "northern", 2005, self.args("--attempts", "2"))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["missing_dates"], ["2005-12-31"])
        self.assertFalse(Path(result["file_path"]).exists())
        self.assertEqual(len(result["attempts"]), 2)

    def test_manifest_resume_retains_prior_entries_and_lock(self):
        with patch.object(crw, "fetch", side_effect=self.successful_fetch):
            self.assertEqual(crw.main(["--output", str(self.root)]), 0)
        with patch.object(crw, "fetch", side_effect=AssertionError("no network")):
            self.assertEqual(crw.main(["--output", str(self.root)]), 0)
        manifest = json.loads((self.root / "manifest.json").read_text())
        self.assertEqual(manifest["files"][0]["status"], "skipped_valid")
        self.assertFalse((self.root / ".download.lock").exists())
        (self.root / ".download.lock").write_text("test")
        self.assertEqual(crw.main(["--output", str(self.root)]), 2)

    def test_http_400_no_retry_and_retry_after(self):
        exc = HTTPError(crw.BASE, 400, "Bad Request", {}, io.BytesIO())
        with patch.object(crw, "fetch", side_effect=exc) as fetch:
            result = crw.process(self.root, "northern", 2005, self.args())
        self.assertEqual(result["status"], "failed")
        self.assertEqual(fetch.call_count, 1)
        throttled = HTTPError(crw.BASE, 429, "Slow down", {"Retry-After": "75"}, io.BytesIO())
        self.assertGreaterEqual(crw.retry_delay(1, 2, throttled), 75)


if __name__ == "__main__":
    unittest.main()
