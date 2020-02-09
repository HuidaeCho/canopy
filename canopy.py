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
    naipqq_layer = canopy_config.naipqq_layer
    naipqq_phyregs_field = canopy_config.naipqq_phyregs_field

    fields = arcpy.ListFields(naipqq_layer, naipqq_phyregs_field)
    for field in fields:
        if field.name == naipqq_phyregs_field:
            arcpy.DeleteField_management(naipqq_layer, naipqq_phyregs_field)
            break
    arcpy.AddField_management(naipqq_layer, naipqq_phyregs_field, 'TEXT',
            field_length=100)

    sorted_phyregs = []
    arcpy.SelectLayerByAttribute_management(phyregs_layer, 'CLEAR_SELECTION')
    arcpy.SelectLayerByAttribute_management(naipqq_layer, 'CLEAR_SELECTION')
    arcpy.CalculateField_management(naipqq_layer, naipqq_phyregs_field, '","')
    with arcpy.da.SearchCursor(phyregs_layer,
            ['AREA', 'NAME', 'PHYSIO_ID']) as cur:
        for row in sorted(cur):
            area = row[0]
            name = row[1]
            print(name)
            phyreg_id = row[2]
            sorted_phyregs.append({
                'name': name,
                'phyreg_id': phyreg_id,
                'area': area})
            arcpy.SelectLayerByAttribute_management(phyregs_layer,
                    where_clause='PHYSIO_ID=%d' % phyreg_id)
            arcpy.SelectLayerByLocation_management(naipqq_layer,
                    select_features=phyregs_layer)
            arcpy.CalculateField_management(naipqq_layer, naipqq_phyregs_field,
                    '!%s!+"%d,"' % (naipqq_phyregs_field, phyreg_id),
                    'PYTHON_9.3')
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
            name = name.replace(' ', '_')
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
            name = name.replace(' ', '_')
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

    naipqq_oidfield = arcpy.Describe(naipqq_layer).OIDFieldName.encode()

    arcpy.env.addOutputsToMap = False
    arcpy.env.snapRaster = snaprast_path

    arcpy.SelectLayerByAttribute_management(phyregs_layer,
            where_clause='PHYSIO_ID in (%s)' % ','.join(map(str, phyreg_ids)))
    with arcpy.da.SearchCursor(phyregs_layer, ['NAME', 'PHYSIO_ID']) as cur:
        for row in cur:
            name = row[0]
            print(name)
            name = name.replace(' ', '_')
            phyreg_id = row[1]
            outdir_path = '%s/%s/Outputs' % (results_path, name)
            if not os.path.exists(outdir_path):
                continue
            arcpy.SelectLayerByAttribute_management(naipqq_layer,
                    where_clause="%s like '%%,%d,%%'" % (naipqq_phyregs_field,
                        phyreg_id))
            with arcpy.da.SearchCursor(naipqq_layer,
                    [naipqq_oidfield, 'FileName']) as cur2:
                for row2 in sorted(cur2):
                    oid = row2[0]
                    filename = row2[1][:-13]
                    frtiffile_path = '%s/fr%s.tif' % (outdir_path, filename)
                    cfrtiffile_path = '%s/cfr%s.tif' % (outdir_path, filename)
                    if os.path.exists(cfrtiffile_path):
                        continue
                    if os.path.exists(frtiffile_path):
                        arcpy.SelectLayerByAttribute_management(naipqq_layer,
                                where_clause='%s=%d' % (naipqq_oidfield, oid))
                        arcpy.gp.ExtractByMask_sa(frtiffile_path, naipqq_layer,
                                cfrtiffile_path)
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
            name = name.replace(' ', '_')
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

