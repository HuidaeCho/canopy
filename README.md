# CanoPy

CanoPy is the Python module for the Georgia Canopy Analysis 2009 project sponsored by the Georgia Forestry Commission (GFC).

We developed this module to conduct the Georgia statewide canopy analysis study using the 2009 National Agriculture Imagery Program (NAIP) imagery data. To assess tree canopy, we needed four bands including red (R), green (G), blue (B), and near-infrared (NIR). The three-band RGB NAIP imagery data is available freely online at https://nrcs.app.box.com/v/naip. However, the four-band NAIP imagery is not available online and needs to be ordered from the United States Department of Agriculture (USDA). They ship it on an external hard drive that has a hierarchical folder structure (``naip_path`` in ``canopy_config-example.py``). Not all NAIP tiles are in one folder; instead, they are organized in multiple folders following their file naming scheme in the quarter quad (QQ) polygon shapefile they provide for data acquisitions (``naipqq_layer`` in ``canopy_config-example.py``). The QQ polygon shapefile provides the filename of each QQ tile in the FileName (Text) field.

Since our study is statewide, there are a large number of NAIP QQ imagery tiles&mdash;specifically, 3,913 GeoTIFF files across the entire Georgia&mdash;and it would not be feasible to manually pre-process these tiles before we feed them to a canopy classification algorithm. It is not only the number of input tiles, but also the number of output tiles that makes it challenging to complete this analysis efficiently. This module provides utility functions for pre-processing input tiles and post-processing output tiles to finally create the final seamless canopy raster for specified physiographic regions.

Georgia is split into 24 physiographic regions. GFC provided a shapefile for the physiographic regions in Georgia (``phyregs_layer`` in ``canopy_config-example.py``). This shapefile includes three useful fields: NAME (Text), PHYSIO_ID (Long), and AREA (Float).
