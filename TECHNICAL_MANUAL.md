# CanoPy Technical Manual

This document outlines the uses and methodology of the functions contained within the CanoPy module.

## Introduction

CanoPy is the Python module for the Georgia Canopy Analysis 2009 project sponsored by the Georgia Forestry Commission (GFC). The project grant was awarded to Dr. Huidae Cho in the Institute for Environmental and Spatial Analysis (IESA) at the University of North Georgia (UNG).

For further background information view the CanoPy [README](README.md).

## Requirements

* ArcGIS Desktop 10.x
* ArcPy
* Python 2 standard module: os
* Feature Analyst (TM) by the Textron Systems
* Automated Feature Extraction (AFE) models trained using Feature Analyst

We are currently planning on developing a fully open source solution without using ArcGIS and Feature Analyst.

## CanoPy Config Variables

Contained in `canopy_config.py` are all the data paths that `CanoPy` functions operate with.
Example configuration can be found in `canopy_config-example.py` and copied into `canopy_config.py`

### `phyregs_layer`

* Type: `str`
* Layer containing polygon features for all physiographic regions.
* Required attribute fields:
    * `NAME` (Text)
    * `PHYSIO_ID` (Long)
    * `AREA` (Float)
* Example: `phyregs_layer = 'Physiographic_Districts_GA'`

### `naipqq_layer`

* Type: `str`
* Layer containing polygon features for all NAIP quarter quad tiles
* Required attribute field
    * `FileName` (Text)
* Example: `naipqq_layer = 'naip_ga_2009_1m_m4b'`

### `naipqq_phyregs_field`

