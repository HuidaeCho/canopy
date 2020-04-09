################################################################################
# Name:    canopy.py
# Purpose: This module provides utility functions for preprocessing NAIP tiles
#          and postprocessing trained canopy tiles.
# Authors: Huidae Cho, Ph.D., Owen Smith, IESA, University of North Georgia
# Since:   November 29, 2019
# Grant:   Sponsored by the Georgia Forestry Commission through the Georgia
#          Statewide Canopy Assessment Phase I: Canopy Analysis 2009 project
################################################################################

import arcpy
import os
import canopy_config

def assign_phyregs_to_naipqq():
    '''
    This function adds the phyregs field to the NAIP QQ shapefile and populates
    it with physiographic region IDs that intersect each NAIP tile. This
    function needs to be run only once, but running it multiple times would not
    hurt either other than wasting computational resources.
    '''
    phyregs_layer = canopy_config.phyregs_layer
    phyregs_area_sqkm_field = canopy_config.phyregs_area_sqkm_field
    naipqq_layer = canopy_config.naipqq_layer
    naipqq_phyregs_field = canopy_config.naipqq_phyregs_field

    # calculate phyregs_area_sqkm_field
    fields = arcpy.ListFields(phyregs_layer, phyregs_area_sqkm_field)
    for field in fields:
        if field.name == phyregs_area_sqkm_field:
            arcpy.DeleteField_management(phyregs_layer, phyregs_area_sqkm_field)
            break
    arcpy.AddField_management(phyregs_layer, phyregs_area_sqkm_field, 'DOUBLE')
    arcpy.management.CalculateGeometryAttributes(phyregs_layer,
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
    arcpy.SelectLayerByAttribute_management(phyregs_layer, 'CLEAR_SELECTION')
    arcpy.SelectLayerByAttribute_management(naipqq_layer, 'CLEAR_SELECTION')

    # initialize the phyregs field to ,
    arcpy.CalculateField_management(naipqq_layer, naipqq_phyregs_field, '","')

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
            arcpy.CalculateField_management(naipqq_layer, naipqq_phyregs_field,
                    '!%s!+"%d,"' % (naipqq_phyregs_field, phyreg_id),
                    'PYTHON_9.3')

    # clear selection again
    arcpy.SelectLayerByAttribute_management(phyregs_layer, 'CLEAR_SELECTION')
    arcpy.SelectLayerByAttribute_management(naipqq_layer, 'CLEAR_SELECTION')

    print('Completed')

def reproject_input_tiles(phyreg_ids):
    '''
    This function reprojects and snaps the NAIP tiles that intersect selected
    physiographic regions.

    phyreg_ids: list of physiographic region IDs to process
    '''
    phyregs_layer = canopy_config.phyregs_layer
    naipqq_layer = canopy_config.naipqq_layer
    naipqq_phyregs_field = canopy_config.naipqq_phyregs_field
    spatref_wkid = canopy_config.spatref_wkid
    snaprast_path = canopy_config.snaprast_path
    naip_path = canopy_config.naip_path
    results_path = canopy_config.results_path

    spatref = arcpy.SpatialReference(spatref_wkid)

    arcpy.env.addOutputsToMap = False
    if not os.path.exists(snaprast_path):
        snaprast_file = os.path.basename(snaprast_path)
        infile_path = '%s/%s/%s' % (naip_path, snaprast_file[3:8],
                snaprast_file[1:])
        arcpy.ProjectRaster_management(infile_path, snaprast_path, spatref)
    arcpy.env.snapRaster = snaprast_path

    arcpy.SelectLayerByAttribute_management(phyregs_layer,
            where_clause='PHYSIO_ID in (%s)' % ','.join(map(str, phyreg_ids)))
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
            arcpy.SelectLayerByAttribute_management(naipqq_layer,
                    where_clause="%s like '%%,%d,%%'" % (naipqq_phyregs_field,
                        phyreg_id))
            with arcpy.da.SearchCursor(naipqq_layer, ['FileName']) as cur2:
                for row2 in sorted(cur2):
                    filename = '%s.tif' % row2[0][:-13]
                    folder = filename[2:7]
                    infile_path = '%s/%s/%s' % (naip_path, folder, filename)
                    outfile_path = '%s/r%s' % (outdir_path, filename)
                    if not os.path.exists(outfile_path):
                        arcpy.ProjectRaster_management(infile_path,
                                outfile_path, spatref)

    # clear selection
    arcpy.SelectLayerByAttribute_management(phyregs_layer, 'CLEAR_SELECTION')
    arcpy.SelectLayerByAttribute_management(naipqq_layer, 'CLEAR_SELECTION')

    print('Completed')


def convert_afe_to_final_tiles(phyreg_ids):
    '''
    This function converts AFE outputs to final TIFF files.

    phyreg_ids: list of physiographic region IDs to process
    '''
    phyregs_layer = canopy_config.phyregs_layer
    naipqq_layer = canopy_config.naipqq_layer
    naipqq_phyregs_field = canopy_config.naipqq_phyregs_field
    snaprast_path = canopy_config.snaprast_path
    results_path = canopy_config.results_path

    arcpy.env.addOutputsToMap = False
    arcpy.env.snapRaster = snaprast_path

    arcpy.SelectLayerByAttribute_management(phyregs_layer,
            where_clause='PHYSIO_ID in (%s)' % ','.join(map(str, phyreg_ids)))
    with arcpy.da.SearchCursor(phyregs_layer, ['NAME', 'PHYSIO_ID']) as cur:
        for row in cur:
            name = row[0]
            print(name)
            # CreateRandomPoints cannot create a shapefile with - in its
            # filename
            name = name.replace(' ', '_').replace('-', '_')
            phyreg_id = row[1]
            outdir_path = '%s/%s/Outputs' % (results_path, name)
            if not os.path.exists(outdir_path):
                continue
            arcpy.SelectLayerByAttribute_management(naipqq_layer,
                    where_clause="%s like '%%,%d,%%'" % (naipqq_phyregs_field,
                        phyreg_id))
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
                                'CLASS_ID', frtiffile_path, 1)
                    elif os.path.exists(rtiffile_path):
                        arcpy.Reclassify_3d(rtiffile_path, 'Value', '1 0;2 1',
                                frtiffile_path)

    # clear selection
    arcpy.SelectLayerByAttribute_management(phyregs_layer, 'CLEAR_SELECTION')
    arcpy.SelectLayerByAttribute_management(naipqq_layer, 'CLEAR_SELECTION')

    print('Completed')

