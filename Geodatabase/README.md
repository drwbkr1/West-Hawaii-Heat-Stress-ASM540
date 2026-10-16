# Open the ArcGIS project

1. Download `WestHawaii_HeatStress_ArcGIS_Data.zip` from the [snapshot release](https://github.com/drwbkr1/West-Hawaii-Heat-Stress-ASM540/releases/tag/v2026.10.16).
2. Extract its contents into this repository's root folder. Keep the `Data`, `WorkingData`, `Documentation`, and `Geodatabase` folder structure intact.
3. Open `Geodatabase/WestHawaii_HeatStress/WestHawaii_HeatStress.aprx` in ArcGIS Pro. The zipped file geodatabase is included alongside it; GitHub's automatic source-code ZIP alone does not contain the large GIS datasets.

The project preserves the saved maps, layouts, tables, joins, symbology, and bookmarks. Local data connections are adjusted in the staged copy. The original coursework files are unchanged. Analysis uses WGS84 and NAD83 UTM Zone 5N as documented in the workflow; the web display map may use Web Mercator.

Basemaps require internet access. ArcGIS Pro licensing is required. This handoff is checked on the packaging machine; cross-version/clean-machine behavior is not established by that check. See `Documentation/PACKAGE_NOTES.md` for the exact validation performed.
