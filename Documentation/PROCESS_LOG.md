Project is saved under Term Project\Geodatabase\WestHawaii_HeatStress

Set the map’s horizontal coordinate system to NAD 1983 UTM Zone 5N (EPSG:26905)

Hawaii.shp has 1764 feature polygons, NAD 1983 UTM zone 5N

Geoprocessing – Copy Features input Hawaii, output Hawaii habitat 2007. Outputs matched

Preserves input features/attributes in new feature class

Geoprocessing – Environments, NAD 1983 UTM Zone 5N unrestricted extent

Specify coordinate system for new feature class.

Georocessing – Create Fishnet, X=-156.1 Y=18.9-19.9 to bound the study area based on geographic coordinates for exact placement.

Geoprocessing – Project, study bounds to  NAD 1983 UTM Zone 5N, preserved shape

Geoprocessing – Clip, habitat to study AOI, 938 records

Geoprocessing – Calculate Geometry Attributes, recalculated geometries in hectacres to account for clipping – Summary statistics to verify that all features have geometries

Geoprocessing – Export Features, selected reefand hardbottom using expressions to create specific feature class, 437 records

Regional Satellite Grid – Heat Exposure

Created a 330-cell grid aligned with the downloaded CRW cell centers using 0.05° spacing and origin −156.150, 18.850 in WGS 1984. Added Cell_ID and projected the grid to NAD83 / UTM Zone 5N using NAD_1983_To_WGS_1984_3, preserving shape with a 1-meter maximum offset.

Intersect – Analysis Tools: Intersect WestHawaii_CRW_Grid__Project and WestHawaii_Habitat_2007 to preserve unknown habitats and habitat cells with both the category and cell ID.

Calculate Geometry Attributes – Data Management: Calculated new area for habitats split by cells.

Summary Statistics – Analysis Tools: Created hectacre sum for new habitat cells. Compared against class totals

Export Table – Conversion Tools: From our summary statistics, exported just the Reef and Hardbottom classes

Copy Features – Data Management: A copy of the grid to hold habitat areas and heat stress stats

Join Field – Data Management: added the reef and hardbottom class area statistics to analysis grid copy

Calculate Geometry Attributes – Data Management: Calculate cell center coordinates for original grid to match downloaded coordinates

Calculate Field – Data Management: combined the lat/lon of the cell center coordinates into a key

Join Field – Data Management: Added the lat, lon, key fields created in the original grid to the analysis grid copy

Merge – Data Management: merged monthly CSV files into one dataset

Export Table – Conversion Tools: Remove unit rows from CSV dataset

Calculate Field – Data Management: combined lat/lon from dataset to matching key

Calculate Field – Data Management: wrote python function to create numeric DHW values (Double field in °C-weeks) while preserving missing data

Calculate Field – Data Management created event year, valid DHW, GE 4 and GE 8 (flags for DHW ≥4 and ≥8 °C-weeks)

Summary Statistics – Analysis Tools: Group by cell and year to see heat stress record in that cell for both years.

Export Table – Conversion Tools: created standalone 2015/2019 annual summaries

Copy Features –  Data Management: Creating separate grids for 2015/2019

Join Field – Data Management: add the heat stress statistics to the year grids

Calculate Field – Data Management: Add heat-stress classes to each year layer

Apply Symbology from Layer – Data Management: After adjusting WestHawaii_CRW_2019 grid symbology, apply the same symbology to 2015

And now we have our first comparison!!

Select Layer By Attribute: Data Management – select the reef and hardbottom tiles

Summary Statistics: Data Management - The case fields group their habitat areas by year and heat-stress category

Calculate Field: Data Management – express each category as a percentage of all mapped reef/hardbottom area in the AOI, percentage of the area that makes up the assessed area. Uses current area summaries to define percentages.

key interpretation: 100% of assessed mapped reef/hardbottom area reached ≥8 °C-weeks in 2015, compared with 76.35% in 2019

Calculate Field: Data Management - retain area in both qualifying categories, assign zero to “Below 4,” and preserve missing DHW. Python function to handle No valid DHW category.

Summarize Statistics: Data Management: Summarize the thresholds per year

Within the assessed mapped reef/hardbottom footprint, area reaching DHW ≥4 and ≥8 °C-weeks was lower in 2019 than in 2015. This result does not support H1’s predicted direction.

Export Table – Use SQL expression to select only the cells centers that fall within our AOI

Merge – Merge the two tables

Summary Statistics: Max DHW CW, Sum GE4, Sum GE8 for median, minimum, maximum.

Regional summaries used the same 135 satellite cells with centers inside the AOI and 365 valid DHW observations in each year. Calculated cell-based median, minimum, and maximum annual peak DHW and days at DHW ≥4 and ≥8. The 117 AOI cells without valid DHW were excluded from these numerical summaries.

Mapped days at DHW ≥8 using common display classes of 0, 1–30, 31–60, and 61–90 days for both years. Restricted duration layers to AOI cell centers and displayed cells without valid DHW separately.

Matched the 135 common, complete-year AOI water cells by Cell_ID. Calculated change in days at DHW ≥8 as 2019 minus 2015; negative values indicate fewer threshold days in 2019.

Of the 135 assessed AOI cells, 129 had fewer days at DHW ≥8 in 2019, six were unchanged, and none had more. Changes ranged from −63 to 0 days.

Across 135 matched valid cells, the median change in days with DHW ≥ 8 was −16 days, ranging from −63 to 0 days. Change was calculated as 2019 minus 2015.

| Measure | 2015 median (range) | 2019 median (range) |
| --- | --- | --- |
| Annual peak DHW, °C-weeks | 11.64 (6.84–13.87) | 10.39 (0.16–11.86) |
| Days with DHW ≥4 | 99 (80–106) | 101 (0–104) |
| Days with DHW ≥8 | 67 (0–76) | 49 (0–63) |