def convert_2bit(phyreg_ids):
    phyregs_layer = canopy_config.phyregs_layer
    naipqq_layer = canopy_config.naipqq_layer
    naipqq_phyregs_field = canopy_config.naipqq_phyregs_field
    snaprast_path = canopy_config.snaprast_path
    results_path = canopy_config.results_path

    naipqq_oid_field = arcpy.Describe(naipqq_layer).OIDFieldName.encode()

    arcpy.env.addOutputsToMap = False
    arcpy.env.snapRaster = snaprast_path

    arcpy.SelectLayerByAttribute_management(phyregs_layer,
            where_clause='PHYSIO_ID in (%s)' % ','.join(map(str, phyreg_ids)))
    with arcpy.da.SearchCursor(phyregs_layer, ['NAME', 'PHYSIO_ID']) as cur:
        for row in cur:
            name = row[0]
            print(name)
            # CreateRandomPoints cannot create a shapefile with - in its
            # filename
            name = name.replace(' ', '_').replace('-', '_')
            phyreg_id = row[1]
            outdir_path = '%s/%s/Outputs' % (results_path, name)
            if not os.path.exists(outdir_path):
                continue
            arcpy.SelectLayerByAttribute_management(naipqq_layer,
                    where_clause="%s like '%%,%d,%%'" % (naipqq_phyregs_field,
                        phyreg_id))
            with arcpy.da.SearchCursor(naipqq_layer,
                    [naipqq_oid_field, 'FileName']) as cur2:
                for row2 in sorted(cur2):
                    oid = row2[0]
                    filename = row2[1][:-13]
                    frtiffile_path = '%s/fr%s.tif' % (outdir_path, filename)
                    cfrtiffile_path = '%s/cfr%s.tif' % (outdir_path, filename)
                    if os.path.exists(cfrtiffile_path):
                        continue
                    if os.path.exists(frtiffile_path):
                        arcpy.SelectLayerByAttribute_management(naipqq_layer,
                                where_clause='%s=%d' % (naipqq_oid_field, oid))
                        arcpy.gp.ExtractByMask_sa(frtiffile_path, naipqq_layer,
                                cfrtiffile_path)

    # clear selection
    arcpy.SelectLayerByAttribute_management(phyregs_layer, 'CLEAR_SELECTION')
    arcpy.SelectLayerByAttribute_management(naipqq_layer, 'CLEAR_SELECTION')

    print('Completed')

