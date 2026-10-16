#!/usr/bin/env python3
"""Download and validate daily PacIOOS dhw_5km single-cell CSVs (stdlib only)."""
from __future__ import annotations

import argparse
import csv
import hashlib
import http.client
import json
import math
import os
import random
import re
import sys
import time
import uuid
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from email.utils import parsedate_to_datetime

BASE = "https://pae-paha.pacioos.hawaii.edu/erddap/griddap/dhw_5km.csv"
METADATA = "https://pae-paha.pacioos.hawaii.edu/erddap/info/dhw_5km/index.html"
CELLS = {
    "northern": ("20.275", "-155.875"),
    "southern_offshore": ("19.225", "-155.925"),
    "southern_nearshore": ("19.225", "-155.875"),
}
VARIABLES = ["CRW_DHW", "CRW_DHW_mask", "CRW_HOTSPOT", "CRW_HOTSPOT_mask",
             "CRW_SST", "CRW_SSTANOMALY", "CRW_SSTANOMALY_mask"]
HEADER = ["time", "latitude", "longitude", *VARIABLES]
UNITS = ["UTC", "degrees_north", "degrees_east", "Celsius weeks", "1",
         "Celsius", "1", "Celsius", "Celsius", "1"]
MAX_BYTES = 5 * 1024 * 1024


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def build_url(cell, year):
    lat, lon = CELLS[cell]
    selection = (f"[({year}-01-01T12:00:00Z):1:({year}-12-31T12:00:00Z)]"
                 f"[({lat}):1:({lat})][({lon}):1:({lon})]")
    return BASE + "?" + quote(",".join(v + selection for v in VARIABLES), safe="(),:-")


def expected_dates(year):
    start, end = date(year, 1, 1), date(year + 1, 1, 1)
    return [(start + timedelta(days=i)).isoformat() for i in range((end-start).days)]


def checksum(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate_csv(path, cell, year, allow_missing=False):
    """Read without rewriting raw bytes. A valid calendar does not imply usable ML data."""
    expected = set(expected_dates(year))
    dates, errors = [], []
    nulls = {v: 0 for v in VARIABLES}
    masks = {v: Counter() for v in VARIABLES if v.endswith("_mask")}
    result = dict(valid=False, complete=False, rows=0, expected_rows=len(expected),
                  start=None, end=None, missing_dates=sorted(expected), duplicate_dates=[],
                  unexpected_dates=[], errors=errors, units=None,
                  missing_values=nulls, mask_counts={}, warnings=[])

    def error(message):
        # Bound malformed-payload diagnostics; never silently accept additional errors.
        if len(errors) < 50:
            errors.append(message)

    try:
        if path.stat().st_size > MAX_BYTES:
            raise ValueError(f"file exceeds {MAX_BYTES} byte single-cell limit")
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream, strict=True)
            header = next(reader, None)
            units = next(reader, None)
            if header != HEADER:
                raise ValueError(f"expected exact column header/order {HEADER}; got {header}")
            result["units"] = units
            if units != UNITS:
                raise ValueError(f"expected ERDDAP units row {UNITS}; got {units}")
            previous = None
            for line, row in enumerate(reader, start=3):
                result["rows"] += 1
                if len(row) != len(HEADER):
                    error(f"line {line}: expected {len(HEADER)} fields, got {len(row)}")
                    continue
                try:
                    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T12:00:00Z", row[0]):
                        raise ValueError("expected daily 12:00:00Z timestamp")
                    day = date.fromisoformat(row[0][:10]).isoformat()
                    dates.append(day)
                    if previous is not None and day <= previous:
                        error(f"line {line}: timestamps must increase strictly")
                    previous = day
                except ValueError as exc:
                    error(f"line {line}: invalid time: {exc}")
                try:
                    # Decimal equality enforces the exact requested cell, no nearest-cell tolerance.
                    if any(Decimal(raw) != Decimal(want)
                           for raw, want in zip(row[1:3], CELLS[cell])):
                        raise ValueError("coordinates do not equal requested single cell")
                except (InvalidOperation, ValueError) as exc:
                    error(f"line {line}: invalid coordinates: {exc}")
                for variable, raw in zip(VARIABLES, row[3:]):
                    try:
                        if raw.strip().lower() in ("", "nan"):
                            nulls[variable] += 1
                            continue
                        number = float(raw)
                        if not math.isfinite(number):
                            raise ValueError("infinite value")
                        if variable.endswith("_mask"):
                            if number not in (0, 1, 2, 4, 251):
                                raise ValueError("unrecognized mask code")
                            masks[variable][str(int(number))] += 1
                            if number == 251:
                                nulls[variable] += 1
                        elif number == -327.68:
                            nulls[variable] += 1
                    except ValueError as exc:
                        error(f"line {line}: invalid {variable}: {exc}")
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        error(str(exc))
    counts = Counter(dates)
    result.update(start=min(dates) if dates else None, end=max(dates) if dates else None,
                  missing_dates=sorted(expected - counts.keys()),
                  duplicate_dates=sorted(d for d, n in counts.items() if n > 1),
                  unexpected_dates=sorted(counts.keys() - expected),
                  mask_counts={v: dict(c) for v, c in masks.items()})
    if not dates:
        error("no valid daily records")
    if result["duplicate_dates"]:
        error("duplicate dates")
    if result["unexpected_dates"]:
        error("dates outside requested year")
    if result["missing_dates"] and not allow_missing:
        error(f"{len(result['missing_dates'])} missing dates (strict policy)")
    if not allow_missing and result["rows"] != len(expected):
        error(f"expected {len(expected)} data rows; got {result['rows']}")
    if any(nulls.values()) or any(any(k != "0" for k in c) for c in masks.values()):
        result["warnings"].append("Missing values or non-water masks: review before modeling.")
    result["valid"] = not errors
    result["complete"] = not errors and not result["missing_dates"]
    return result


