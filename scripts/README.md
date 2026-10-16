# Acquisition and preparation helpers

`crw_download/crw_downloader.py` acquires/validates the selected-cell histories; `crw_download/crw_regional.py` acquires/validates monthly regional grids. Run either with `--help` for options. `crw_prepare/prepare_event_tables.py` creates typed working CSVs for the manual ArcGIS workflow.

The scripts use the Python standard library. The forecast archive needed by the notebook is already included, so downloading it again is unnecessary. Existing tests are retained with their helpers. Regional default output was changed to the repository's `Data/crw_regional` folder for portability; the original analysis parameters are preserved.

Q1/Q2 were completed through the guided ArcGIS workflow documented in `Documentation/WORKFLOW.md`; these helpers do not automate the entire GIS project. Q3 is reproducible through the notebook.
