# West Hawaiʻi heat stress process log

ASM54000 course project   Drew Baker

StoryMap: [Following the heat around West Hawaiʻi](https://storymaps.arcgis.com/stories/7e6551719d15418a997e2517c2bc24cc).

## Recorded dates

The dates below come from download manifests and saved geoprocessing history. They identify recorded milestones rather than every work session. Original habitat and logger download dates were not recorded.

- 2026-09-13: Verify the selected-cell satellite archive (download manifest).
- 2026-09-26: Acquire regional satellite data, clip habitat, and create the study boundary and grid (manifest and geoprocessing history).
- 2026-10-04: Join annual DHW summaries and classify heat exposure (geoprocessing history).
- 2026-10-09 to 2026-10-10: Add annual SST summaries, prepare logger observations, and calculate seasonal comparisons (geoprocessing history and working record).
- 2026-10-13: Import forecast summaries and create the annual forecast polygons (geoprocessing history).
- 2026-10-16: Consolidate this process log and package the final GIS results.

## 1 Sources and project setup

I address three questions: Q1 regional heat exposure and reef habitat in 2015 and 2019; Q2 satellite–underwater temperature differences by site and depth; and Q3 seven-day SST forecasts compared with persistence and seasonal baselines.

Download the data used in the analysis

| Source link | Period used | What to download |
| --- | --- | --- |
| [NOAA Coral Reef Watch via PacIOOS](https://pae-paha.pacioos.hawaii.edu/erddap/griddap/dhw_5km.html) | 2015 and 2019 regional;2003–2025 selected cells | Open the ERDDAP data form. Select CRW_SST, CRW_DHW, and CRW_DHW_mask. Export daily CSVs for the regional grid and the three forecast cells. |
| [NOAA NCEI underwater loggers](https://www.ncei.noaa.gov/erddap/tabledap/CRCP_Subsurface_Temp_Hawaii.html) | 2015 and 2019 | Filter the data form to the study area and each year. Export time, coordinates, site, depth, deployment ID, TEMP_C, and accession_url. Export distinct deployment metadata separately. |
| [NOAA NCCOS benthic habitat](https://products.coastalscience.noaa.gov/collections/benthic/e97hawaii/data2007.aspx) | 2007 release | Choose Benthic Habitat Shapefiles Data, unzip the download, and use hawaii.shp with its companion files and metadata. |

For the regional download, use cell-center bounds 18.875–20.325° latitude and −156.125 to −155.625° longitude, at 0.05° spacing. Download the full calendar years. The selected forecast cells are listed in Section 4.

Create the GIS workspace

1.1 Create an ArcGIS Pro project and geodatabase in a chosen location. Keep source downloads separate from derived outputs. Use Q3_SST_Forecasting.ipynb for the Python analysis. Save later outputs to a chosen location.

1.2 Use Create Fishnet, polygon geometry, no label points, and WGS84 (EPSG 4326) for the study boundary and satellite grid.

| Parameter | Study boundary | Satellite grid |
| --- | --- | --- |
| Origin longitude, latitude | −156.100, 18.900 | −156.150, 18.850 |
| Y-axis coordinate | −156.100, 19.900 | −156.150, 19.850 |
| Cell width × height (degrees) | 0.45 × 1.40 | 0.05 × 0.05 |
| Rows × columns | 1 × 1 | 30 × 11 |

1.3 Add a stable Cell_ID and cell-center coordinates to the grid. Create CRW_Key from latitude_longitude, each rounded to three decimals. Project the boundary and grid to NAD83 UTM Zone 5N (EPSG 26905) using NAD_1983_To_WGS_1984_3, Preserve Shape, and a 1-meter maximum offset.

## 2 Prepare habitat and calculate Q1 heat exposure

Prepare the habitat layers

2.1 Copy hawaii.shp into the geodatabase and Clip it to the study boundary. Calculate geodesic Area_ha in hectares from the clipped geometry. Summarize by M_STRUCT, then save the Coral Reef and Hardbottom subset. Run Check Geometry on the boundary and clipped habitat.

2.2 Intersect the projected grid and clipped habitat. Calculate geodesic Piece_ha for the intersection pieces. Sum Piece_ha by Cell_ID and habitat class; reconcile the totals with the clipped habitat. Join reef area to the grid by Cell_ID.

| GIS check | Reference result |
| --- | --- |
| Clipped habitat / reef and hardbottom subset | 938 / 437 polygons |
| Grid / habitat intersection | 330 cells / 1,381 pieces |
| Cells containing mapped reef and hardbottom | 51 |
| Geometry problem records | 0 |

Summarize satellite records and exposed habitat

2.3 Combine the regional monthly CSVs, excluding pilot files and units rows. Create CRW_Key, Event_Year, numeric SST_C, and numeric DHW_CW. Keep masked or unavailable DHW null; retain valid zero values.

2.4 Calculate valid-day and DHW ≥4 / ≥8 indicators. Run Summary Statistics by CRW_Key and Event_Year: maximum DHW, valid-day count, threshold-day totals, and mean/minimum/maximum/count of SST. Keep SST statistics null where no SST observations are valid. Join each year’s summaries to a grid copy.

2.5 Classify annual maximum DHW as No valid DHW, Below 4, 4 to below 8, or 8 or above. Join the classes to reef intersection pieces and sum Piece_ha by year and class. Calculate percentages using both all mapped reef area and assessed reef area. Include the ≥8 class within the ≥4 total.

2.6 Select common cells with centers inside the study boundary and complete annual DHW coverage. Match by Cell_ID and calculate 2019 minus 2015 days at DHW ≥8. Use these paired cells for numerical comparisons.

| Data and area check | Reference result |
| --- | --- |
| Regional daily records / annual cell-year records | 240,900 / 660 |
| Annual grid records / paired water cells per year | 330 / 135 |
| Mapped / assessed reef and hardbottom (ha) | 5,702.29 / 4,731.23 |
| Mapped reef without valid satellite DHW (ha) | 971.05 |

| Q1 measure | 2015 | 2019 |
| --- | --- | --- |
| Reef area reaching DHW ≥4 (ha) | 4,731.23 | 4,259.42 |
| Reef area reaching DHW ≥8 (ha) | 4,731.23 | 3,612.16 |
| Median annual peak DHW (°C-weeks) | 11.64 | 10.39 |
| Median days at DHW ≥8 | 67 | 49 |
| Median annual mean SST (°C) | 26.53 | 26.68 |

Area totals use assessed reef habitat; medians use the paired water cells.

## 3 Q2 Compare satellite and underwater temperatures

Clean and locate the logger observations

3.1 Import working copies of the logger CSVs with Copy Rows, then remove units rows. Run Delete Identical on imported observation fields except ObjectID. Check duplicate time, site, and deployment keys with Find Identical, returning duplicate records only.

3.2 Create Date fields for timestamps and Double fields for temperature and depth. Convert UTC to HST by subtracting 10 hours; calculate local date, hour, and event year. Merge the cleaned yearly observations as Logger_Observations_Clean.

3.3 Summarize deployment coverage, coordinates, and depth. Use XY Table To Point with longitude as X, latitude as Y, and WGS84. Spatial Join the points to the satellite grid; join each deployment’s cell key back to its observations.

Match complete nights and compare seasonal windows

3.4 Select 00:00 to before 06:00 HST. Summarize temperature by site, deployment, local date, year, and satellite cell. Keep complete nights: 72 readings at five-minute intervals or 360 at one-minute intervals. Match nightly means to satellite SST and DHW by cell and date.

3.5 Calculate difference = satellite SST − nightly underwater mean and its square. Select common seasonal windows below. Summarize matched counts and mean difference by year, site, deployment, depth, and window. Calculate RMSD = √(mean squared difference). Combine the seasonal results into one table.

| Window | OCC-HAW sites | Nights per site and year | Matched rows |
| --- | --- | --- | --- |
| January–June | 002, 009, 011 | 181 | 1,086 |
| August–November | 001, 002, 009 | 122 | 732 |

| Logger check | Reference result |
| --- | --- |
| Cleaned 2015 / 2019 observations | 420,480 / 662,927 |
| Merged observations / deployment groups | 1,083,407 / 13 |
| Nighttime readings / complete deployment-nights | 271,080 / 3,089 |
| Repeated observation keys / seasonal summary rows | 0 / 12 |

| August–November RMSD (°C) | 2015 | 2019 |
| --- | --- | --- |
| OCC-HAW-001 | 0.741 | 0.334 |
| OCC-HAW-002 | 0.566 | 0.290 |
| OCC-HAW-009 | 0.317 | 0.210 |

Positive mean differences indicate warmer satellite values. Compare sites and depths within the same window; the comparison does not isolate a causal depth effect.

## 4 Q3 Evaluate seven day SST forecasts

4.1 In Q3_SST_Forecasting.ipynb, load the three-cell archive, remove units rows, standardize dates and values, and complete each cell’s daily calendar. Leave missing observations unfilled.

| Forecast cell | Latitude | Longitude |
| --- | ---: | ---: |
| northern | 20.275 | −155.875 |
| southern_nearshore | 19.225 | −155.875 |
| southern_offshore | 19.225 | −155.925 |

4.2 Set the target to SST seven days later. Use current SST, 1/7/14/28-day lags, 7/28-day averages, seven-day change, seasonal sine/cosine, and cell indicators. Retain complete 29-day histories and issue-date-through-target windows. Use future DHW only to group evaluation results.

4.3 Apply chronological splits below. Keep training targets earlier than validation issue dates, and development targets earlier than test issue dates. Tune on validation data, then refit using eligible pre-test data.

| Data stage | Period or scope | Reference rows |
| --- | --- | --- |
| Source / complete calendar | Three cells, 2003–2025 | 25,188 / 25,203 |
| Eligible forecast examples | Before split exclusions | 24,819 |
| Initial training / validation | 2003–2013 / 2014 | 11,949 / 1,074 |
| Development refit / test | Before 2015 / 2015–2025 | 13,044 / 11,754 |

4.4 Use current SST for persistence. Fit the seasonal baseline from earlier training/development records within ±15 days of the target season day. Compare random forests with depth 8/16 and minimum leaf size 5/20, 300 trees, and seed 540. Select by validation MAE, then RMSE; refit depth 16 and leaf size 20 for testing.

4.5 Compare all models on identical test dates using MAE and RMSE. Summarize by cell, target year, and target-date DHW class. Calculate RF skill (%) = 100 × (1 − RF MAE / persistence MAE); positive values favor RF.

| Model | MAE (°C) | RMSE (°C) |
| --- | --- | --- |
| Persistence | 0.2228 | 0.2817 |
| Random forest | 0.2350 | 0.3135 |
| Seasonal baseline | 0.5656 | 0.7070 |

Bring the summaries into ArcGIS

4.6 Export cell, high-DHW, and annual summaries as CSVs to a chosen location. Use XY Table To Point in WGS84 and match results to the native satellite cell polygons. Project the polygons to UTM Zone 5N.

4.7 Import the annual table into the geodatabase. Add Join to the three cell polygons using a one-to-many match on Cell_Name, then Export Features to a chosen location.

| Forecast output check | Reference result |
| --- | --- |
| Cell / high-DHW / annual summary rows | 3 / 3 / 33 |
| Annual polygons / forecasts per cell | 33 / 3,918 |
| Forecasts by DHW: <4 / 4 to <8 / ≥8 | 11,168 / 259 / 327 |