def atomic_json(path, value):
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def log_attempt(root, record):
    with (root / "attempts.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def fetch(url, destination, timeout):
    request = Request(url, headers={"User-Agent": "CRW-single-cell-downloader/1.0",
                                    "Accept": "text/csv", "Accept-Encoding": "identity"})
    with urlopen(request, timeout=timeout) as response, destination.open("xb") as stream:
        if not response.url.startswith("https://"):
            raise ValueError("refusing non-HTTPS response")
        total = 0
        while block := response.read(65536):
            total += len(block)
            if total > MAX_BYTES:
                raise ValueError("response too large for a single cell-year")
            stream.write(block)
        length = response.headers.get("Content-Length")
        if length is not None and total != int(length):
            raise ValueError("response length differs from Content-Length")
        stream.flush()
        os.fsync(stream.fileno())
        return {"final_url": response.url, "content_type": response.headers.get("Content-Type"),
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"), "bytes": total}


def retry_delay(attempt, backoff, exc):
    delay = min(60.0, backoff * 2 ** (attempt - 1) + random.uniform(0, 1))
    if isinstance(exc, HTTPError):
        retry_after = exc.headers.get("Retry-After") if exc.headers else None
        if retry_after:
            try:
                requested = float(retry_after)
            except ValueError:
                try:
                    requested = (parsedate_to_datetime(retry_after) -
                                 datetime.now(timezone.utc)).total_seconds()
                except (TypeError, ValueError):
                    requested = 0
            if math.isfinite(requested):
                delay = max(delay, requested)
    return max(0, delay)


def process(root, cell, year, args):
    path = root / cell / f"crw_{cell}_{year}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    url = build_url(cell, year)
    base = dict(cell=cell, year=year, latitude=CELLS[cell][0], longitude=CELLS[cell][1],
                url=url, file_path=str(path.resolve()), checksum=None, checksum_algorithm="sha256",
                checked_at=utc_now(), allow_missing_dates=args.allow_missing_dates, attempts=[])
    if path.exists():
        validation = validate_csv(path, cell, year, args.allow_missing_dates)
        if validation["valid"]:
            return dict(base, **validation, status=("skipped_valid" if validation["complete"]
                        else "skipped_with_missing_dates"), checksum=checksum(path))
        # Retain earlier/partial-schema bytes instead of destroying them.
        saved = root / "rejected" / (path.name + ".existing." + uuid.uuid4().hex)
        saved.parent.mkdir(exist_ok=True)
        path.rename(saved)
        log_attempt(root, dict(cell=cell, year=year, event="existing_invalid", at=utc_now(),
                              file_path=str(saved), checksum=checksum(saved), validation=validation))
        base["previous_invalid_file"] = str(saved)
    for attempt in range(1, args.attempts + 1):
        partial = path.with_name(path.name + "." + uuid.uuid4().hex + ".part")
        record = dict(cell=cell, year=year, attempt=attempt, at=utc_now(), url=url,
                      file_path=str(partial), event="started")
        log_attempt(root, record)
        validation = None
        try:
            response = fetch(url, partial, args.timeout)
            validation = validate_csv(partial, cell, year, args.allow_missing_dates)
            if not validation["valid"]:
                raise ValueError("CSV validation failed: " + "; ".join(validation["errors"][:5]))
            digest = checksum(partial)
            # Atomic no-replace promotion on the same filesystem; fails if a final file exists.
            os.link(partial, path)
            partial.unlink()
            record.update(event="downloaded", file_path=str(path), checksum=digest,
                          validation=validation, response=response)
            log_attempt(root, record)
            base["attempts"].append(record)
            return dict(base, **validation, status=("downloaded" if validation["complete"]
                        else "downloaded_with_missing_dates"), checksum=digest, response=response)
        except (OSError, URLError, http.client.HTTPException, ValueError) as exc:
            record.update(event="failed", error=f"{type(exc).__name__}: {exc}", validation=validation)
            if partial.exists():
                rejected = root / "rejected" / partial.name
                rejected.parent.mkdir(exist_ok=True)
                partial.rename(rejected)
                record.update(file_path=str(rejected), checksum=checksum(rejected))
            log_attempt(root, record)
            base["attempts"].append(record)
            retryable = not isinstance(exc, (FileExistsError, PermissionError))
            if isinstance(exc, HTTPError):
                retryable = exc.code in (408, 429, 500, 502, 503, 504)
                exc.close()
            if attempt == args.attempts or not retryable:
                report = validation or dict(rows=None, expected_rows=len(expected_dates(year)),
                                             start=None, end=None, missing_dates=None, duplicate_dates=None)
                return dict(base, **report, status="failed", error=record["error"],
                            rejected_file=record.get("file_path"),
                            rejected_checksum=record.get("checksum"))
            delay = retry_delay(attempt, args.backoff, exc)
            print(f"{cell} {year}: attempt {attempt} failed; retry in {delay:.1f}s: {exc}", flush=True)
            time.sleep(delay)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--full", action="store_true", help="all three cells, 2003-2025 (69 files)")
    scope.add_argument("--years", nargs="+", type=int, help="specific years (default: 2005)")
    parser.add_argument("--cells", nargs="+", choices=list(CELLS), help="default: northern")
    parser.add_argument("--output", type=Path, default=Path("crw_data"))
    parser.add_argument("--attempts", type=int, default=4, help="total attempts per cell-year")
    parser.add_argument("--timeout", type=float, default=120, help="socket timeout seconds")
    parser.add_argument("--backoff", type=float, default=2, help="exponential backoff base seconds")
    parser.add_argument("--pause", type=float, default=1, help="seconds between cell-years")
    parser.add_argument("--allow-missing-dates", action="store_true",
                        help="retain otherwise valid files with gaps explicitly listed in manifest")
    args = parser.parse_args(argv)
    if args.full and args.cells:
        parser.error("--full cannot be combined with --cells")
    args.years = list(range(2003, 2026)) if args.full else sorted(set(args.years or [2005]))
    args.cells = list(CELLS) if args.full else list(dict.fromkeys(args.cells or ["northern"]))
    if any(y < 2003 or y > 2025 for y in args.years):
        parser.error("years must be within the requested archive: 2003-2025")
    if args.attempts < 1 or not all(math.isfinite(n) and n >= 0 for n in
                                   (args.timeout, args.backoff, args.pause)) or args.timeout == 0:
        parser.error("attempts and timeout must be positive; backoff and pause must be nonnegative")
    return args


def main(argv=None):
    command = list(sys.argv[1:] if argv is None else argv)
    if "--regional" in command:
        from crw_regional import main as regional_main
        command.remove("--regional")
        return regional_main(command)
    args = parse_args(argv)
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock = root / ".download.lock"
    try:
        with lock.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(dict(pid=os.getpid(), started_at=utc_now())))
    except FileExistsError:
        print(f"Output is locked: {lock}. Check for a running downloader before removing a stale lock.",
              file=sys.stderr)
        return 2
    try:
        manifest_path = root / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {
            "schema_version": 1, "dataset": "dhw_5km", "source": BASE,
            "metadata": METADATA, "variables": VARIABLES, "stride": 1, "files": []}
        if manifest.get("schema_version") != 1 or manifest.get("source") != BASE:
            raise ValueError("unrecognized existing manifest; use a separate output directory")
        entries = {(r["cell"], r["year"]): r for r in manifest["files"]}
        failures = 0
        for index, (cell, year) in enumerate((c, y) for c in args.cells for y in args.years):
            if index:
                time.sleep(args.pause)
            result = process(root, cell, year, args)
            entries[cell, year] = result
            manifest.update(updated_at=utc_now(), files=[entries[k] for k in sorted(entries)])
            atomic_json(manifest_path, manifest)
            log_attempt(root, dict(event="result", at=utc_now(), result=result))
            failures += result["status"] == "failed"
            print(f"{cell} {year}: {result['status']}; rows={result.get('rows')}", flush=True)
        print(f"Manifest: {manifest_path}", flush=True)
        return 1 if failures else 0
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Interrupted; completed entries are saved. Rerun the same command to resume.", file=sys.stderr)
        sys.exit(130)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        sys.exit(2)