def clip_final_tiles(phyreg_ids):
    '''
    This function clips final TIFF files.

    phyreg_ids: list of physiographic region IDs to process
    '''
    phyregs_layer = canopy_config.phyregs_layer
    naipqq_layer = canopy_config.naipqq_layer
    naipqq_phyregs_field = canopy_config.naipqq_phyregs_field
    snaprast_path = canopy_config.snaprast_path
    results_path = canopy_config.results_path

    naipqq_oid_field = arcpy.Describe(naipqq_layer).OIDFieldName.encode()

    arcpy.env.addOutputsToMap = False
    arcpy.env.snapRaster = snaprast_path

    arcpy.SelectLayerByAttribute_management(phyregs_layer,
            where_clause='PHYSIO_ID in (%s)' % ','.join(map(str, phyreg_ids)))
    with arcpy.da.SearchCursor(phyregs_layer, ['NAME', 'PHYSIO_ID']) as cur:
        for row in cur:
            name = row[0]
            print(name)
            # CreateRandomPoints cannot create a shapefile with - in its
            # filename
            name = name.replace(' ', '_').replace('-', '_')
            phyreg_id = row[1]
            outdir_path = '%s/%s/Outputs' % (results_path, name)
            if not os.path.exists(outdir_path):
                continue
            arcpy.SelectLayerByAttribute_management(naipqq_layer,
                    where_clause="%s like '%%,%d,%%'" % (naipqq_phyregs_field,
                        phyreg_id))
            with arcpy.da.SearchCursor(naipqq_layer,
                    [naipqq_oid_field, 'FileName']) as cur2:
                for row2 in sorted(cur2):
                    oid = row2[0]
                    filename = row2[1][:-13]
                    frtiffile_path = '%s/fr%s.tif' % (outdir_path, filename)
                    cfrtiffile_path = '%s/cfr%s.tif' % (outdir_path, filename)
                    if os.path.exists(cfrtiffile_path):
                        continue
                    if os.path.exists(frtiffile_path):
                        arcpy.SelectLayerByAttribute_management(naipqq_layer,
                                where_clause='%s=%d' % (naipqq_oid_field, oid))
                        arcpy.gp.ExtractByMask_sa(frtiffile_path, naipqq_layer,
                                cfrtiffile_path)

    # clear selection
    arcpy.SelectLayerByAttribute_management(phyregs_layer, 'CLEAR_SELECTION')
    arcpy.SelectLayerByAttribute_management(naipqq_layer, 'CLEAR_SELECTION')

    print('Completed')

def mosaic_clipped_final_tiles(phyreg_ids):
    '''
    This function mosaics clipped final TIFF files and clips mosaicked files to
    physiographic regions.

    phyreg_ids: list of physiographic region IDs to process
    '''
    phyregs_layer = canopy_config.phyregs_layer
    naipqq_layer = canopy_config.naipqq_layer
    naipqq_phyregs_field = canopy_config.naipqq_phyregs_field
    analysis_year = canopy_config.analysis_year
    snaprast_path = canopy_config.snaprast_path
    results_path = canopy_config.results_path

    arcpy.env.addOutputsToMap = False
    arcpy.env.snapRaster = snaprast_path

    arcpy.SelectLayerByAttribute_management(phyregs_layer,
            where_clause='PHYSIO_ID in (%s)' % ','.join(map(str, phyreg_ids)))
    with arcpy.da.SearchCursor(phyregs_layer, ['NAME', 'PHYSIO_ID']) as cur:
        for row in cur:
            name = row[0]
            print(name)
            # CreateRandomPoints cannot create a shapefile with - in its
            # filename
            name = name.replace(' ', '_').replace('-', '_')
            phyreg_id = row[1]
            outdir_path = '%s/%s/Outputs' % (results_path, name)
            if not os.path.exists(outdir_path):
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
                with arcpy.da.SearchCursor(naipqq_layer, ['FileName']) as cur2:
                    for row2 in sorted(cur2):
                        filename = row2[0][:-13]
                        cfrtiffile_path = '%s/cfr%s.tif' % (outdir_path,
                                filename)
                        if not os.path.exists(cfrtiffile_path):
                            input_rasters = ''
                            break
                        if input_rasters is not '':
                            input_rasters += ';'
                        input_rasters += "'%s'" % cfrtiffile_path
                if input_rasters == '':
                    continue
                arcpy.MosaicToNewRaster_management(input_rasters, outdir_path,
                        mosaictif_filename, pixel_type='2_BIT',
                        number_of_bands=1)
            arcpy.SelectLayerByAttribute_management(phyregs_layer,
                    where_clause='PHYSIO_ID=%d' % phyreg_id)
            arcpy.gp.ExtractByMask_sa(mosaictif_path, phyregs_layer,
                    canopytif_path)

    # clear selection
    arcpy.SelectLayerByAttribute_management(phyregs_layer, 'CLEAR_SELECTION')
    arcpy.SelectLayerByAttribute_management(naipqq_layer, 'CLEAR_SELECTION')

    print('Completed')

