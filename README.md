# West Hawaiʻi Heat Stress ASM540

An ASM540 GIS term project by Drew Baker exploring reef heat exposure, satellite–underwater temperature differences, and seven-day sea-surface temperature (SST) forecasts along West Hawaiʻi.

## Project questions

1. Where did heat-stress intensity and duration differ in 2015 and 2019, and how much mapped reef/hardbottom habitat was exposed?
2. How did satellite temperatures compare with nighttime underwater logger measurements by site and depth?
3. Could a random forest forecast SST seven days ahead more accurately than persistence and a seasonal baseline?

## Start here

- [GIS analysis workflow](Documentation/WORKFLOW.md): the concise, step-by-step course workflow and reference results.
- [Original process log](Documentation/PROCESS_LOG.md) and [Word document](Documentation/Process_Log_ASM_540_Term_Project.docx): the earlier working record. The workflow above is the more complete reconstruction.
- [Python forecasting notebook](Analysis/Q3/Q3_SST_Forecasting.ipynb): code, tables, plots, and saved outputs.
- [Maps, charts, and animations](Documentation/Figures) and [forecast summary CSVs](Analysis/Q3/Outputs).
- [Complete ArcGIS project, geodatabase, and data download](https://github.com/drwbkr1/West-Hawaii-Heat-Stress-ASM540/releases/tag/v2026.10.16): release assets keep the large binary datasets outside Git history.

## Run the notebook

The three-cell CSV archive and animation frames are included in this repository. Use **Python 3.12 or later**, create an environment, and install `requirements.txt`:

```sh
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```

Open `Analysis/Q3/Q3_SST_Forecasting.ipynb` in VS Code/Jupyter, select that environment, and run all cells. On macOS/Linux, use `.venv/bin/python` for the installation command. No ArcGIS installation is required for the forecasting notebook. The GIS maps and analysis require ArcGIS Pro; see [opening the GIS project](Geodatabase/README.md).

## Data and interpretation

Inputs are NOAA Coral Reef Watch via PacIOOS, NOAA NCEI underwater loggers, and NOAA NCCOS historical benthic habitat. See [sources and coverage](Data/README.md) for download links, dates, and known gaps.

The analysis compares **thermal exposure**, rather than measured coral mortality. The forecast target is satellite SST at three selected cells; it is not a regional bleaching forecast. Depth comparisons are associations from a small monitoring network. The saved results found greater accumulated heat stress in 2015 than 2019, and the random forest did not beat persistence overall.

This is a course-project snapshot dated October 16, 2026. The StoryMap is being prepared separately.
