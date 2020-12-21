################################################################################
# Name:    canopy.py
# Purpose: This module provides utility functions for preprocessing NAIP tiles
#          and postprocessing trained canopy tiles.
# Authors: Huidae Cho, Ph.D., Owen Smith, IESA, University of North Georgia
# Since:   November 29, 2019
# Grant:   Sponsored by the Georgia Forestry Commission through the Georgia
#          Statewide Canopy Assessment Project
#          Phase 1:   2009 Canopy Analysis
#          Phase 1.5: 2019 Canopy Analysis
#          Phase 2:   2009-2019 Canopy Change Analysis
################################################################################

import arcpy
import os
import sys
import glob
from .templates import config_template
from configparser import ConfigParser
import time
import numpy as np


class Canopy:
    '''
    Object to effectively manage the configuration of CanoPy and run
    the processing functions created.

    Attributes
    ----------
    config : str
        Path for initialized configuration file.
    phyregs_layer : str
        Layer containing polygon features for all physiographic regions.
    phyregs_area_sqkm_field : str
        Field name for computed area.
    naipqq_layer : str
        Name of the NAIP QQ feature layer.
    naipqq_phyregs_field : str
        Field name to make NAIP QQ's queryable based on physiographic
        region.
    naip_path : str
        Path to NAIP directory
    spatref_wkid : int
        WKID specifies the target spatial reference for all output files.
    snaprast_path : str
        This input/output raster is used to snap NAIP tiles to a
        consistent grid system. If this file does not already exist, the
        filename part of snaprast_path must be 'r' + the filename of an
        existing original NAIP tile so that reproject_input_tiles() can
        automatically create it based on the folder structure of the
        NAIP imagery data (naip_path).
    results_path : str
        Folder which will contain all outputs.
    analysis_year : int
        Specifies which year is being analyzed.
    phyreg_ids : list
        List of phyreg ids to process.

    Methods
    -------
    gen_cfg(config_path):
        Generates a template configuration file at the specified location.
    update_config(**parameters):
        Allows CanoPy attributes to be written directly in the generated *.cfg
        file.
    regions(phyregs):
        Adds the desired regions to self.phyreg_ids
    calculate_row_column(xy, rast_ext, rast_res):
        Calculates array row and column using x, y, extent, and
        resolution.
    assign_phyregs_to_naipqq():
        Adds the phyregs field to the NAIP QQ shapefile and
        populates it with physiographic region IDs that intersect each NAIP
        tile.
    reproject_naip_tiles():
        Function reprojects and snaps the NAIP tiles that intersect
        selected physiographic regions.
    convert_afe_to_final_tiles():
        Converts AFE outputs to final TIFF files.
    clip_final_tiles():
        Clips final TIFF files.
    mosaic_clipped_final_tiles():
        Mosaics clipped final TIFF files and clips mosaicked files
        to physiographic regions.
    convert_afe_to_canopy_tif():
        A wrapper function that converts AFE outputs to the
        final canopy TIFF file by invoking convert_afe_to_final_tiles(),
        clip_final_tiles(), and mosaic_clipped_final_tiles() in the correct
        order.
    correct_inverted_canopy_tif(inverted_phyreg_ids):
        Corrects the values of mosaikced and clipped regions that
        have been inverted.
    convert_canopy_tif_to_shp():
        Converts the canopy TIFF files to shapefile.
    generate_gtpoints(phyreg_ids, min_area_sqkm, max_area_sqkm, min_points,
                      max_points):
        Generates randomized points for ground truthing.
    update_gtpoints(self, old_points, phyreg_ids)
        Copies a previous years GT points but with the new years GT values.
    add_naip_tiles_for_gt(gtpoints):
        Adds NAIP imagery where a ground truthing point is located.
    '''

    def __init__(self, config_path):
        '''
        Parameters
        ----------
            config_path : str
                Path which points to the *.cfg path which serve as the
                configuration for CanoPy. If one does not exist it will be
                automatically generated using the template configuration.
        '''

        # Add .cfg extentsion to file path if not present
        if not os.path.splitext(config_path)[1] == '.cfg':
            config_path = '%s%s' % (config_path, '.cfg')

        # Generate template configuration file if file path does not exist.
        if os.path.exists(config_path):
            self.config = config_path
        if not os.path.exists(config_path):
            self.gen_cfg(config_path)
            self.config = config_path
        self.__reload_cfg()

    def __timed(func):
        # Decorative function for verbose time outputs
        def wrapper(self, *args, **kwargs):
            if self.verbosity == 1:
                start_time = time.time()
                func(self, *args, **kwargs)
                end_time = time.time() - start_time
                print(f"---- {end_time / 60} minutes elapsed----")
            else:
                func(self, *args, **kwargs)

        return wrapper

    def __get_cellsizes(self, input_raster):
        # Returns a tuple of the x,y cell dimensions of raster
        x = arcpy.Raster(input_raster).meanCellWidth
        y = arcpy.Raster(input_raster).meanCellHeight
        return x, y

    def __check_float(self, x1, x2, tolerance):
        # Check if floats are within certain range or tolerance. Simple
        # predicate function.
        return abs(x1 - x2) <= tolerance

    def __check_snap(self, input_raster):

        # Get the xy cell dimensions of both the snap raster and the
        # input raster.
        snap_x, snap_y = self.__get_cellsizes(self.snaprast_path)
        in_x, in_y = self.__get_cellsizes(input_raster)

        # Determine if cells dimensions wall within tolerance. Needed as
        # reprojections can slightly skew float cell size,
        # e.g. 0.6 -> 0.599999...
        check_x = self.__check_float(snap_x, in_x, 0.0001)
        check_y = self.__check_float(snap_y, in_y, 0.0001)
        # If both dimensions fall within tolerance do nothing. If not then
        # raise error.
        try:
            if check_y is False and check_x is False:
                raise ValueError
        except ValueError:
            print("Invlaid snapraster cellsize: The snapraster cell size does \n"
                  "not match that of the input rasters cellsize.")
            sys.exit(1)

    def gen_cfg(self, config_path):
        '''
        Generates a template configuration file at the specified location.

        Parameters
        ----------
            config_path : str
        '''
        # Write config file template
        with open(config_path, 'w') as f:
            f.write(config_template)
            f.close()
        print("CanoPy config generated at %s" % config_path)
        return config_path

    def __reload_cfg(self):
        '''
        Reloads the configuration parameters within the Canopy object if changes
        have been made to the *.cfg file. This allows for changes to be made to
        the overall configuration with out the object or the python environment
        having to be reinitalized.
        '''
        # Open configuration file with configparser
        conf = ConfigParser()
        conf.read(self.config)

        # Get individual attributes from configuration
        self.verbosity = int(conf.get('config', 'verbosity'))
        self.phyregs_layer = str.strip(conf.get('config', 'phyregs_layer'))
        self.phyregs_area_sqkm_field = str.strip(conf.get('config',
                                                    'phyregs_area_sqkm_field'))
        self.naipqq_layer = str.strip(conf.get('config', 'naipqq_layer'))
        self.naipqq_phyregs_field = str.strip(conf.get('config',
                                                       'naipqq_phyregs_field'))
        self.naip_path = str.strip(conf.get('config', 'naip_path'))
        self.spatref_wkid = int(conf.get('config', 'spatref_wkid'))
        self.snaprast_path = str.strip(conf.get('config', 'snaprast_path'))
        self.results_path = str.strip(conf.get('config', 'results_path'))
        self.analysis_year = int(conf.get('config', 'analysis_year'))

    def update_config(self, **parameters):
        '''
        Updates the configuration parameters directly in the Canopy *.cfg file.

        Keyword Args
        ------------

        phyregs_layer: str
            This input layer contains the polygon features for all physiographic
            regions.
                Required fields:
                NAME (Text)
                PHYSIO_ID (Long)
                AREA (Float)
        naipqq_layer: str
            This input layer contains the polygon features for all NAIP tiles.
                Required field:
                FileName (Text)
        naipqq_phyregs_field: str
            This output text field will be created in the naipqq layer by
            assign_phyregs_to_naipqq().
        naip_path: str
            The structure of this input folder is defined by USDA, the original
            source of NAIP imagery. Under this folder are multiple 5-digit
            numeric folders that contain actual imagery GeoTIFF files.
            For example,
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
        spatref_wkid: int
            Well-Known IDs (WKIDs) are numeric identifiers for coordinate
            systems administered by Esri. This variable specifies the target
            spatial reference for output files
        project_path: str
            This variable specifies the path to the project root folder
            The default structure of the project folder is defined as follows:
            C:/.../ (project_path)
                Data/
                    Physiographic_Districts_GA.shp (added as a layer)
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
                                        gtpoints_2009_Winder_Slope.tif
                        ...
        analysis_year: int
            This variable specifies the year for analysis.
        snaprast_path: str
            This input/output raster is used to snap NAIP tiles to a consistent
            grid system. If this file does not already exist, the filename part
            of snaprast_path must be 'r' + the filename of an existing original
            NAIP tile so that reproject_input_tiles() can automatically create
            it based on the folder structure of the NAIP imagery data
            (naip_path).
        '''

        # Read the configuration file
        conf = ConfigParser(inline_comment_prefixes='#')
        conf.read(self.config)

        # List of parameters which can be edited by user.
        params = ["phyregs_layer", "naipqq_layer", "naipqq_phyregs_field",
                  "naip_path", "spatref_wkid", "project_path", "analysis_year",
                  "snaprast_path"]

        # iterate over key word parameters and if present, overwrite entry in
        # config file.
        for arg in parameters:
            for p in params:
                if arg is p:
                    # Get parameters entry from key word dictonary.
                    conf.set('config', arg, f'{parameters.get(arg)}')
        # Write file
        with open(self.config, 'w') as configfile:
            conf.write(configfile)
        # Reload the configuration within the CanoPy object.
        self.__reload_cfg()

    def regions(self, phyregs):
        '''
        Adds the desired regions to be generated.

        Parameters
        ----------
            phyregs : list
                List of physiographic region id's to be processed with CanoPy.
        '''
        # Populate phyregs_ids
        self.phyreg_ids = []
        for i in range(len(phyregs)):
            self.phyreg_ids.append(phyregs[i])

    def __calculate_row_column(self, xy, rast_ext, rast_res):
        '''
        This function calculates array row and column using x, y, extent, and
        resolution.

        Parameters
        ----------
            xy : list, tuple
                (x, y) coordinates
            rast_ext :
                raster extent
            rast_res : list, tuple
                (width, height) raster resolution

        Returns
        -------
            row, col
        '''
        x = xy[0]
        y = xy[1]
        w = rast_res[0]
        h = rast_res[1]
        row = int((rast_ext.YMax - y) / h)
        col = int((x - rast_ext.XMin) / w)
        return row, col

    def assign_phyregs_to_naipqq(self):
        '''
        This function adds the phyregs field to the NAIP QQ shapefile and
        populates it with physiographic region IDs that intersect each NAIP
        tile. This function needs to be run only once, but running it multiple
        times would not hurt either other than wasting computational resources.
        '''
        phyregs_layer = self.phyregs_layer
        phyregs_area_sqkm_field = self.phyregs_area_sqkm_field
        naipqq_layer = self.naipqq_layer
        naipqq_phyregs_field = self.naipqq_phyregs_field

        # calculate phyregs_area_sqkm_field
        fields = arcpy.ListFields(phyregs_layer, phyregs_area_sqkm_field)
        for field in fields:
            if field.name == phyregs_area_sqkm_field:
                arcpy.DeleteField_management(phyregs_layer,
                                             phyregs_area_sqkm_field)
                break
        arcpy.AddField_management(phyregs_layer, phyregs_area_sqkm_field,
                                  'DOUBLE')
        arcpy.CalculateGeometryAttributes_management(phyregs_layer,
                [[phyregs_area_sqkm_field, 'AREA']], '', 'SQUARE_KILOMETERS')

        # calculate naipqq_phyregs_field
        fields = arcpy.ListFields(naipqq_layer, naipqq_phyregs_field)
        for field in fields:
            if field.name == naipqq_phyregs_field:
                arcpy.DeleteField_management(naipqq_layer, naipqq_phyregs_field)
                break
        arcpy.AddField_management(naipqq_layer, naipqq_phyregs_field, 'TEXT',
                field_length=100)

        # make sure to clear selection because most geoprocessing tools use
        # selected features, if any
        arcpy.SelectLayerByAttribute_management(phyregs_layer,
                                                'CLEAR_SELECTION')
        arcpy.SelectLayerByAttribute_management(naipqq_layer,
                                                'CLEAR_SELECTION')

        # initialize the phyregs field to ,
        arcpy.CalculateField_management(naipqq_layer, naipqq_phyregs_field,
                                        '","')

        # for each physiographic region
        with arcpy.da.SearchCursor(phyregs_layer, ['NAME', 'PHYSIO_ID']) as cur:
            for row in sorted(cur):
                name = row[0]
                print(name)
                phyreg_id = row[1]
                # select the current physiographic region
                arcpy.SelectLayerByAttribute_management(phyregs_layer,
                        where_clause='PHYSIO_ID=%d' % phyreg_id)
                # select intersecting naip qq features
                arcpy.SelectLayerByLocation_management(naipqq_layer,
                        select_features=phyregs_layer)
                # append phyreg_id + , so the result becomes ,...,#,
                arcpy.CalculateField_management(naipqq_layer,
                                                naipqq_phyregs_field,
                        '!%s!+"%d,"' % (naipqq_phyregs_field, phyreg_id),
                        'PYTHON_9.3')

        # clear selection again
        arcpy.SelectLayerByAttribute_management(phyregs_layer,
                                                'CLEAR_SELECTION')
        arcpy.SelectLayerByAttribute_management(naipqq_layer,
                                                'CLEAR_SELECTION')

        print('Completed')

    @__timed
    def reproject_naip_tiles(self):
        '''
        This function reprojects and snaps the NAIP tiles that intersect
        selected physiographic regions.
        '''
        phyregs_layer = self.phyregs_layer
        naipqq_layer = self.naipqq_layer
        naipqq_phyregs_field = self.naipqq_phyregs_field
        spatref_wkid = self.spatref_wkid
        naip_path = self.naip_path
        results_path = self.results_path
        snaprast_path = self.snaprast_path

        spatref = arcpy.SpatialReference(spatref_wkid)

        arcpy.env.addOutputsToMap = False
        if not os.path.exists(snaprast_path):
            snaprast_file = os.path.basename(snaprast_path)
            # Account for different filename lengths between years
            if len(snaprast_file) == 28:
                infile_path = '%s/%s/%s' % (naip_path, snaprast_file[2:7],
                                            snaprast_file)
            else:
                infile_path = '%s/%s/%s' % (naip_path, snaprast_file[3:8],
                                            snaprast_file[1:])
            arcpy.ProjectRaster_management(infile_path, snaprast_path, spatref)
        arcpy.env.snapRaster = snaprast_path

        arcpy.SelectLayerByAttribute_management(phyregs_layer,
                where_clause='PHYSIO_ID in (%s)' % ','.join(map(str,
                                            self.phyreg_ids)))
        with arcpy.da.SearchCursor(phyregs_layer, ['NAME', 'PHYSIO_ID']) as cur:
            for row in cur:
                name = row[0]
                print(name)
                # CreateRandomPoints cannot create a shapefile with - in its
                # filename
                name = name.replace(' ', '_').replace('-', '_')
                phyreg_id = row[1]
                outdir_path = '%s/%s/Inputs' % (results_path, name)
                if not os.path.exists(outdir_path):
                    if not os.path.exists(outdir_path[:-7]):
                        os.mkdir(outdir_path[:-7])
                    os.mkdir(outdir_path)
                outputs_path = '%s/%s/Outputs' % (results_path, name)
                if not os.path.exists(outputs_path):
                    os.mkdir(outputs_path)
                arcpy.SelectLayerByAttribute_management(naipqq_layer,
                        where_clause="%s like '%%,%d,%%'" % (
                            naipqq_phyregs_field, phyreg_id))
                with arcpy.da.SearchCursor(naipqq_layer, ['FileName']) as cur2:
                    for row2 in sorted(cur2):
                        filename = '%s.tif' % row2[0][:-13]
                        folder = filename[2:7]
                        infile_path = '%s/%s/%s' % (naip_path, folder, filename)
                        outfile_path = '%s/r%s' % (outdir_path, filename)
                        self.__check_snap(infile_path)
                        if not os.path.exists(outfile_path):
                            arcpy.ProjectRaster_management(infile_path,
                                    outfile_path, spatref)

        # clear selection
        arcpy.SelectLayerByAttribute_management(phyregs_layer,
                                                'CLEAR_SELECTION')
        arcpy.SelectLayerByAttribute_management(naipqq_layer,
                                                'CLEAR_SELECTION')

        print('Completed')

    @__timed
    def convert_afe_to_final_tiles(self):
        '''
        This function converts AFE outputs to final TIFF files.
        '''
        phyregs_layer = self.phyregs_layer
        naipqq_layer = self.naipqq_layer
        naipqq_phyregs_field = self.naipqq_phyregs_field
        results_path = self.results_path
        snaprast_path = self.snaprast_path

        arcpy.env.addOutputsToMap = False
        arcpy.env.snapRaster = snaprast_path

        arcpy.SelectLayerByAttribute_management(phyregs_layer,
                where_clause='PHYSIO_ID in (%s)' % ','.join(map(str,
                                                        self.phyreg_ids)))
        with arcpy.da.SearchCursor(phyregs_layer, ['NAME', 'PHYSIO_ID']) as cur:
            for row in cur:
                name = row[0]
                print(name)
                # CreateRandomPoints cannot create a shapefile with - in its
                # filename
                name = name.replace(' ', '_').replace('-', '_')
                phyreg_id = row[1]
                # Check and ensure that FA has classified all files.
                outdir_path = '%s/%s/Outputs' % (results_path, name)
                # Path for reprojected tiles
                inputs_path = '%s/%s/Inputs' % (results_path, name)

                if len(os.listdir(outdir_path)) == 0:
                    continue
                # File names for all reprojected inputs
                inputs_check = [os.path.basename(x) for x in
                                glob.glob(f"{inputs_path}/rm_*.tif")]
                # File names for all classified outputs
                output_class_check = [os.path.basename(x) for x in
                                      glob.glob(f"{outdir_path}/rm_*.tif")]
                # Check and get file names of those missing.
                missing = []
                for i in inputs_check:
                    if i not in output_class_check:
                        missing.append(i)
                # If any are missing then the length of each list will be
                # different. Raise I/O error and return missing file names.
                if len(inputs_check) != len(output_class_check):
                    # Format the same way FA specifies batch inputs.
                    missing_formated = " ".join(missing).replace(' ', '; ')
                    raise IOError(f"Missing classified file: {missing_formated}")
                arcpy.SelectLayerByAttribute_management(naipqq_layer,
                        where_clause="%s like '%%,%d,%%'" % (
                            naipqq_phyregs_field, phyreg_id))
                with arcpy.da.SearchCursor(naipqq_layer, ['FileName']) as cur2:
                    for row2 in sorted(cur2):
                        filename = row2[0][:-13]
                        rshpfile_path = '%s/r%s.shp' % (outdir_path, filename)
                        rtiffile_path = '%s/r%s.tif' % (outdir_path, filename)
                        frtiffile_path = '%s/fr%s.tif' % (outdir_path, filename)
                        if os.path.exists(frtiffile_path):
                            continue
                        if os.path.exists(rshpfile_path):
                            arcpy.FeatureToRaster_conversion(rshpfile_path,
                                    'CLASS_ID', frtiffile_path)
                            # Compare output tif cell size to snap raster
                            self.__check_snap(frtiffile_path)
                        elif os.path.exists(rtiffile_path):
                            # Compare input tif cell size to snap raster
                            self.__check_snap(rtiffile_path)
                            arcpy.Reclassify_3d(rtiffile_path, 'Value',
                                                '1 0;2 1', frtiffile_path)
        # clear selection
        arcpy.SelectLayerByAttribute_management(phyregs_layer,
                                                'CLEAR_SELECTION')
        arcpy.SelectLayerByAttribute_management(naipqq_layer,
                                                'CLEAR_SELECTION')

        print('Completed')

    @__timed
    def clip_final_tiles(self):
        '''
        This function clips final TIFF files.
        '''
        phyregs_layer = self.phyregs_layer
        naipqq_layer = self.naipqq_layer
        naipqq_phyregs_field = self.naipqq_phyregs_field
        results_path = self.results_path
        snaprast_path = self.snaprast_path

        # Get inmutiable ID's, does not need to be encoded.
        naipqq_oid_field = arcpy.Describe(naipqq_layer).OIDFieldName

        arcpy.env.addOutputsToMap = False
        arcpy.env.snapRaster = snaprast_path

        arcpy.SelectLayerByAttribute_management(phyregs_layer,
                where_clause='PHYSIO_ID in (%s)' % ','.join(map(str,
                                                        self.phyreg_ids)))
        with arcpy.da.SearchCursor(phyregs_layer, ['NAME', 'PHYSIO_ID']) as cur:
            for row in cur:
                name = row[0]
                print(name)
                # CreateRandomPoints cannot create a shapefile with - in its
                # filename
                name = name.replace(' ', '_').replace('-', '_')
                phyreg_id = row[1]
                outdir_path = '%s/%s/Outputs' % (results_path, name)
                if len(os.listdir(outdir_path)) == 0:
                    continue
                arcpy.SelectLayerByAttribute_management(naipqq_layer,
                        where_clause="%s like '%%,%d,%%'" % (
                            naipqq_phyregs_field, phyreg_id))
                with arcpy.da.SearchCursor(naipqq_layer,
                        [naipqq_oid_field, 'FileName']) as cur2:
                    for row2 in sorted(cur2):
                        oid = row2[0]
                        filename = row2[1][:-13]
                        frtiffile_path = '%s/fr%s.tif' % (
                            outdir_path, filename)
                        cfrtiffile_path = '%s/cfr%s.tif' % (
                            outdir_path, filename)
                        if os.path.exists(cfrtiffile_path):
                            continue
                        if os.path.exists(frtiffile_path):
                            arcpy.SelectLayerByAttribute_management(
                                    naipqq_layer,
                                    where_clause='%s=%d' % (
                                        naipqq_oid_field, oid))
                            out_raster = arcpy.sa.ExtractByMask(
                                frtiffile_path, naipqq_layer)
                            out_raster.save(cfrtiffile_path)
        # clear selection
        arcpy.SelectLayerByAttribute_management(phyregs_layer,
                                                'CLEAR_SELECTION')
        arcpy.SelectLayerByAttribute_management(naipqq_layer,
                                                'CLEAR_SELECTION')

        print('Completed')

    @__timed
    def mosaic_clipped_final_tiles(self):
        '''
        This function mosaics clipped final TIFF files and clips mosaicked files
        to physiographic regions.
        '''
        phyregs_layer = self.phyregs_layer
        naipqq_layer = self.naipqq_layer
        naipqq_phyregs_field = self.naipqq_phyregs_field
        analysis_year = self.analysis_year
        results_path = self.results_path
        snaprast_path = self.snaprast_path

        arcpy.env.addOutputsToMap = False
        arcpy.env.snapRaster = snaprast_path

        arcpy.SelectLayerByAttribute_management(phyregs_layer,
                where_clause='PHYSIO_ID in (%s)' % ','.join(map(str,
                                                        self.phyreg_ids)))
        with arcpy.da.SearchCursor(phyregs_layer, ['NAME', 'PHYSIO_ID']) as cur:
            for row in cur:
                name = row[0]
                print(name)
                # CreateRandomPoints cannot create a shapefile with - in its
                # filename
                name = name.replace(' ', '_').replace('-', '_')
                phyreg_id = row[1]
                outdir_path = '%s/%s/Outputs' % (results_path, name)
                if len(os.listdir(outdir_path)) == 0:
                    continue
                canopytif_path = '%s/canopy_%d_%s.tif' % (outdir_path,
                    analysis_year, name)
                if os.path.exists(canopytif_path):
                    continue
                mosaictif_filename = 'mosaic_%d_%s.tif' % (analysis_year, name)
                mosaictif_path = '%s/%s' % (outdir_path, mosaictif_filename)
                if not os.path.exists(mosaictif_path):
                    arcpy.SelectLayerByAttribute_management(naipqq_layer,
                            where_clause="%s like '%%,%d,%%'" % (
                                naipqq_phyregs_field, phyreg_id))
                    input_rasters = ''
                    with arcpy.da.SearchCursor(naipqq_layer,
                                               ['FileName']) as cur2:
                        for row2 in sorted(cur2):
                            filename = row2[0][:-13]
                            cfrtiffile_path = '%s/cfr%s.tif' % (outdir_path,
                                    filename)
                            if not os.path.exists(cfrtiffile_path):
                                input_rasters += ''
                            if input_rasters is not '':
                                input_rasters += ';'
                            if os.path.exists(cfrtiffile_path):
                                input_rasters += "'%s'" % cfrtiffile_path
                    if input_rasters == '':
                        continue
                    arcpy.MosaicToNewRaster_management(input_rasters,
                        outdir_path, mosaictif_filename, pixel_type='2_BIT',
                        number_of_bands=1)
                arcpy.SelectLayerByAttribute_management(phyregs_layer,
                        where_clause='PHYSIO_ID=%d' % phyreg_id)
                canopytif_raster = arcpy.sa.ExtractByMask(mosaictif_path,
                        phyregs_layer)
                canopytif_raster.save(canopytif_path)

        # clear selection
        arcpy.SelectLayerByAttribute_management(phyregs_layer,
                                                'CLEAR_SELECTION')
        arcpy.SelectLayerByAttribute_management(naipqq_layer,
                                                'CLEAR_SELECTION')

        print('Completed')

    @__timed
    def convert_afe_to_canopy_tif(self):
        '''
        This function is a wrapper function that converts AFE outputs to the
        final canopy TIFF file by invoking convert_afe_to_final_tiles(),
        clip_final_tiles(), and mosaic_clipped_final_tiles() in the correct
        order.
        '''

        self.convert_afe_to_final_tiles()
        self.clip_final_tiles()
        self.mosaic_clipped_final_tiles()

    @__timed
    def correct_inverted_canopy_tif(self, inverted_phyreg_ids):
        '''
        This function corrects the values of mosaikced and clipped regions that
        have been inverted with values canopy 0 and noncanopy 1, and changes
        them to canopy 1 and noncanopy 0.

        Parameters
        ----------
            inverted_phyreg_ids : list
                list of physiographic region IDs to process
        '''
        phyregs_layer = self.phyregs_layer
        analysis_year = self.analysis_year
        results_path = self.results_path
        snaprast_path = self.snaprast_path

        arcpy.env.addOutputsToMap = False
        arcpy.env.snapRaster = snaprast_path

        arcpy.SelectLayerByAttribute_management(phyregs_layer,
                where_clause='PHYSIO_ID in (%s)' % ','.join(
                    map(str, inverted_phyreg_ids)))
        with arcpy.da.SearchCursor(phyregs_layer, ['NAME', 'PHYSIO_ID']) as cur:
            for row in cur:
                name = row[0]
                print(name)
                name = name.replace(' ', '_').replace('-', '_')
                phyreg_id = row[1]
                outdir_path = '%s/%s/Outputs' % (results_path, name)
                if not os.path.exists(outdir_path):
                    continue
                canopytif_path = '%s/canopy_%d_%s.tif' % (outdir_path,
                        analysis_year, name)
                # name of corrected regions just add corrected_ as prefix
                corrected_path = '%s/corrected_canopy_%d_%s.tif' % (
                    outdir_path, analysis_year, name)
                if not os.path.exists(canopytif_path):
                    continue
                if os.path.exists(corrected_path):
                    continue
                if not os.path.exists(corrected_path):
                    # switch 1 and 0
                    corrected = 1 - arcpy.Raster(canopytif_path)
                    # copy raster is used as arcpy.save does not give bit
                    # options.
                    arcpy.CopyRaster_management(corrected, corrected_path,
                                                nodata_value = '3',
                                                pixel_type='2_BIT')

        # clear selection
        arcpy.SelectLayerByAttribute_management(phyregs_layer,
                                                'CLEAR_SELECTION')

        print('Completed')

    @__timed
    def convert_canopy_tif_to_shp(self):
        '''
        This function converts the canopy TIFF files to shapefile. If a region
        has been corrected for inverted values the function will convert the
        corrected TIFF to shapefile instead of the original canopy TIFF. If no
        corrected TIFF exists for a region then the original canopy TIFF will be
        converted.
        '''
        phyregs_layer = self.phyregs_layer
        analysis_year = self.analysis_year
        snaprast_path = self.snaprast_path
        results_path = self.results_path

        arcpy.env.addOutputsToMap = False
        arcpy.env.snapRaster = snaprast_path

        arcpy.SelectLayerByAttribute_management(phyregs_layer,
                where_clause='PHYSIO_ID in (%s)' % ','.join(
                    map(str, self.phyreg_ids)))
        with arcpy.da.SearchCursor(phyregs_layer, ['NAME', 'PHYSIO_ID']) as cur:
            for row in cur:
                name = row[0]
                print(name)
                name = name.replace(' ', '_').replace('-', '_')
                phyreg_id = row[1]
                outdir_path = '%s/%s/Outputs' % (results_path, name)
                if not os.path.exists(outdir_path):
                    continue
                canopytif_path = '%s/canopy_%d_%s.tif' % (outdir_path,
                                                          analysis_year, name)
                corrected_path = '%s/corrected_canopy_%d_%s.tif' % (
                    outdir_path, analysis_year, name)
                # Add shp_ as prefix to output shapefile
                canopyshp_path = '%s/shp_canopy_%d_%s.shp' % (
                    outdir_path, analysis_year, name)
                if os.path.exists(canopyshp_path):
                    continue
                if not os.path.exists(canopyshp_path):
                    # Check for corrected inverted TIFF first
                    if os.path.exists(corrected_path):
                        # Do not simplify polygons, keep cell extents
                        arcpy.RasterToPolygon_conversion(corrected_path,
                                canopyshp_path, 'NO_SIMPLIFY', 'Value')
                    # If no corrected inverted TIFF use orginial canopy TIFF
                    elif os.path.exists(canopytif_path):
                        # Do not simplify polygons, keep cell extents
                        arcpy.RasterToPolygon_conversion(canopytif_path,
                                canopyshp_path, 'NO_SIMPLIFY', 'Value')
                    # Add 'Canopy' field
                    arcpy.AddField_management(canopyshp_path, 'Canopy', 'SHORT',
                                              field_length='1')
                    # Calculate 'Canopy' field
                    arcpy.CalculateField_management(canopyshp_path, 'Canopy',
                                                    '!gridcode!')
                    # Remove Id and gridcode fields
                    arcpy.DeleteField_management(canopyshp_path, ['Id',
                                                                  'gridcode'])

        # clear selection
        arcpy.SelectLayerByAttribute_management(phyregs_layer,
                                                'CLEAR_SELECTION')

        print('Completed')

    def generate_gtpoints(self, phyreg_ids, min_area_sqkm, max_area_sqkm,
                          min_points, max_points):
        '''
        This function generates randomized points for ground truthing. It create
        the GT field in the output shapefile.

        Parameters
        ----------
        phyreg_ids : list
            list of physiographic region IDs to process
        min_area_sqkm : float
            miminum area in square kilometers
        max_area_sqkm : float
            maximum area in square kilometers
        min_points : int
            minimum number of points allowed
        max_points : int
            maximum number of points allowed
        '''
        # fix user errors, if any
        if min_area_sqkm > max_area_sqkm:
            tmp = min_area_sqkm
            min_area_sqkm = max_area_sqkm
            max_area_sqkm = tmp

        if min_points > max_points:
            tmp = min_points
            min_points = max_points
            max_points = tmp

        phyregs_layer = self.phyregs_layer
        phyregs_area_sqkm_field = self.phyregs_area_sqkm_field
        naipqq_layer = self.naipqq_layer
        spatref_wkid = self.spatref_wkid
        analysis_year = self.analysis_year
        results_path = self.results_path

        arcpy.env.overwriteOutput = True
        arcpy.env.addOutputsToMap = False
        arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(spatref_wkid)

        # use configparser converter to read list
        conf = ConfigParser(converters={'list': lambda x: [int(i.strip())
                                                    for i in x.split(',')]})
        conf.read(self.config)
        inverted_reg = conf.getlist('config', 'inverted_phyreg_ids')

        # make sure to clear selection because most geoprocessing tools use
        # selected features, if any
        arcpy.SelectLayerByAttribute_management(naipqq_layer, 'CLEAR_SELECTION')

        # select phyregs features to process
        arcpy.SelectLayerByAttribute_management(phyregs_layer,
                where_clause='PHYSIO_ID in (%s)' % ','.join(map(str,
                                                                phyreg_ids)))
        with arcpy.da.SearchCursor(phyregs_layer,
                ['NAME', 'PHYSIO_ID', phyregs_area_sqkm_field]) as cur:
            for row in cur:
                name = row[0]
                print(name)
                # CreateRandomPoints cannot create a shapefile with - in its
                # filename

                name = name.replace(' ', '_').replace('-', '_')
                phyreg_id = row[1]
                area_sqkm = row[2]

                # Check if region is inverted
                if row[1] in inverted_reg:
                    inverted = True
                else:
                    inverted = False

                # +1 to count partial points; e.g., 0.1 requires one point
                point_count = int(min_points + (max_points - min_points) /
                        (max_area_sqkm - min_area_sqkm) *
                        (area_sqkm - min_area_sqkm) + 1)
                print('Raw point count: %d' % point_count)
                if point_count < min_points:
                    point_count = min_points
                elif point_count > max_points:
                    point_count = max_points
                print('Final point count: %d' % point_count)

                outdir_path = '%s/%s/Outputs' % (results_path, name)
                shp_filename = 'gtpoints_%d_%s.shp' % (analysis_year, name)

                tmp_shp_filename = 'tmp_%s' % shp_filename
                tmp_shp_path = '%s/%s' % (outdir_path, tmp_shp_filename)

                # create random points
                arcpy.SelectLayerByAttribute_management(phyregs_layer,
                        where_clause='PHYSIO_ID=%d' % phyreg_id)
                arcpy.CreateRandomPoints_management(outdir_path,
                        tmp_shp_filename, phyregs_layer, '', point_count)

                # create a new field to store data for ground truthing
                gt_field = 'GT'
                arcpy.AddField_management(tmp_shp_path, gt_field, 'SHORT')

                # spatially join the naip qq layer to random points to find
                # output tile filenames
                shp_path = '%s/%s' % (outdir_path, shp_filename)
                arcpy.SpatialJoin_analysis(tmp_shp_path, naipqq_layer, shp_path)

                # delete temporary point shapefile
                arcpy.Delete_management(tmp_shp_path)

                # get required fields from spatially joined point layer
                with arcpy.da.UpdateCursor(shp_path, ['SHAPE@XY', gt_field,
                    'FileName']) as cur2:
                    for row2 in cur2:
                        # read filename
                        filename = row2[2][:-13]
                        # construct the final output tile path
                        cfrtiffile_path = '%s/cfr%s.tif' % (outdir_path,
                                                            filename)
                        # read the output tile as raster
                        ras = arcpy.sa.Raster(cfrtiffile_path)
                        # resolution
                        res = (ras.meanCellWidth, ras.meanCellHeight)
                        # convert raster to numpy array to read cell values
                        ras_a = arcpy.RasterToNumPyArray(ras)
                        # get xy values of point
                        xy = row2[0]
                        # perform calculate_row_column to get the row and column
                        # of the point
                        rc = self.__calculate_row_column(xy, ras.extent, res)
                        # update the point, correct inverted region points
                        if inverted is True:
                            row2[1] = 1 - ras_a[rc]
                            cur2.updateRow(row2)
                        else:
                            row2[1] = ras_a[rc]
                            cur.updateRow(row2)

                # delete all fields except only those required
                shp_desc = arcpy.Describe(shp_path)
                oid_field = shp_desc.OIDFieldName
                shape_field = shp_desc.shapeFieldName

                all_fields = arcpy.ListFields(shp_path)
                required_fields = [oid_field, shape_field, gt_field]
                extra_fields = [x.name for x in all_fields
                        if x.name not in required_fields]
                arcpy.DeleteField_management(shp_path, extra_fields)

        # clear selection again
        arcpy.SelectLayerByAttribute_management(phyregs_layer,
                                                'CLEAR_SELECTION')

        print('Completed')

    def update_gtpoints(self, old_points, phyreg_ids):
        '''
        This function copies a previous years GT points and copies the
        points but with the new years GT values. It addtionally corrects the
        values if they are within an inverted region.

        Parameters
        ----------
        old_points : str
            Layer name for the previous years points
        phyreg_ids : list
            list of physiographic region IDs to process
        '''
        phyregs_layer = self.phyregs_layer
        naipqq_layer = self.naipqq_layer
        spatref_wkid = self.spatref_wkid
        analysis_year = self.analysis_year
        results_path = self.results_path

        arcpy.env.overwriteOutput = True
        arcpy.env.addOutputsToMap = False
        arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(spatref_wkid)

        # use configparser converter to read list
        conf = ConfigParser(converters={'list': lambda x: [int(i.strip())
                                                    for i in x.split(',')]})
        conf.read(self.config)
        inverted_reg = conf.getlist('config', 'inverted_phyreg_ids')

        # make sure to clear selection because most geoprocessing tools use
        # selected features, if any
        arcpy.SelectLayerByAttribute_management(naipqq_layer, 'CLEAR_SELECTION')

        # select phyregs features to process
        arcpy.SelectLayerByAttribute_management(phyregs_layer,
            where_clause='PHYSIO_ID in (%s)' % ','.join(map(str,
                phyreg_ids)))
        with arcpy.da.SearchCursor(phyregs_layer,
                ['NAME', 'PHYSIO_ID']) as cur:
            for row in cur:
                name = row[0]
                print(name)
                # CreateRandomPoints cannot create a shapefile with - in its
                # filename
                name = name.replace(' ', '_').replace('-', '_')
                phyreg_id = row[1]
                # Check if region is inverted
                if row[1] in inverted_reg:
                    inverted = True
                else:
                    inverted = False

                outdir_path = '%s/%s/Outputs' % (results_path, name)
                shp_filename = 'gtpoints_%d_%s.shp' % (analysis_year, name)

                tmp_shp_filename = 'tmp_%s' % shp_filename
                tmp_shp_path = '%s/%s' % (outdir_path, tmp_shp_filename)

                # create random points
                arcpy.SelectLayerByAttribute_management(phyregs_layer,
                        where_clause='PHYSIO_ID=%d' % phyreg_id)

                # create a new field to store data for ground truthing
                gt_field = 'GT_%s' % analysis_year
                arcpy.CopyFeatures_management(old_points, tmp_shp_path)
                arcpy.AddField_management(tmp_shp_path, gt_field, 'SHORT')

                # spatially join the naip qq layer to random points to find
                # output tile filenames
                shp_path = '%s/%s' % (outdir_path, shp_filename)
                arcpy.SpatialJoin_analysis(tmp_shp_path, naipqq_layer, shp_path)

                # delete temporary point shapefile
                arcpy.Delete_management(tmp_shp_path)

                # get required fields from spatially joined point layer
                with arcpy.da.UpdateCursor(shp_path, ['SHAPE@XY', gt_field,
                                                      'FileName']) as cur2:
                    for row2 in cur2:
                        # read filename
                        filename = row2[2][:-13]
                        # construct the final output tile path
                        cfrtiffile_path = '%s/cfr%s.tif' % (outdir_path,
                                                            filename)
                        # read the output tile as raster
                        ras = arcpy.sa.Raster(cfrtiffile_path)
                        # resolution
                        res = (ras.meanCellWidth, ras.meanCellHeight)
                        # convert raster to numpy array to read cell values
                        ras_a = arcpy.RasterToNumPyArray(ras)
                        # get xy values of point
                        xy = row2[0]
                        # perform calculate_row_column to get the row and column
                        # of the point
                        rc = self.__calculate_row_column(xy, ras.extent, res)
                        # update the point, correct inverted region points
                        if inverted is True:
                            row2[1] = 1 - ras_a[rc]
                            cur2.updateRow(row2)
                        else:
                            row2[1] = ras_a[rc]
                            cur2.updateRow(row2)

                # delete all fields except only those required
                shp_desc = arcpy.Describe(shp_path)
                oid_field = shp_desc.OIDFieldName
                shape_field = shp_desc.shapeFieldName

                all_fields = arcpy.ListFields(shp_path)
                required_fields = [oid_field, shape_field, gt_field]
                extra_fields = [x.name for x in all_fields
                                if x.name not in required_fields]
                arcpy.DeleteField_management(shp_path, extra_fields)

        # clear selection again
        arcpy.SelectLayerByAttribute_management(phyregs_layer,
                                                'CLEAR_SELECTION')

        print('Completed')

    def add_naip_tiles_for_gt(self, gtpoints):
        '''
        This function adds NAIP imagery where a ground truthing point is located
        into an arcgis project. Imagery is saved as a temporary layer.
        Functional in both ArcMap & ArcGIS Pro.

        Parameters
        ----------
        gtpoints : str
            name of ground truthing points shapefile to add NAIP based off
        '''
        naipqq_layer = self.naipqq_layer
        naip_path = self.naip_path

        arcpy.SelectLayerByAttribute_management(naipqq_layer,
                                                'CLEAR_SELECTION')
        arcpy.SelectLayerByLocation_management(naipqq_layer,
                                               'INTERSECT', gtpoints)

        with arcpy.da.SearchCursor(naipqq_layer, ['FileName']) as cur:
            for row in sorted(cur):
                filename = '%s.tif' % row[0][:-13]
                folder = filename[2:7]
                infile_path = '%s/%s/%s' % (naip_path, folder, filename)
                tmp = 'in_memory/%s' % filename
                arcpy.MakeRasterLayer_management(infile_path, tmp)

        arcpy.SelectLayerByAttribute_management(naipqq_layer, 'CLEAR_SELECTION')

        print('Completed')