def convert_afe_to_canopy_tiff(phyreg_ids):
    '''
    This function is a wrapper function that converts AFE outputs to the final
    canopy TIFF file by invoking convert_afe_to_final_tiles(),
    clip_final_tiles(), and mosaic_clipped_final_tiles() in the correct order.

    phyreg_ids: list of physiographic region IDs to process
    '''
    convert_afe_to_final_tiles(phyreg_ids)
    clip_final_tiles(phyreg_ids)
    mosaic_clipped_final_tiles(phyreg_ids)

def correct_inverted_canopy_tiff(inverted_phyreg_ids):
    '''
    This function corrects the values of mosaikced and clipped regions that
    have been inverted with values canopy 0 and noncanopy 1, and changes them
    to canopy 1 and noncanopy 0.

    inverted_phyreg_ids: list of physiographic region IDs to process
    '''
    phyregs_layer = canopy_config.phyregs_layer
    analysis_year = canopy_config.analysis_year
    snaprast_path = canopy_config.snaprast_path
    results_path = canopy_config.results_path

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
                # copy raster is used as arcpy.save does not give bit options.
                arcpy.CopyRaster_management(corrected, corrected_path,
                        pixel_type='2_BIT')

    # clear selection
    arcpy.SelectLayerByAttribute_management(phyregs_layer, 'CLEAR_SELECTION')

    print('Completed')

def calculate_row_column(xy, rast_ext, rast_res):
    '''
    This function calculates array row and column using x, y, extent, and
    resolution.

    xy:       (x, y) coordinates
    rast_ext: raster extent
    rast_res: (width, height) raster resolution
    '''
    x = xy[0]
    y = xy[1]
    w = rast_res[0]
    h = rast_res[1]
    row = int((rast_ext.YMax - y) / h)
    col = int((x - rast_ext.XMin) / w)
    return row, col

