# CanoPy

CanoPy is the Python module for the Georgia Canopy Analysis 2009 project sponsored by the Georgia Forestry Commission (GFC). The project grant was awarded to Dr. Huidae Cho in the Institute for Environmental and Spatial Analysis (IESA) at the University of North Georgia (UNG).

We developed this module to conduct the Georgia statewide canopy analysis study using the 2009 National Agriculture Imagery Program (NAIP) imagery data. Georgia comprises 24 physiographic regions for which the GFC provided a shapefile (``phyregs_layer`` in ``canopy_config-example.py``). This shapefile includes three useful fields: NAME (Text), PHYSIO_ID (Long), and AREA (Float).

To assess tree canopy, we needed four bands including red (R), green (G), blue (B), and near-infrared (NIR). The three-band RGB NAIP imagery data is available freely online at https://nrcs.app.box.com/v/naip. However, the four-band NAIP imagery is not available online and needs to be ordered from the United States Department of Agriculture (USDA). They ship it on an external hard drive that has a hierarchical folder structure (``naip_path`` in ``canopy_config-example.py``). Not all NAIP tiles are in one folder; instead, they are organized in multiple folders following their file naming scheme in the quarter quad (QQ) polygon shapefile that they provide for data acquisitions (``naipqq_layer`` in ``canopy_config-example.py``). The QQ polygon shapefile provides the filename of each QQ tile in the FileName (Text) field.

Since our study is statewide, there are a large number of NAIP QQ imagery tiles&mdash;specifically, 3,913 GeoTIFF files across the entire Georgia&mdash;and it would not be feasible to manually pre-process these tiles before we feed them to a canopy classification algorithm. It is not only the number of input tiles, but also the number of output files that makes it challenging to complete this analysis efficiently. This module provides utility functions for pre-processing input tiles and post-processing output tiles to finally create the final seamless canopy raster for specified physiographic regions.

## Requirements

* ArcGIS Desktop 10.x
* ArcPy
* Python 2 standard modules: os, json
* Feature Analyst (TM) by the Textron Systems
* Automated Feature Extraction (AFE) models trained using Feature Analyst

We are currently planning on developing a fully open source solution without using ArcGIS and Feature Analyst.

## Usage

1. Copy ``canopy_config-example.py`` to ``canopy_config.py``
1. Edit ``canopy_config.py`` to recognize your folder structures and layers
1. Start ArcMap
1. Add Physiographic_Districts_GA.shp. Its layer name is ``phyregs_layer`` in ``canopy_config.py``
1. Add naip_ga_2009_1m_m4b.shp. Its layer name is ``naipqq_layer`` in ``canopy_config.py``
1. Open the Python window from within ArcMap
1. ``import os; os.chdir('C:/path/to/the/canopy/module')`` Change the current directory to the canopy module folder
1. ``import canopy`` Import the canopy module
1. ``assign_phyregs_to_naipqq()`` Assign physiographic region IDs to the naipqq layer
1. ``phyreg_ids = [8, 7]`` Add physiographic region IDs to process to ``phyreg_ids``
1. ``reproject_input_tiles(phyreg_ids)`` Reproject original NAIP QQ tiles to the target projection
1. Run trained AFE models to classify canopy and non-canopy cells
1. ``convert_afe_to_canopy_tiff(phyreg_ids)`` Convert AFE output files to the final seamless canopy GeoTIFF file per physiographic region

## Project Team

* Huidae Cho, Ph.D., Assistant Professor of Geospatial Science and Computing, IESA, UNG
  * Principal investigator
  * Python development
* Jennifer McCollum, Undergraduate Student, IESA, UNG
  * Research about Feature Analyst
  * Literature review
  * Documentation
* Owen Smith, Undergraduate Student, IESA, UNG
  * Python development
  * Technical documentation

## Acknowledgement

This work was supported by the Georgia Forestry Commission through the Georgia Statewide Canopy Assessment Phase I: Canopy Analysis 2009 project grant.
