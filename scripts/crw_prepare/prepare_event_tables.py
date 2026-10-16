"""Prepare typed daily CRW working CSVs for the guided ArcGIS Q1 analysis.

Raw monthly files are read only. The existing downloader's checks validate the
calendar, grid, masks, ranges and checksums before any derived files are written.
Annual statistics are left to the user in ArcGIS Pro.
"""
import argparse
import calendar
import csv
import hashlib
import json
import math
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "crw_download"))
import crw_regional as regional


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def number(raw):
    if raw.strip().lower() in ("", "nan", "-327.68"):
        return None
    value = float(raw)
    if not math.isfinite(value):
        raise ValueError("Nonfinite measurement")
    return value


def prepare_row(row, thresholds):
    """Return typed attributes; invalid DHW is null, validity is an explicit 0."""
    timestamp, latitude, longitude, sst_text, dhw_text, mask_text = row
    observation_date = date.fromisoformat(timestamp[:10])
    if timestamp != observation_date.isoformat() + "T12:00:00Z":
        raise ValueError("Unexpected CRW daily reference timestamp")
    latitude, longitude = float(latitude), float(longitude)
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError("Invalid geographic coordinate")
    mask = None if mask_text.strip().lower() in ("", "nan", "-5", "251") else float(mask_text)
    if mask is not None and mask not in (0, 1, 2, 4):
        raise ValueError("Unknown DHW mask")
    mask = int(mask) if mask is not None else None
    sst, dhw = number(sst_text), number(dhw_text)
    valid = mask == 0 and dhw is not None
    flags = [int(dhw >= threshold) if valid else None for threshold in thresholds]
    return [observation_date.isoformat(), f"{latitude:.3f}_{longitude:.3f}",
            latitude, longitude, mask, sst, dhw if valid else None, int(valid), *flags]


def columns(year, thresholds):
    return [("Date_UTC", "DateTime"), ("CRW_Key", "Text Width 24"),
            ("CRW_Lat", "Double"), ("CRW_Lon", "Double"),
            ("DHW_Mask", "Long"), ("SST_C", "Double"),
            (f"DHW_{year}", "Double"), (f"Valid_{year}", "Long"),
            *[(f"GE{threshold}_{year}", "Long") for threshold in thresholds]]


def prepare(source_root, output_dir, years, thresholds):
    source_root, output_dir = Path(source_root).resolve(), Path(output_dir).resolve()
    if output_dir == source_root or output_dir.is_relative_to(source_root):
        raise ValueError("Working output must be outside the raw collection")
    if len(set(years)) != len(years) or len(set(thresholds)) != len(thresholds):
        raise ValueError("Years and thresholds must be distinct")
    if not thresholds or any(t < 0 for t in thresholds):
        raise ValueError("Specify nonnegative integer DHW thresholds")
    if output_dir.exists():
        raise FileExistsError(f"Choose a new output directory: {output_dir}")
    manifest_path = source_root / "manifest.json"
    manifest_hash = digest(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["scope"] != regional.scope():
        raise ValueError("Source manifest differs from the approved regional scope")
    if not set(years).issubset(manifest["scope"]["years"]):
        raise ValueError("Requested year is outside the acquired scope")
    sources = []
    for year in years:
        for month in range(1, 13):
            key = f"{year}_{month:02d}"
            asset = manifest["files"][key]
            relative = f"{year}/crw_west_hawaii_{key}.csv"
            if asset["state"] != "promoted" or asset["destination"] != relative:
                raise ValueError(f"Unapproved input: {key}")
            path = source_root / relative
            if digest(path) != asset["checksum"] or path.stat().st_size != asset["bytes"]:
                raise ValueError(f"Changed raw input: {key}")
            checked = regional.validate_csv(path, date(year, month, 1),
                                           date(year, month, calendar.monthrange(year, month)[1]))
            if not checked["valid"]:
                raise ValueError(f"Invalid raw input {key}: {checked['errors']}")
            sources.append({"path": str(path), "year": year, "month": month,
                            "sha256": asset["checksum"], "rows": checked["rows"]})
    output_dir.mkdir(parents=True, exist_ok=False)
    receipt = {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
               "source_manifest": str(manifest_path), "source_manifest_sha256": manifest_hash,
               "script_sha256": digest(__file__), "years": years,
               "thresholds_celsius_weeks": thresholds, "sources": sources,
               "raw_unchanged": False, "outputs": [],
               "method": "One record per native cell and UTC reference date. DHW eligible only for mask=0 and finite DHW. Inclusive thresholds. No interpolation or gap filling.",
               "zero_valid_days": "Annual peak and threshold counts are unassessed when valid-day count is zero, regardless of ArcGIS null-sum display."}
    schema = []
    for year in years:
        destination = output_dir / f"crw_daily_{year}.csv"
        field_definitions = columns(year, thresholds)
        counts, masks, valid_days = Counter(), Counter(), Counter()
        seen = set()
        with destination.open("x", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow([name for name, _ in field_definitions])
            for source in (s for s in sources if s["year"] == year):
                with Path(source["path"]).open(encoding="utf-8-sig", newline="") as raw:
                    reader = csv.reader(raw)
                    if next(reader) != regional.HEADER or next(reader) != regional.UNITS:
                        raise ValueError("Raw header changed after validation")
                    for row in reader:
                        prepared = prepare_row(row, thresholds)
                        pair = tuple(prepared[:2])
                        if pair in seen:
                            raise ValueError("Duplicate cell/date after preparation")
                        seen.add(pair)
                        counts[prepared[1]] += 1
                        masks[str(prepared[4])] += 1
                        valid_days[prepared[1]] += prepared[7]
                        writer.writerow(prepared)
        expected_keys = {f"{lat:.3f}_{lon:.3f}" for lat in regional.LATITUDES for lon in regional.LONGITUDES}
        expected_days = 366 if calendar.isleap(year) else 365
        if set(counts) != expected_keys or any(n != expected_days for n in counts.values()):
            raise ValueError("Incomplete prepared calendar or key collision")
        schema.extend([f"[{destination.name}]", "Format=CSVDelimited", "ColNameHeader=True",
                       "MaxScanRows=0", "CharacterSet=ANSI", "DateTimeFormat=yyyy-mm-dd",
                       "DecimalSymbol=."])
        schema.extend(f"Col{i}={name} {datatype}" for i, (name, datatype) in enumerate(field_definitions, 1))
        schema.append("")
        receipt["outputs"].append({"path": str(destination), "sha256": digest(destination),
                                   "year": year, "rows": len(seen), "unique_keys": len(counts),
                                   "days_per_cell": expected_days, "mask_counts": dict(masks),
                                   "valid_day_distribution": dict(Counter(valid_days.values())),
                                   "duplicate_cell_dates": 0})
    (output_dir / "schema.ini").write_text("\n".join(schema), encoding="ascii")
    receipt["schema_sha256"] = digest(output_dir / "schema.ini")
    if digest(manifest_path) != manifest_hash or any(digest(s["path"]) != s["sha256"] for s in sources):
        raise ValueError("Source identity changed during preparation")
    receipt["raw_unchanged"] = True
    (output_dir / "preparation.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--years", type=int, nargs="+", required=True)
    parser.add_argument("--thresholds", type=int, nargs="+", required=True)
    args = parser.parse_args()
    result = prepare(args.source_root, args.output_dir, args.years, args.thresholds)
    print(json.dumps({"outputs": result["outputs"], "raw_unchanged": result["raw_unchanged"]}, indent=2))


if __name__ == "__main__":
    main()