def generate_ground_truthing_points(phyreg_ids, point_density, max_points=400,
        min_points=200):
    '''
    This function generates randomized points for ground truthing. It create
    the GT field in the output shapefile.

    phyreg_ids:     list of physiographic region IDs to process
    point_density:  number of points per square kilometer
    max_points:     maximum number of points allowed
    min_points:     minimum number of points allowed
    '''
    # fix a user error, if any
    if min_points > max_points:
        tmp = min_points
        min_points = max_points
        max_points = tmp

    phyregs_layer = canopy_config.phyregs_layer
    phyregs_area_sqkm_field = canopy_config.phyregs_area_sqkm_field
    naipqq_layer = canopy_config.naipqq_layer
    spatref_wkid = canopy_config.spatref_wkid
    analysis_year = canopy_config.analysis_year
    results_path = canopy_config.results_path

    arcpy.env.overwriteOutput = True
    arcpy.env.addOutputsToMap = False
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(spatref_wkid)

    # make sure to clear selection because most geoprocessing tools use
    # selected features, if any
    arcpy.SelectLayerByAttribute_management(naipqq_layer, 'CLEAR_SELECTION')

    # select phyregs features to process
    arcpy.SelectLayerByAttribute_management(phyregs_layer,
            where_clause='PHYSIO_ID in (%s)' % ','.join(map(str, phyreg_ids)))
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

            # +1 to count partial points; e.g., 0.1 requires one point
            point_count = int(point_density * area_sqkm + 1)
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
            arcpy.CreateRandomPoints_management(outdir_path, tmp_shp_filename,
                    phyregs_layer, '', point_count)

            # create a new field to store data for ground thruthing
            gt_field = 'GT'
            arcpy.AddField_management(tmp_shp_path, gt_field, 'SHORT')

            # spatially join the naip qq layer to random points to find output
            # tile filenames
            shp_path = '%s/%s' % (outdir_path, shp_filename)
            arcpy.analysis.SpatialJoin(tmp_shp_path, naipqq_layer, shp_path)

            # delete temporary point shapefile
            arcpy.Delete_management(tmp_shp_path)

            # get required fields from spatially joined point layer
            with arcpy.da.UpdateCursor(shp_path, ['SHAPE@XY', gt_field,
                'FileName']) as cur2:
                for row2 in cur2:
                    # read filename
                    filename = row2[2][:-13]
                    # construct the final output tile path
                    cfrtiffile_path = '%s/cfr%s.tif' % (outdir_path, filename)
                    # read the output tile as raster
                    ras = arcpy.sa.Raster(cfrtiffile_path)
                    # resolution
                    res = (ras.meanCellWidth, ras.meanCellHeight)
                    # convert raster to numpy array to read cell values
                    ras_a = arcpy.RasterToNumPyArray(ras)
                    # get xy values of point
                    xy = row2[0]
                    # perform calculate_row_column to get the row and column of
                    # the point
                    rc = calculate_row_column(xy, ras.extent, res)
                    # update the point
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
    arcpy.SelectLayerByAttribute_management(phyregs_layer, 'CLEAR_SELECTION')

    print('Completed')

def add_naip(gt_point):
    '''
    This function adds naip imagery where a groundtruthing point is located
    into an arcgis project. Imagery is saved as a temporary layer. Functional
    in both ArcMap & ArcGIS Pro.

    Parameters:
    gt_point: name of ground truhting point shapefile to add naip based off of
    '''
    naipqq_layer = canopy_config.naipqq_layer
    naip_path = canopy_config.naip_path

    arcpy.SelectLayerByAttribute_management(naipqq_layer, 'CLEAR_SELECTION')
    arcpy.SelectLayerByLocation_management(naipqq_layer, 'INTERSECT', gt_point)

    with arcpy.da.SearchCursor(naipqq_layer, ['FileName']) as cur:
        for row in sorted(cur):
            filename = '%s.tif' % row[0][:-13]
            folder = filename[2:7]
            infile_path = '%s/%s/%s' % (naip_path, folder, filename)
            tmp = 'in_memory/%s' % filename
            arcpy.MakeRasterLayer_management(infile_path, tmp)

    arcpy.SelectLayerByAttribute_management(naipqq_layer, 'CLEAR_SELECTION')

    print('Completed')

def canopy_tif_to_shp(phyreg_id):

    phyregs_layer = canopy_config.phyregs_layer
    analysis_year = canopy_config.analysis_year
    snaprast_path = canopy_config.snaprast_path
    results_path = canopy_config.results_path

    arcpy.env.addOutputsToMap = False
    arcpy.env.snapRaster = snaprast_path

    arcpy.SelectLayerByAttribute_management(phyregs_layer,
                                            where_clause='PHYSIO_ID in (%s)' % ','.join(
                                                map(str, phyreg_id)))
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
            canopyshp_path = '%s/shp_canopy_%d_%s.shp' % (
                outdir_path, analysis_year, name)
            if not os.path.exists(canopytif_path):
                continue
            if os.path.exists(canopyshp_path):
                continue
            if not os.path.exists(canopyshp_path):
                # switch 1 and 0
                arcpy.RasterToPolygon(canopytif_path, canopyshp_path, 'NO_SIMPLIFY')
                # copy raster is used as arcpy.save does not give bit options.
                # arcpy.CopyRaster_management(corrected, corrected_path,
                #                             pixel_type='2_BIT')

    # clear selection
    arcpy.SelectLayerByAttribute_management(phyregs_layer, 'CLEAR_SELECTION')

    print('Completed')