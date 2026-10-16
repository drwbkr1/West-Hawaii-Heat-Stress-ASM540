"""West Hawaii regional extension to the existing CRW CSV downloader (stdlib)."""
import argparse
import calendar
import csv
import http.client
import json
import math
import os
import shutil
import sys
import time
import uuid
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote

import crw_downloader as core

LATITUDES = tuple(Decimal('20.325') - Decimal('0.05') * i for i in range(30))
LONGITUDES = tuple(Decimal('-156.125') + Decimal('0.05') * i for i in range(11))
VARIABLES = ['CRW_SST', 'CRW_DHW', 'CRW_DHW_mask']
HEADER = ['time', 'latitude', 'longitude', *VARIABLES]
UNITS = ['UTC', 'degrees_north', 'degrees_east', 'Celsius', 'Celsius weeks', '1']
DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / 'Data' / 'crw_regional'


def scope():
    return dict(dataset='dhw_5km', product_version='3.1', variables=VARIABLES,
                latitudes=[str(v) for v in LATITUDES],
                longitudes=[str(v) for v in LONGITUDES], stride=1,
                years=[2015, 2019], time_reference='12:00:00Z',
                format='ERDDAP CSV including names and units rows')


def dates(start, end):
    return [(start + timedelta(days=i)).isoformat() for i in range((end-start).days+1)]


def build_url(start, end):
    selection = (f'[({start}T12:00:00Z):1:({end}T12:00:00Z)]'
                 f'[({LATITUDES[0]}):1:({LATITUDES[-1]})]'
                 f'[({LONGITUDES[0]}):1:({LONGITUDES[-1]})]')
    return core.BASE + '?' + quote(','.join(v + selection for v in VARIABLES), safe='(),:-')


def validate_csv(path, start, end):
    """Require every requested cell-day exactly once; retain masks and missing values."""
    expected_days = dates(start, end)
    expected_keys = {(day, lat, lon) for day in expected_days
                     for lat in LATITUDES for lon in LONGITUDES}
    seen, errors = set(), []
    masks, missing, valid_days = Counter(), Counter(), Counter()
    rows = duplicates = 0
    day_counts = Counter()

    def error(message):
        if len(errors) < 30:
            errors.append(message)

    def number(raw, lo, hi):
        if raw.strip().lower() in ('', 'nan') or raw == '-327.68':
            return None
        value = float(raw)
        if not math.isfinite(value) or not lo <= value <= hi:
            raise ValueError(f'out-of-range numeric value {raw}')
        return value

    try:
        if path.stat().st_size > core.MAX_BYTES:
            raise ValueError('payload exceeds monthly regional limit')
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.reader(stream, strict=True)
            if next(reader, None) != HEADER or next(reader, None) != UNITS:
                raise ValueError('incorrect variable names/order or ERDDAP units row')
            for line, row in enumerate(reader, 3):
                rows += 1
                try:
                    if len(row) != len(HEADER):
                        raise ValueError('incorrect column count')
                    day = date.fromisoformat(row[0][:10]).isoformat()
                    if row[0] != day + 'T12:00:00Z':
                        raise ValueError('incorrect daily reference timestamp')
                    lat, lon = Decimal(row[1]), Decimal(row[2])
                    key = (day, lat, lon)
                    if key not in expected_keys:
                        raise ValueError('unexpected date or grid coordinate')
                    if key in seen:
                        duplicates += 1
                        raise ValueError('duplicate cell-day')
                    seen.add(key)
                    day_counts[day] += 1
                    sst = number(row[3], -2, 50)
                    dhw = number(row[4], 0, 100)
                    raw_mask = row[5].strip().lower()
                    if raw_mask in ('', 'nan', '-5', '251'):
                        mask = 'fill'
                    else:
                        m = float(raw_mask)
                        if m not in (0, 1, 2, 4):
                            raise ValueError('unrecognized DHW mask')
                        mask = str(int(m))
                    masks[mask] += 1
                    missing['CRW_SST'] += sst is None
                    missing['CRW_DHW'] += dhw is None
                    missing['CRW_DHW_mask'] += mask == 'fill'
                    cell = f'{lat},{lon}'
                    if mask == '0' and dhw is not None:
                        valid_days[cell] += 1
                except (ValueError, InvalidOperation) as exc:
                    error(f'line {line}: {exc}')
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        error(str(exc))
    missing_keys = expected_keys - seen
    if missing_keys:
        error(f'{len(missing_keys)} missing cell-days')
    if rows != len(expected_keys):
        error(f'expected {len(expected_keys)} rows, got {rows}')
    return dict(valid=not errors, complete=not errors, rows=rows,
                expected_rows=len(expected_keys), cells=len(LATITUDES)*len(LONGITUDES),
                dates=len(expected_days), start=str(start), end=str(end), errors=errors,
                duplicate_cell_days=duplicates, missing_cell_days=len(missing_keys),
                missing_dates=[d for d in expected_days if not day_counts[d]],
                mask_counts=dict(masks), missing_values=dict(missing),
                valid_dhw_days_by_cell=dict(valid_days),
                validity_note='Complete cell-day records include land/missing pixels; these are not valid water observations.')