def generate_ground_truthing_points(phyreg_ids,
                                    point_density=0.25,
                                    max_points=400, min_points=0):
    '''
    This function generates randomized points for ground truthing.
    Can only take one phyreg_id at a time currently.

    phyreg_ids:     list of physiographic region IDs to process
    point_density:  number of points per square kilometer
    max_points:     maximum number of points allowed
    min_points:     minimum number of points allowed
    '''
    phyregs_layer = canopy_config.phyregs_layer
    naipqq_layer = canopy_config.naipqq_layer
    spatref_wkid = canopy_config.spatref_wkid
    gt_output_folder = canopy_config.ground_truth
    analysis_year = canopy_config.analysis_year
    results_path = canopy_config.results_path

    arcpy.env.addOutputsToMap = False
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(spatref_wkid)

    if not os.path.join(gt_output_folder):
        os.mkdir(gt_output_folder)

    if not len(arcpy.ListFields(phyregs_layer, 'AREA_SQKM')) > 0:
        arcpy.AddField_management(phyregs_layer, 'AREA_SQKM', 'DOUBLE')
        arcpy.management.CalculateGeometryAttributes(
            phyregs_layer, [['AREA_SQKM', 'AREA']], '', 'SQUARE_KILOMETERS',
            spatref_wkid)

    def get_array_indices(xy, ext, res):
        '''
        Get array indices using x, y, extent, and resolution
        xy:  (x, y) indices
        ext: raster extent
        res: (width, height) raster resolution
        '''
        x = xy[0]
        y = xy[1]
        w = res[0]
        h = res[1]
        row = int((ext.YMax - y) / h)
        col = int((x - ext.XMin) / w)
        return row, col

    arcpy.SelectLayerByAttribute_management(phyregs_layer,
            where_clause='PHYSIO_ID in (%s)' % ','.join(map(str, phyreg_ids)))
    with arcpy.da.SearchCursor(phyregs_layer, ['NAME', 'PHYSIO_ID',
                                               'AREA_SQKM']) \
            as cur:
        for row in cur:
            name = row[0]
            print(name)
            name = name.replace(' ', '_')
            phyreg_id = row[1]
            if not os.path.exists(gt_output_folder):
                os.mkdir(gt_output_folder)
            shp_filename = 'gtpoints_%s.shp' % name
            shp_path = '%s/%s' % (gt_output_folder, shp_filename)
            arcpy.SelectLayerByAttribute_management(phyregs_layer,
                    where_clause='PHYSIO_ID=%d' % phyreg_id)
            metersPerUnit = arcpy.Describe(
                phyregs_layer).spatialReference.metersPerUnit
            point_density *= metersPerUnit**2
            area = row[2]
            point_count = float(point_density * area)
            print('Point Count: ', str(point_count))
            if point_count < min_points:
                del point_count
                point_count = min_points
            if point_count > max_points:
                del point_count
                point_count = max_points
            arcpy.CreateRandomPoints_management(gt_output_folder, shp_filename,
                    phyregs_layer, '', point_count)
            field = 'GT_%s' % str(analysis_year)
            if not len(arcpy.ListFields(shp_path, field)) > 0:
                arcpy.AddField_management(shp_path, field, 'SHORT')
            region_out = '%s/Outputs' % name
            path = os.path.join(results_path, region_out)
            input_naip = '%s/%s/Outputs' % (results_path, name)
            # New spatially joined feature to
            out_path = '%s/s%s' % (gt_output_folder, shp_filename)

            # Spatial join naip qq layer with random points allows for
            # bypassing the nested loops required to get necessary
            # attributes. Original random points layer are deleted after
            # process runs, and all fields except 'FID', 'Shape',
            # and 'GT_Year' are deleted.
            arcpy.analysis.SpatialJoin(shp_path,
                                       naipqq_layer,
                                       out_path,
                                       "JOIN_ONE_TO_ONE", "KEEP_ALL")

    # Get required fields from spatially joined point layer
    with arcpy.da.SearchCursor(out_path,
                               ['FID', 'SHAPE@X', 'SHAPE@Y',
                                'GT_2009', 'FileName']) as cur3:
        for row3 in cur3:
            # Read filenames as raster
            filename = row3[4][:-13]
            cfrtiffile_path = '%s/cfr%s.tif' % (input_naip, filename)
            raster = cfrtiffile_path
            ras = arcpy.sa.Raster(raster)
            res = (ras.meanCellWidth, ras.meanCellHeight)
            # Convert raster to NumPy array to read values
            ras_a = arcpy.RasterToNumPyArray(ras)
            # Get xy values of point
            pnt_x = row3[1]
            pnt_y = row3[2]
            xy = (pnt_x, pnt_y)
            # Perform get_array_indices to get rows and cols of the point in
            # its corresponding array
            rc = get_array_indices(xy, ras.extent, res)
            with arcpy.da.UpdateCursor(out_path, ['GT_2009'],
                                       'FID = %d' % row3[0]) as cur:
                for row in cur:
                    print(ras_a[rc[0]][rc[1]])
                    row[0] = ras_a[rc[0]][rc[1]]
                    cur.updateRow(row)

    # Delete all fields except only those required
    list_fields = arcpy.ListFields(out_path)
    fields = ['FID', 'Shape', field]
    delete_fields = [x.name for x in list_fields if x.name not in fields]
    arcpy.DeleteField_management(out_path, delete_fields)
    # Delete original point shapefile
    arcpy.Delete_management(shp_path)
    print('Completed')



