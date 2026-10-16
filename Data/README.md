# Data sources and coverage

| Source | Coverage used | Download location | Included files |
| --- | --- | --- | --- |
| NOAA Coral Reef Watch v3.1 via PacIOOS ERDDAP | Regional daily grid: calendar years 2015 and 2019; selected cells: 2003–2025 | [Dataset information](https://pae-paha.pacioos.hawaii.edu/erddap/info/dhw_5km/index.html) and [data form](https://pae-paha.pacioos.hawaii.edu/erddap/griddap/dhw_5km.html) | Three-cell histories in `dhw_5km/`; regional CSVs in the release bundle |
| NOAA NCEI subsurface temperature recorders | West Hawaiʻi observations and deployments used for 2015/2019 comparisons | [ERDDAP download form](https://www.ncei.noaa.gov/erddap/tabledap/CRCP_Subsurface_Temp_Hawaii.html) | Source observations, deployment metadata, and source documentation in the release bundle |
| NOAA NCCOS historical benthic habitat, 2007 release | Hawaiʻi Island habitat, clipped during analysis | [Benthic habitat shapefiles and metadata](https://products.coastalscience.noaa.gov/collections/benthic/e97hawaii/data2007.aspx) | Original shapefile components/metadata and derived habitat layers in the release bundle |

## Selected forecast cells

| Cell | Latitude | Longitude |
| --- | ---: | ---: |
| northern | 20.275 | -155.875 |
| southern_nearshore | 19.225 | -155.875 |
| southern_offshore | 19.225 | -155.925 |

There are 69 annual CSVs: 23 years at each cell. Raw ERDDAP CSVs have a second row containing units; the notebook removes that row. Preserve valid zero DHW values and treat masks/missingness separately.

The archived PacIOOS series has five missing dates in 2024 at each cell: January 30, July 4–6, and July 25. This is a gap in the acquired series, not a claim that NOAA's original source files lack those dates. The notebook leaves gaps unfilled and excludes forecast windows crossing them.

Regional download cell-center bounds are latitude 18.875–20.325 and longitude -156.125 to -155.625, at 0.05-degree spacing (330 cells). The study boundary is smaller; numerical comparisons use the common valid AOI cells described in the workflow.

## Attribution and use

Retain NOAA/PacIOOS/NCEI/NCCOS attribution, accession URLs in logger records, and the source metadata when reusing these data. Provider terms and recommended dataset citations remain applicable. Esri basemap services are referenced by the project and are not redistributed as offline imagery.

The [final course package](https://github.com/drwbkr1/West-Hawaii-Heat-Stress-ASM540/releases/tag/v2026.10.16-final) contains finished GIS data only. The [earlier reproduction archive](https://github.com/drwbkr1/West-Hawaii-Heat-Stress-ASM540/releases/tag/v2026.10.16) preserves the source and working data, including the original multi-island habitat collection. The analysis uses Hawaiʻi Island. Use the course package for submission and the separate archive when rebuilding the manual GIS analysis.