class Check_gaps:
    '''
    Object to check if gaps within in raster array are present.
    '''
    def __init__(self, arc_raster, nodata=3):
        self.region_array = arcpy.RasterToNumPyArray(arc_raster,
                                                     nodata_to_value=nodata)
        self.nodata = nodata
        self.check(self.region_array)

    def __neighbors(self, arr, i, j, d=1):
        # Neighbors function adapted from ocsmit/mwinpy.git
        neighbors = arr[max(i - d, 0):min(i + d + 1, arr.shape[0]),
            max(j - d, 0):min(j + d + 1, arr.shape[1])].flatten()
        return neighbors

    def check(self, arr):
        # Get array i,j indices only where the value is equal to nodata.
        index_i, index_j = np.where(arr >= self.nodata)
        for i in range(len(index_i)):
            # Get 8 neighbors of cell
            n = self.__neighbors(arr, index_i[i], index_j[i])
            # Get count of values in cell
            u, c = np.unique(n, return_counts=True)
            val_dict = dict(zip(u, c))
            # If number of nodata cells is less than or equal to 2, then it
            # is a gap in the mosaic. Here, we assume single-cell-wide gaps
            # only. For example, see
            #   XXXXXX    XXXXXX    XXXXXX
            #   X....X or X..X.X or X.X..X
            #   XXXXXX    XXXXXX    X.XX.X
            #                       XXXXXX
            # where X and . are non-nodata and nodata cells, respectively.
            # These nodata cells (....) are a nodata gap within non-nodata
            # cells. However, in the following case,
            #   ......
            #   ....XX
            #   ..XXXX
            # the nodata cells are just outside the region boundary. Depending
            # on their locations, this check will fail to flag wider gaps such
            # as the following cases though:
            #   XXXXXX    XXXXXX
            #   X....X or X.X..X
            #   XX...X    X..X.X
            #   XXXXXX    XXXXXX
            #   6 right   2 middle nodata cells unflagged
            if val_dict.get(self.nodata) <= 2:
                print("Gaps are present in mosaic")
                break
