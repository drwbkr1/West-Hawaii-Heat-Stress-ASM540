# ArcGIS course deliverables

Download and extract **GISProjectDrewBaker.zip** from the [final release](https://github.com/drwbkr1/West-Hawaii-Heat-Stress-ASM540/releases/tag/v2026.10.16-final). Open `WestHawaii_HeatStress.aprx` inside the extracted folder.

```text
GISProjectDrewBaker/
  WestHawaii_HeatStress.aprx
  WestHawaii_HeatStress.atbx
  Data/WestHawaii_HeatStress.gdb/
  Documentation/GISProcessLogDrewBaker.docx
  Documentation/GISPresentationDrewBaker.pptx
  Other/Figures/
  Other/Results/
```

The file geodatabase contains **16 finished feature classes and tables**. Raw logger observations, import tables, temporary joins, unused habitat source islands, and other intermediate data are excluded. [Dataset names and counts](Documentation/GEODATABASE_CONTENTS.csv) are listed beside the process log.

The nine maps cover Q1 peak DHW, threshold-day change and annual mean SST, Q2 logger locations, and Q3 overall, high-stress and annual forecast performance. Five saved layouts retain the course map designs. In the mean-SST map, toggle the 2015 and 2019 layers for comparison. The annual forecast maps open at 2015; change `Target_Year` in both annual layers’ definition queries to view another year from 2015 through 2025. All 33 cell-year records remain in the geodatabase.

The reef/hardbottom layer is retained as a finished habitat result and starts hidden in the 2015 peak-DHW map. Q2 starts with four representative 2019 logger sites, while its source layer retains all 12 seasonal summary records.

ArcGIS Pro licensing and internet access to the referenced Esri basemaps are required. Analysis uses WGS84 and NAD83 UTM Zone 5N as documented in the process log. The package is checked with ArcGIS Pro 3.7.1 on the packaging machine; another machine or ArcGIS version has not been tested.

The separate [Python notebook](https://github.com/drwbkr1/West-Hawaii-Heat-Stress-ASM540/blob/main/Analysis/Q3/Q3_SST_Forecasting.ipynb), source CSVs, and [process log](https://github.com/drwbkr1/West-Hawaii-Heat-Stress-ASM540/blob/main/Documentation/PROCESS_LOG.md) are available in the repository. Use the release ZIP for the complete GIS folder.