* Type: `str`
* This output text field will be created in the naipqq layer by assign_phyregs_to_naipqq().
* PHSYIO_ID's from `physregs_layer` in which a `naipqq_layer` polygon is contained are out put into this field.
    * Output Format: (,#,#,...)
* Example: `naipqq_phyregs_field = 'phyregs'`

### `naip_path`

* Type: `str`
* Input folder in which NAIP imagery is stored.
* The structure of this input folder is defined by USDA, the original source of
  NAIP imagery. Under this folder are multiple 5-digit numeric folders that
  contain actual imagery GeoTIFF files.
  ```textmate
    F:/Georgia/ga/
                   34083/
                          m_3408301_ne_17_1_20090929.tif
                          m_3408301_ne_17_1_20090930.tif
                          ...
                   34084/
                          m_3408407_ne_16_1_20090930.tif
                          m_3408407_nw_16_1_20090930.tif
                          ...
                   ...
  ```
* Example: `naip_path = 'F:/Georgia/ga'`

### `spatref_wkid`

* Type: `int`
* Takes desired output coordinate system in WKID format.
*  Well-Known IDs (WKIDs) are numeric identifiers for coordinate systems
    administered by Esri.  This variable specifies the target spatial reference
    for output files.
* Standard used for CanoPy is WKID 102039, USA Contiguous Albers Equal Area Conic USGS version.
* Example: `spatref_wkid = 102039`

### `project_path`

* Type: `str`
* Folder path with which all other output paths are determined.
* The default structure of the project folder is defined as follows:
  ```textmate
  C:/.../ (project_path)
         Data/
              Physiographic_Districts_GA.shp (added as a layer)
         Results/
                 gtpoints_Winder_Slope.shp
                 ...
         2009 Analysis/ (analysis_path)
                       Data/
                            naip_ga_2009_1m_m4b.shp (added as a layer)
                            snaprast.tif (snaprast_path)
                 Results/ (results_path)
                         Winder_Slope/ (physiographic region name)
                                      Inputs/
                                             reprojected NAIP tiles
                                      Outputs/
                                              intermediate output tiles
                                              canopy_2009_Winder_Slope.tif
         2019 Analysis/ (analysis_path)
                       Data/
                            naip_ga_2019_1m_m4b.shp (added as a layer)
                            snaprast.tif (snaprast_path)
                 Results/ (results_path)
                         Winder_Slope/ (physiographic region name)
                                      Inputs/
                                             reprojected NAIP tiles
                                      Outputs/
                                              intermediate output tiles
                                              canopy_2019_Winder_Slope.tif
         ...
  ```
* **NOTE:** Output folder must be manually created. It is used when running Feature Analyst and is _**NOT**_ created by CanoPy.
* Example: `project_path = 'C:/work/Research/GFC Canopy Assessment'`

### `analysis_path_format`

* Type: `str`
* This variable specifies the format of the analysis path for one year.
* Example: `analysis_path_format = '%s/%%d Analysis' % project_path`

###  `analysis_year`

* Type: `int`
* Specifies year for analysis
* Example: `analysis_year = 2009`

### `snaprast_path`

* Type: `str`
* This input/output raster is used to snap NAIP tiles to a consistent grid
  system. If this file does not already exist, the filename part of
  snaprast_path must be 'r' + the filename of an existing original NAIP tile so
  that reproject_input_tiles() can automatically create it based on the folder
  structure of the NAIP imagery data (naip_path).
* Example: `snaprast_path = '%s/Data/rm_3408504_nw_16_1_20090824.tif' % analysis_path`

### `results_path`

* Type: `str`
* Where all results will be stored
* Example: `results_path = '%s/Results' % analysis_path`

## CanoPy Functions

All functions designed for preproccessing NAIP imagery and for postprocessing trained/classified canopy tiles  in addition
to utility functions are contained within `canopy.py`.

**NOTE:** `physregs_layer` and `naipqq_layer` must be added to open ArcMap or ArcGIS Pro dataframe for function to run.

### Preprocessing

#### `canopy.assign_phyregs_to_naipqq()`

* This function adds the phyregs field to the NAIP QQ shapefile and populates
  it with physiographic region IDs that intersect each NAIP tile.

* Parameters:
  * None

* Input data assigned with `canopy_config`:
  * `phyregs_layer = canopy_config.phyregs_layer`
  * `naipqq_layer = canopy_config.naipqq_layer`
  * `naipqq_phyregs_field = canopy_config.naipqq_phyregs_field`

* Process:

  1. The data fields of the input NAIP qq shapefile are read using `arcpy.ListFields` and a new text field titled
     `naip_phyregs_field` is added. If the field already exists, then it is deleted and a new field is created.
  2. Using `arcpy.CalculateField_managment` a comma ',' is inserted into the newly created `naip_phyregs_field`.
     This becomes important as the format for the `naip_phyregs_field` must be ',#,#,...,' to allow for SQL statments
     in following functions to be able to read the `naip_phyregs_field` properly. The SQL selections will allow for
     the right NAIP tiles to be computed as the NAIP qq shapedfile has a corresponding field for file names.
  3. All selections are cleared, and now each NAIP qq polygon will contain the `naip_phyregs_field` filled with the
     ID's of physical regions that the qq tile intersects.

#### `canopy.reproject_input_tiles(phyreg_ids)`

* This function reprojects and snaps the NAIP tiles that intersect selected
  physiographic regions.

* Parameters:
    * `phyreg_ids` (`str`): IDs of physical regions to process

* Input data assigned with `canopy_config`:
    * `phyregs_layer = canopy_config.phyregs_layer`
    * `naipqq_layer = canopy_config.naipqq_layer`
    * `naipqq_phyregs_field = canopy_config.naipqq_phyregs_field`
    * `spatref_wkid = canopy_config.spatref_wkid`
    * `snaprast_path = canopy_config.snaprast_path`
    * `naip_path = canopy_config.naip_path`
    * `results_path = canopy_config.results_path`

* Process:

  1. The spatial reference desired is set using the WKID specified in the `canopy_config` using `arcpy.SpatialReference`
     which reads the WKID.
  2. If the snap raster does not exist within the `snaprast_path` then it is created and `arcpy.env.snapRaster` is used
     to set all output cell alignments to match the snap.
  3. All NAIP tiles intersecting the input `phyreg_ids` are selected using an SQL clause to select the `phyreg_ids` then
     reading the file name field from each selected NAIP qq polygon.
  4. Using `arcpy.ProjectRaster_managment` selected the selected NAIp are reprojected to the specified WKID and saved as outputs and the prefix 'r'
     is added to the file name.
  5. The outputs of this function are saved in an inputs folder and are what will used by Textron's Feature Analysis.

### Postprocessing

#### `canopy.convert_afe_to_final_tiles(phyreg_ids)`

* This function converts Textron's Feature Analyst classified outputs to final TIFF files

* Parameters:
  * `phyreg_ids` (`str`): IDs of physical regions to process

* Input data assigned with `canopy_config`:
  * `phyregs_layer = canopy_config.phyregs_layer`
  * `naipqq_layer = canopy_config.naipqq_layer`
  * `naipqq_phyregs_field = canopy_config.naipqq_phyregs_field`
  * `snaprast_path = canopy_config.snaprast_path`
  * `results_path = canopy_config.results_path`

* Process:

  1. All NAIP tiles in the desired physiographic region are first selected using an  SQL statement to select the input
     physio id.
  2. The file names from the NAIP qq shapefile with the the reprojected prefix are used to as the outputs folder created to
     save the classified imagery is walked through.
  3. Conversion necessary as some AFE models used in feature analysis output TIFF files and some output shapefiles.
     1. If the file is a shapefile then it is converted to raster with classes 1 and 0.
     2. if the file is a TIFF file is the values are reclassified from 1 to 0 and 2 to 1.
     3. If the file has already run through this function and has the appropriate prefix then nothing happens to it.
  4. Outputs are saved in the outputs folder with the prefix 'fr'.

#### `canopy.clip_final_tiles(phyreg_ids)`

* This function clips final tiles to their respective NAIP qq area to eliminate overlap.

* Parameters:
  * `phyreg_ids` (`str`): IDs of physical regions to process

* Input data assigned with `canopy_config`:
  * `phyregs_layer = canopy_config.phyregs_layer`
  * `naipqq_layer = canopy_config.naipqq_layer`
  * `naipqq_phyregs_field = canopy_config.naipqq_phyregs_field`
  * `snaprast_path = canopy_config.snaprast_path`
  * `results_path = canopy_config.results_path`

* Process:

  1. First the `OID` field of the entire NAIP qq shapefile is encoded.
  2. All NAIP tiles in the desired physiographic region are first selected using an  SQL statement to select the input
     physio id.
  3. The output files from `canopy.convert_afe_to_final_tiles` are looped over and using the corresponding `OID` field
     are then clipped to their respective NAIP qq polygons.
  4. If the tile has already been clipped and has the appropriate prefix, then it will be skipped. If not then the tile
     will be clipped and the output TIFF will have the prefix 'cfr'.

#### `mosaic_clipped_final_tiles(phyreg_ids)`

* This function mosaics clipped final TIFF and then clips the mosaicked files to their corresponding physiographic
  regions

* Parameters:
  * `phyreg_ids` (`str`): IDs of physical regions to process

* Input data assigned with `canopy_config`:
  * `phyregs_layer = canopy_config.phyregs_layer`
  * `naipqq_layer = canopy_config.naipqq_layer`
  * `naipqq_phyregs_field = canopy_config.naipqq_phyregs_field`
  * `analysis_year = canopy_config.analysis_year`
  * `snaprast_path = canopy_config.snaprast_path`
  * `results_path = canopy_config.results_path`

* Process:

  1. All NAIP tiles in the input physiographic regions are first selected using an  SQL statement to select the input
     physio id.
  2. If the mosaicked file with the analysis year set by the `canopy_config` file exists the function ends.
     If no mosaiked layer with the analysis year exists then the process continues.
  3. Input tiles to be mosiacked are products from `canopy.clip_final_tiles` with the prefix 'cfr'.
  4. Mosiacking occurs using `arcpy.MosaicToNewRaster` to create the output raster as a new 2 bit TIF file.
  5. The new mosaiked data set is clipped to the outline of the physiographic region with the corresponding physiographic
     id.

#### `canopy.convert_afe_to_canopy_tif(phyreg_ids)`

* This function is a wrapper function that converts AFE outputs to the final canopy TIFF file by invoking
  `convert_afe_to_final_tiles()`, `clip_final_tiles()`, and `mosaic_clipped_final_tiles()` in the correct order.

* Parameters:
  * `phyreg_ids` (`str`): IDs of physical regions to process

* Input data assigned with `canopy_config`:
  * `phyregs_layer = canopy_config.phyregs_layer`
  * `naipqq_layer = canopy_config.naipqq_layer`
  * `naipqq_phyregs_field = canopy_config.naipqq_phyregs_field`
  * `analysis_year = canopy_config.analysis_year`
  * `snaprast_path = canopy_config.snaprast_path`
  * `results_path = canopy_config.results_path`

### Utility Functions

#### `generate_ground_truthing_points(phyreg_ids, analysis_years, point_count)`

* **NOTE:** This function is still a work in progress.

* This function generates randomized points for ground truthing with fields for corresponding analysis years.

* Parameters:
  * `phyreg_ids` | String : ID's of physical regions to process
  * `analysis_years` | Integer : Years to add as fields
  * `point_count` | Integer : Number of randomly generate points in each region.

* Input data assigned with `canopy_config`:
  * `phyregs_layer = canopy_config.phyregs_layer`
  * `spatref_wkid = canopy_config.spatref_wkid`
  * `project_path = canopy_config.project_path`
  * `analysis_path_format = canopy_config.analysis_path_format`

* Process:

  1. The physiographic regions are selected using the input physio id.
  2. Random points in each region are created using `arcpy.CreateRandomPoints`.
  3. Fields are created in each point shapefile with the header of 'GT_`analysis_years`'
  4. The values of each classified cell that contains the randomized points will be read. This will be done using a NumPy

## Authors:
Owen Smith, IESA, University of North Georgia