def safe_path(root, relative):
    value = Path(relative)
    if value.is_absolute() or '..' in value.parts:
        raise ValueError('unsafe relative destination')
    candidate = root / value
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise ValueError('destination escapes output root')
    if any(p.is_symlink() for p in (candidate, *candidate.parents)):
        raise ValueError('symlink destination is unsupported')
    return candidate


def transfer(root, key, start, end, args, prior=None):
    relative = f'{start.year}/crw_west_hawaii_{key}.csv'
    path = safe_path(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    url = build_url(start, end)
    if path.exists():
        if not prior or prior.get('state') != 'promoted':
            raise ValueError(f'untracked destination collision: {path}')
        checked = validate_csv(path, start, end)
        if core.checksum(path) != prior['checksum'] or not checked['valid']:
            raise ValueError(f'previously promoted file changed: {path}')
        return dict(prior, validation=checked, verified_at=core.utc_now())
    if prior and prior.get('state') == 'promoted':
        raise ValueError(f'previously promoted file is absent: {path}')
    base = dict(key=key, source_url=url, destination=relative, start=str(start), end=str(end),
                expected_sha256=None, expected_bytes=None,
                identity_note='Dynamic ERDDAP subset has no published upstream checksum or byte size.')
    for attempt in range(1, args.attempts + 1):
        asset_id = uuid.uuid4().hex
        partial = path.with_name(path.name + '.' + asset_id + '.part')
        record = dict(base, asset_id=asset_id, attempt=attempt,
                      staging_path=partial.relative_to(root).as_posix(), at=core.utc_now())
        for state in ('planned', 'authorized', 'staging'):
            core.log_attempt(root, dict(record, state=state))
        try:
            response = core.fetch(url, partial, args.timeout)
            digest, size = core.checksum(partial), partial.stat().st_size
            record.update(response=response, checksum=digest, bytes=size)
            core.log_attempt(root, dict(record, state='staged'))
            checked = validate_csv(partial, start, end)
            record['validation'] = checked
            if not checked['valid']:
                raise ValueError('; '.join(checked['errors'][:3]))
            core.log_attempt(root, dict(record, state='verified'))
            os.link(partial, path)  # Atomic no-replace; partial remains if publication fails.
            if core.checksum(path) != digest or path.stat().st_size != size:
                raise ValueError('post-promotion identity mismatch')
            partial.unlink()
            record.update(state='promoted', promoted_at=core.utc_now())
            core.log_attempt(root, record)
            return record
        except (OSError, URLError, http.client.HTTPException, ValueError) as exc:
            record.update(state='failed', error=f'{type(exc).__name__}: {exc}')
            if partial.exists():
                record.update(rejected_checksum=core.checksum(partial), rejected_bytes=partial.stat().st_size)
            core.log_attempt(root, record)
            retryable = not isinstance(exc, (FileExistsError, PermissionError)) and not path.exists()
            if isinstance(exc, HTTPError):
                retryable = exc.code in (408, 429, 500, 502, 503, 504)
            delay = core.retry_delay(attempt, args.backoff, exc)
            if isinstance(exc, HTTPError):
                exc.close()
            if not retryable or attempt == args.attempts:
                return record
            print(f'{key}: attempt {attempt} failed; retry in {delay:.1f}s: {exc}', flush=True)
            time.sleep(delay)


def jobs(args):
    if args.sample:
        return [('sample_2015_09_01_07', date(2015,9,1), date(2015,9,7))]
    return [(f'{y}_{m:02d}', date(y,m,1), date(y,m,calendar.monthrange(y,m)[1]))
            for y in (2015,2019) for m in range(1,13)]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--sample', action='store_true', help='one week over all 330 cells')
    parser.add_argument('--verify-only', action='store_true', help='validate all expected files without network')
    parser.add_argument('--timeout', type=float, default=300)
    parser.add_argument('--attempts', type=int, default=4)
    parser.add_argument('--backoff', type=float, default=2)
    parser.add_argument('--pause', type=float, default=2)
    args = parser.parse_args(argv)
    if args.attempts < 1 or not all(math.isfinite(v) and v >= 0 for v in (args.timeout,args.backoff,args.pause)) or args.timeout == 0:
        parser.error('invalid retry, timeout, backoff or pause')
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(root).free < 100 * 1024**2:
        raise ValueError('less than 100 MiB free')
    lock = root / '.download.lock'
    with lock.open('x', encoding='utf-8') as stream:
        json.dump(dict(pid=os.getpid(), started_at=core.utc_now(), mode='regional'), stream)
    try:
        manifest_path = root / 'manifest.json'
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            if manifest.get('schema_version') != 2 or manifest.get('scope') != scope():
                raise ValueError('incompatible manifest; existing archive is protected')
        else:
            if args.verify_only:
                raise ValueError('no regional manifest to verify')
            manifest = dict(schema_version=2, scope=scope(), source=core.BASE,
                            terms_ref=core.METADATA, authorization='Public NOAA CRW data; user requested regional collection.',
                            source_identity='Generated subsets: upstream hashes unavailable; local SHA-256 after transfer.',
                            collision_policy='fail', promotion_mode='atomic-no-replace', files={})
            core.atomic_json(manifest_path, manifest)
        requested = jobs(args)
        failures = 0
        for index,(key,start,end) in enumerate(requested,1):
            prior = manifest['files'].get(key)
            if args.verify_only:
                if not prior or prior.get('state') != 'promoted':
                    failures += 1
                    print(f'{key}: not promoted', flush=True)
                    continue
            if index > 1 and not args.verify_only:
                time.sleep(args.pause)
            print(f'[{index}/{len(requested)}] {key}: checking/downloading', flush=True)
            result = transfer(root,key,start,end,args,prior)
            manifest['files'][key] = result
            failures += result['state'] != 'promoted'
            manifest.update(updated_at=core.utc_now(), last_run_failures=failures)
            core.atomic_json(manifest_path,manifest)
            print(f'{key}: {result["state"]}; rows={result.get("validation",{}).get("rows")}', flush=True)
        summary = dict(checked_at=core.utc_now(), requested_files=len(requested), failures=failures,
                       complete=failures == 0, verify_only=args.verify_only,
                       rows=sum(manifest['files'].get(k,{}).get('validation',{}).get('rows',0) for k,_,_ in requested))
        core.atomic_json(root / ('sample_validation.json' if args.sample else 'validation.json'),summary)
        print(json.dumps(summary), flush=True)
        return 1 if failures else 0
    finally:
        lock.unlink(missing_ok=True)


if __name__ == '__main__':
    sys.exit(main())
