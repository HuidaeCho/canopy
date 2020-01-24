# CanoPy

CanoPy is the Python module for the Georgia Canopy Analysis 2009 project sponsored by the Georgia Forestry Commission (GFC). The project grant was awarded to Dr. Huidae Cho in the Institute for Environmental and Spatial Analysis (IESA) at the University of North Georgia (UNG).

We developed this module to conduct the Georgia statewide canopy analysis study using the 2009 National Agriculture Imagery Program (NAIP) imagery data. Georgia comprises 24 physiographic regions for which the GFC provided a shapefile (``phyregs_layer`` in ``canopy_config-example.py``). This shapefile includes three useful fields: NAME (Text), PHYSIO_ID (Long), and AREA (Float).

To assess tree canopy, we needed four bands including red (R), green (G), blue (B), and near-infrared (NIR). The three-band RGB NAIP imagery data is available freely online at https://nrcs.app.box.com/v/naip. However, the four-band NAIP imagery is not available online and needs to be ordered from the United States Department of Agriculture (USDA). They ship it on an external hard drive that has a hierarchical folder structure (``naip_path`` in ``canopy_config-example.py``). Not all NAIP tiles are in one folder; instead, they are organized in multiple folders following their file naming scheme in the quarter quad (QQ) polygon shapefile that they provide for data acquisitions (``naipqq_layer`` in ``canopy_config-example.py``). The QQ polygon shapefile provides the filename of each QQ tile in the FileName (Text) field.

Since our study is statewide, there are a large number of NAIP QQ imagery tiles&mdash;specifically, 3,913 GeoTIFF files across the entire Georgia&mdash;and it would not be feasible to manually pre-process these tiles before we feed them to a canopy classification algorithm. It is not only the number of input tiles, but also the number of output files that makes it challenging to complete this analysis efficiently. This module provides utility functions for pre-processing input tiles and post-processing output files to finally create the final seamless canopy raster for specified physiographic regions.

## Requirements

* ArcGIS Desktop 10.x
* ArcPy
* Python 2 standard modules: os, json
* Feature Analyst (TM) by the Textron Systems
* Automated Feature Extraction (AFE) models trained using Feature Analyst

We are currently planning on developing a fully open source solution without using ArcGIS and Feature Analyst.

## CanoPy Config | `canopy_config.py`

Contained in `canopy_config.py` are all the data paths that `CanoPy` functions operate with.
Example configuration can be found in `canopy_config-example.py` and copied into `canopy_config.py`

### **`canopy_config.py` Parameters**

1. _**`phyregs_layer` | String**_
    * Layer containing polgon features for all physiographic regions.
    * Required attribute fields:
        * NAME (Text)
        * PHYSIO_ID (Long)
        * AREA (Float)
    * Example: `phyregs_layer = 'Physiographic_Districts_GA'`

1. _**`naipqq_layer` | String**_
    * Layer containing polygon features for all NAIP quarter quad tiles
    * Required attribute fields
        * FID (Object ID)
        * FileName (Text)
    * Example: `naipqq_layer = 'naip_ga_2009_1m_m4b'`

1. _**`naipqq_phyregs_field` | String**_
    * This output text field will be created in the naipqq layer by assign_phyregs_to_naipqq().
    * PHSYIO_ID's from `physregs_layer` in which a `naipqq_layer` polygon is contained are out put into this field.
        * Output Format: (,#,#,...)
    * Example: `naipqq_phyregs_field = 'phyregs'`
        
1. _**`naip_path` | String**_
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
    
1. _**`spatref_wkid` | Integer**_
    * Takes desired output coordinate system in WKID format. 
    *  Well-Known IDs (WKIDs) are numeric identifiers for coordinate systems
        administered by Esri.  This variable specifies the target spatial reference
        for output files.
    * Standard used for CanoPy is WKID 102039, USA Contiguous Albers Equal Area Conic USGS version.
    * Example: `spatref_wkid = 102039`
    
1. _**`project_path` | String**_
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
                             ...
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

 1. _**`analysis_path_format` | String**_
    * This variable specifies the format of the analysis path for one year.
    * Example: `analysis_path_format = '%s/%%d Analysis' % project_path`
    
 1. _**`analysis_year` | Integer**_
    * Specifies year for analysis
    * Example: `analysis_year = 2009`
    
 1. _**`snaprast_path` | String**_
    * This input/output raster is used to snap NAIP tiles to a consistent grid
      system. If this file does not already exist, the filename part of
      snaprast_path must be 'r' + the filename of an existing original NAIP tile so
      that reproject_input_tiles() can automatically create it based on the folder
      structure of the NAIP imagery data (naip_path).
    * Example: `snaprast_path = '%s/Data/rm_3408504_nw_16_1_20090824.tif' % analysis_path`
 
 1. _**`results_path` | String**_
    * Where all results will be stored
    * Example: `results_path = '%s/Results' % analysis_path`
 
## CanoPy Functions
 
TODO: CanoPy functions


---
##### Authors:
 Owen Smith, IESA, University of North Georgia

