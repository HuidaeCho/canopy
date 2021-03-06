config_template = """

################################################################################
# Name:    config_template.py
# Purpose: This module provides example configurations for the canopy.py
#          module. Please copy this file to canopy_config.py and edit the
#          latter.
# Authors:  Huidae Cho, Ph.D., IESA, University of North Georgia
#           Owen Smith, IESA, University of North Georgia
# Since:   November 29, 2019
# Grant:   Sponsored by the Georgia Forestry Commission through the Georgia
#          Statewide Canopy Assessment Phase I: Canopy Analysis 2009 project
################################################################################

[config]

# Predicate parameter where 1 = True and 0 = False. Determined whether or not 
# to print elapsed times for processing functions.

verbosity = 1

# This input layer contains the polygon features for all physiographic regions.
# Data source: Physiographic_Districts_GA.zip
#              Michael Torbett, GFC, October 3, 2019 at 10:48am
# Required fields:
#   NAME (Text)
#   PHYSIO_ID (Long)
#   AREA (Float)
phyregs_layer = Physiographic_Districts_GA

# This output double field will be created in the phyregs layer by
# assign_phyregs_to_naipqq().
phyregs_area_sqkm_field = AREA_SQKM

# This input layer contains the polygon features for all NAIP tiles.
# Data source: ga_naip09qq.zip
#              David Parry, USDA, September 30, 2019 at 9:48am
# Required field:
#   FileName (Text)
naipqq_layer = naip_ga_2009_1m_m4b

# This output text field will be created in the naipqq layer by
# assign_phyregs_to_naipqq().
naipqq_phyregs_field = PHYREGS

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
naip_path = F:/Georgia/ga

# Well-Known IDs (WKIDs) are numeric identifiers for coordinate systems
# administered by Esri.  This variable specifies the target spatial reference
# for output files. For more information about WKIDs, please refer to the
# following sources:
#   https://developers.arcgis.com/rest/services-reference/projected-coordinate-systems.htm
#   https://pro.arcgis.com/en/pro-app/arcpy/classes/pdf/projected_coordinate_systems.pdf
#   http://resources.esri.com/help/9.3/arcgisserver/apis/rest/pcs.html
# WKID 102039 is USA Contiguous Albers Equal Area Conic USGS version.
spatref_wkid = 102039

# The default structure of the project folder is defined as follows:
#   C:/.../ (project_path)
#          Data/
#               Physiographic_Districts_GA.shp (added as a layer)
#          2009 Analysis/ (analysis_path)
#                        Data/
#                             naip_ga_2009_1m_m4b.shp (added as a layer)
#                             snaprast.tif (snaprast_path)
#                        Results/ (results_path)
#                                Winder_Slope/ (physiographic region name)
#                                             Inputs/
#                                                    reprojected NAIP tiles
#                                             Outputs/
#                                                     intermediate output tiles
#                                                     canopy_2009_Winder_Slope.tif
#                                                     gtpoints_2009_Winder_Slope.tif
#                                ...
#          2019 Analysis/ (analysis_path)
#                        Data/
#                             naip_ga_2019_1m_m4b.shp (added as a layer)
#                             snaprast.tif (snaprast_path)
#                        Results/ (results_path)
#                                Winder_Slope/ (physiographic region name)
#                                             Inputs/
#                                                    reprojected NAIP tiles
#                                             Outputs/
#                                                     intermediate output tiles
#                                                     canopy_2019_Winder_Slope.tif
#                                                     gtpoints_2019_Winder_Slope.tif
#                                ...
#          ...

# This variable specifies the path to the project root folder.
project_path = C:/work/Research/GFC Canopy Assessment

# This variable specifies the year for analysis.
analysis_year = 2009

# This variable specifies the format of the analysis path for one year.
analysis_path_format = %(project_path)s/%(analysis_year)s Analysis

# This variable is used only in this file to define snaprast_path and
# results_path.
analysis_path = %(analysis_path_format)s

# This input/output raster is used to snap NAIP tiles to a consistent grid
# system. If this file does not already exist, the filename part of
# snaprast_path must be 'r' + the filename of an existing original NAIP tile so
# that reproject_input_tiles() can automatically create it based on the folder
# structure of the NAIP imagery data (naip_path).
snaprast_path = %(analysis_path)s/Data/rm_3408504_nw_16_1_20090824.tif

# This folder will contain all result files.
results_path = %(analysis_path)s/Results 

# This list contains all physiographic region IDs, but it is not used at all.
# reproject_input_tiles(), convert_afe_to_final_tiles(), clip_final_tiles(),
# and mosaic_clipped_final_tiles() take a list of physiographic region IDs (a
# subset of this list) to process the specified regions only. This list is
# defined here as a reference only.
phyreg_ids = [8,7,2,14,22,5,4,12,9,11,20,3,6,26,13,17,24,25,15,23,21,16,18,19]

# This list contains physiographic region IDs whose trained model produces an
# inverted result.
inverted_phyreg_ids = 5, 21, 12, 4, 11, 17, 2, 26, 20, 16
"""
