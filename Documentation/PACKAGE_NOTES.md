# Package notes — October 16, 2026

## Included

The Git repository contains the forecasting notebook, its 69 annual source CSVs, environment requirements, acquisition/preparation helpers, original process log, simplified GIS workflow, map/plot exports, GIFs and frames, and Q1/Q2/Q3 summary CSVs. The saved APRX and toolbox are included in the repository; their large data dependencies are in the release ZIP.

The release ZIP contains the saved ArcGIS Pro project and toolbox, the complete file geodatabase (74 feature-class/table datasets), regional satellite data, underwater logger source files and deployment metadata, historical habitat shapefiles with their companion files/metadata, working CSV imports, the notebook, and course documentation/figures. Other-island habitat files are retained as components of the original source collection; the analysis uses Hawaiʻi Island.

The ZIP has **612 files**, occupies **311,830,319 bytes** (about 297.4 MiB), and expands to approximately 2.7 GB. `ARCHIVE_FILE_MANIFEST.csv` describes the release archive payload, rather than the evolving Git checkout. The ZIP also contains its own root-level `FILE_MANIFEST.csv`. Use `SHA256SUMS.txt` beside the release asset to verify the ZIP.

## Completed checks

- Copied into isolated staging; checksums confirmed 605 original source files were unchanged.
- ZIP CRC test passed; all 611 payload files listed by the manifest matched their size and SHA-256 after extraction.
- Reopened the extraction in a fresh ArcGIS Pro Python process: **9 maps, 5 layouts, 74 datasets**, no broken data sources, and no local data connections or project defaults pointing back to the source/staging directories.
- Exported and visually inspected the extracted project's Q1 peak-DHW comparison and Q3 northern annual layout. Online basemaps rendered in these checks.
- Executed all **40 code cells** in the repository notebook with Python 3.12.10 and the course environment. No execution errors; the final cells verified both 11-frame GIFs. Visually inspected the two notebook forecast plots.
- Regenerated forecast CSVs matched the saved course exports to floating-point precision (largest absolute numeric difference 1.78e-13).
- The retained acquisition/preparation helper suites passed **33 tests**.
- Checked the explicit public handoff files for common credential/private-key patterns and oversized Git files; no matches requiring removal were found. This is a bounded check, not a comprehensive security audit.

## Portability changes

Only the staged/publication copies were changed: ArcGIS data connections now resolve within the extracted project, the notebook finds the repository root instead of a machine-specific path, and helper defaults use repository folders. Scientific parameters and analysis logic were preserved. Original coursework files were not rewritten.

Raw forecast CSV byte contents are preserved in Git. The notebook writes outputs into the repository copy of `Analysis/Q3/Outputs` and `Documentation/Figures`. Its final GIF cells assemble the supplied ArcGIS-exported frames; they do not recreate the GIS layouts. Q1/Q2 are documented manual ArcGIS workflows, not a fully automated pipeline.

## Dependencies and scope

ArcGIS Pro 3.7.1 was used for the package checks. ArcGIS licensing and internet access to Esri basemap services are required for the full GIS experience. No basemap cache, ArcGIS licence, or login credential is distributed. Fresh-machine/cross-version behavior and a fresh dependency installation were not tested.

Virtual environments, locks, caches, backups, failed/pilot downloads, unused bleaching context, instructor-owned course materials, and unrelated project files are excluded. The earlier process log is retained as an earlier working record; `WORKFLOW.md` and its simplified Word counterpart cover the completed course analysis more fully. The StoryMap is maintained separately and is not claimed as published by this snapshot.
