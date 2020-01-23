################################################################################
# Name:     canopy_config.py
# Purpose:  This module provides configurations to the canopy.py module.
# Author:   Huidae Cho
# Since:    November 29, 2019
# Grant:    Sponsored by the Georgia Forestry Commission through the Georgia
#           Statewide Canopy Assessment Phase I: Canopy Analysis 2009 project
################################################################################

# This input layer contains the polygon features for all physiographic regions.
# Data source: Physiographic_Districts_GA.zip
#              Michael Torbett, GFC, October 3, 2019 at 10:48am
# Required fields:
#   NAME (Text)
#   PHYSIO_ID (Long)
#   AREA (Float)
phyregs_layer = 'Physiographic_Districts_GA'

# This input layer contains the polygon features for all NAIP tiles.
# Data source: ga_naip09qq.zip
#              David Parry, USDA, September 30, 2019 at 9:48am
# Required fields:
#   FID (Object ID)
#   FileName (Text)
naipqq_layer = 'naip_ga_2009_1m_m4b'

# This output text field will be created in the naipqq layer by
# assign_phyregs_to_naipqq().
naipqq_phyregs_field = 'phyregs'

# The structure of this input folder is defined by USDA, the original source of
# NAIP imagery. Under this folder are multiple 5-digit numeric folders that
# contain actual imagery GeoTIFF files. For example,
#   F:/Georgia/ga/
#                 34083/
#                       m_3408301_ne_17_1_20090929.tif
#                       m_3408301_ne_17_1_20090930.tif
#                       ...
#                 34084/
#                       m_3408407_ne_16_1_20090930.tif
#                       m_3408407_nw_16_1_20090930.tif
#                       ...
#                 ...
naip_path = 'F:/Georgia/ga'

# The default structure of the project folder is defined as follows:
# C:/.../2009 Analysis/ (project_path)
#                      Data/
#                           Physiographic_Districts_GA.shp (added as a layer)
#                           naip_ga_2009_1m_m4b.shp (added as a layer)
#                           snaprast.tif (snaprast_path)
#                           spatref.tif (spatrast_path)
#                      Results/ (results_path)
#                              Winder_Slope/ (physiographic region name)
#                                           Inputs/
#                                                  reprojected NAIP tiles
#                                           Outputs/
#                                                  intermediate output tiles
#                                                  canopy_2009_Winder_Slope.tif
#                              ...

# This variable is used only in this file to define snaprast_path,
# spatref_path, and results_path.
project_path = 'C:/work/Research/GFC Canopy Assessment/2009 Analysis'

# This input/output raster is used to snap NAIP tiles to a consistent grid
# system. If this file does not already exist, the filename part of
# snaprast_path must be 'r' + the filename of an existing original NAIP tile so
# that reproject_input_tiles() can automatically create it based on the folder
# structure of the NAIP imagery data (naip_path).
snaprast_path = '%s/Data/rm_3408504_nw_16_1_20090824.tif' % project_path

# This input raster is used to reproject original NAIP tiles to the target
# spatial reference. This file may be obtained from a previous study.
spatref_path = '%s/Data/LMD_Canopy.tif' % project_path

# This folder will contain all result files.
results_path = '%s/Results' % project_path

# This list contains all physiographic region IDs, but it is not used at all.
# reproject_input_tiles(), convert_afe_to_final_tiles(), clip_final_tiles(),
# and mosaic_clipped_final_tiles() take a list of physiographic region IDs (a
# subset of this list) to process the specified regions only. This list is
# defined here as a reference only.
phyreg_ids = [8,7,2,14,22,5,4,12,9,11,20,3,6,26,13,17,24,25,15,23,21,16,18,19]