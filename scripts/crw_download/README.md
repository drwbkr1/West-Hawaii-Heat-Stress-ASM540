# Coral Reef Watch download helpers

These standard-library Python scripts download and validate NOAA Coral Reef Watch v3.1 CSV subsets from [PacIOOS ERDDAP](https://pae-paha.pacioos.hawaii.edu/erddap/info/dhw_5km/index.html).

The notebook's three-cell archive is already included. A new download is optional and may differ if the upstream archive has changed. Preserve the supplied snapshot when reproducing the course results.

## Three-cell archive

From the repository root:

```sh
python scripts/crw_download/crw_downloader.py --help
python scripts/crw_download/crw_downloader.py --full --output Data/dhw_5km --timeout 300
```

The full scope is three selected cells and 2003–2025 (69 annual files). Existing files are validated against the manifest and skipped when valid. The supplied 2024 records have five documented gaps per cell. The strict downloader reports incomplete years; `--allow-missing-dates` permits the documented gap exception rather than filling observations. See `Data/README.md` and the script's help.

## Regional event years

```sh
python scripts/crw_download/crw_regional.py --help
python scripts/crw_download/crw_regional.py --verify-only --output Data/crw_regional
```

Extract the release bundle first for offline regional validation. The regional request contains 330 grid positions (30 by 11), at 0.05-degree spacing, for all of 2015 and 2019. Latitude cell centers span 18.875–20.325; longitude centers span -156.125 to -155.625. Variables are `CRW_SST`, `CRW_DHW`, and `CRW_DHW_mask`; reference timestamps are noon UTC.

Without `--verify-only`, the regional script acquires missing data. `--sample` requests a one-week pilot in a separate test folder. Download locks, retries, partial-file retention, units/header checks, calendar/grid checks, and SHA-256 manifest checks are retained from the original helpers. Inspect a lock owner before attempting recovery; do not run parallel downloaders against the same output folder.

Mask meanings are 0 valid water, 1 land, 2 missing, and 4 ice. Valid zero DHW is distinct from missing or masked data. Recorded hashes establish local byte identity; the provider does not publish a checksum for each dynamically generated subset.

The optional `run_crw.ps1` wrapper accepts `-Regional`, `-VerifyOnly`, `-Sample`, `-Full`, `-DataDirectory`, and `-PythonExecutable`. Its default folders now resolve within this repository.
