# CanoPy

CanoPy is the Python module for the Georgia Canopy Analysis 2009 project
sponsored by the Georgia Forestry Commission (GFC). For more details about this
project including the technical manual, please visit [its wiki
page](https://gislab.isnew.info/canopy).

## Requirements

* ArcGIS Desktop 10.x
* ArcPy
* Python 2 standard module: os
* Feature Analyst (TM) by the Textron Systems
* Automated Feature Extraction (AFE) models trained using Feature Analyst

We are currently planning on developing a fully open source solution without
using ArcGIS and Feature Analyst.

## Usage

1. Copy `canopy_config-example.py` to `canopy_config.py`
1. Edit `canopy_config.py` to recognize your layers and folder structures
1. Start ArcMap
1. Add Physiographic_Districts_GA.shp. Its layer name is `phyregs_layer` in
   `canopy_config.py`
1. Add naip_ga_2009_1m_m4b.shp. Its layer name is `naipqq_layer` in
   `canopy_config.py`
1. Open the Python window from within ArcMap
1. Change the current directory to the canopy module folder
   ```python
   import os
   os.chdir('C:/path/to/the/canopy/module')
   ```
   or
   ```python
   import sys
   sys.path.append('C:/path/to/the/canopy/module')
   ```
1. Import the canopy module
   ```python
   import canopy
   ```
1. Assign physiographic region IDs to the naipqq layer
   ```python
   canopy.assign_phyregs_to_naipqq()
   ```
1. Add physiographic region IDs to process to `phyreg_ids`
   ```python
   phyreg_ids = [8, 7]
   ```
1. Reproject original NAIP QQ tiles to the target projection
   ```python
   canopy.reproject_input_tiles(phyreg_ids)
   ```
1. Run trained AFE models to classify canopy and non-canopy cells
1. Convert AFE output files to the final seamless canopy GeoTIFF file per
   physiographic region
   ```python
   canopy.convert_afe_to_canopy_tiff(phyreg_ids)
   ```

## Project Team

* Huidae Cho, Ph.D., Assistant Professor of Geospatial Science and Computing,
  IESA, UNG
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

This work was supported by the Georgia Forestry Commission through the Georgia
Statewide Canopy Assessment Phase I: Canopy Analysis 2009 project grant.

## Grant Disclaimer

The work upon which this software is based was funded in whole or in part
through an Urban and Community Forestry grant awarded by the Southern Region,
State and Private Forestry, U.S. Forest Service and administered by the Georgia
Forestry Commission.
