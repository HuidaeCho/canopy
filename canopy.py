################################################################################
# Name:    canopy.py
# Purpose: This module provides utility functions for preprocessing NAIP tiles
#          and postprocessing trained canopy tiles.
# Author:  Huidae Cho, Ph.D., IESA, University of North Georgia
# Since:   November 29, 2019
# Grant:   Sponsored by the Georgia Forestry Commission through the Georgia
#          Statewide Canopy Assessment Phase I: Canopy Analysis 2009 project
################################################################################

import arcpy
import os
import json
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

    fs = arcpy.FeatureSet(naipqq_layer)
    fsjson = json.loads(fs.JSON)
    for field in fsjson['fields']:
        if field['name'] == naipqq_phyregs_field:
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
                    where_clause="PHYSIO_ID=%d" % phyreg_id)
            arcpy.SelectLayerByLocation_management(naipqq_layer,
                    select_features=phyregs_layer)
            arcpy.CalculateField_management(naipqq_layer, naipqq_phyregs_field,
                    '!%s!+"%d,"' % (naipqq_phyregs_field, phyreg_id),
                    'PYTHON_9.3')
    arcpy.SelectLayerByAttribute_management(phyregs_layer, 'CLEAR_SELECTION')
    arcpy.SelectLayerByAttribute_management(naipqq_layer, 'CLEAR_SELECTION')
    print("Completed")

def reproject_input_tiles(phyreg_ids):
    '''
    This function reprojects and snaps the NAIP tiles that intersect selected
    physiographic regions.

    phyreg_ids: list of physiographic region IDs to process
    '''
    phyregs_layer = canopy_config.phyregs_layer
    naipqq_layer = canopy_config.naipqq_layer
    naipqq_phyregs_field = canopy_config.naipqq_phyregs_field
    snaprast_path = canopy_config.snaprast_path
    spatref_path = canopy_config.spatref_path
    naip_path = canopy_config.naip_path
    results_path = canopy_config.results_path

    spatref = arcpy.Raster(spatref_path).spatialReference

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
    print("Completed")

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
    print("Completed")

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
                                where_clause="%s=%d" % (naipqq_oidfield, oid)
                        arcpy.gp.ExtractByMask_sa(frtiffile_path, naipqq_layer,
                                cfrtiffile_path)
    print("Completed")

def mosaic_clipped_final_tiles(phyreg_ids):
    '''
    This function mosaics clipped final TIFF files and clips mosaicked files to
    physiographic regions.

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
            canopytif_path = '%s/canopy_2009_%s.tif' % (outdir_path, name)
            if os.path.exists(canopytif_path):
                continue
            mosaictif_filename = 'mosaic_2009_%s.tif' % name
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
    print("Completed")

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
    
def gt_point(count):
	'''
	This function is designed to provide randomized points for ground truthing.
	
	The points are projected in WKID 102039: USA Contiguous Albers Equal Area 
	Conic USGS version
	
	
	'''
	
	project_path = canopy_config.project_path
	phyregs_layer = canopy_config.phyregs_layer
	results_path = canopy_config.results_path
	ind_regions =  '%s/IndvidualRegions' %results_path
	ouput_folder = '%s/GroundTruth' % results_path
	
	regions_path = []
	names = []
    
    arcpy.env.overwriteOutput=True
    arcpy.env.addOutputsToMap=False

    # WKID 102039: USA Contiguous Albers Equal Area Conic USGS version
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(102039)
	
	if not os.path.exists(ind_regions):
		os.makedirs(ind_regions)
	
	arcpy.SplitByAttributes_analysis(phyregs_layer, ind_regions, ['NAME'])
	
	for dir, subdir, files in os.walk(ind_regions):
		for f in files:
			if f.endswith('.shp'):
				regions_path.append(os.path.join(ind_regions, f))
			if len(regions_path) == 24:
					continue
		for f in files:
			if f.endswith('.shp'):
				names.append('gt_' + f[:-4])
		if os.path.exists(ouput_folder):
				break
		if not os.path.exists(ouput_folder):
			os.makedirs(ouput_folder)

	in_file = []
	for i in range(len(names)):
		for f in names:
			rp_points = results_path + '/%s' % f
		if os.path.exists(rp_points + '.shp'):
			break
		if not os.path.exists(rp_points + '.shp'):
			arcpy.CreateRandomPoints_management(results_path, names[i], regions_path[i], '', count)
			print(names[i])
			
	for dir, subdir, files in os.walk(results_path):
		for f in files:
			if f.endswith('.shp'):
				in_file.append(os.path.join(results_path, f))
		for i in range(len(in_file)):
			arcpy.AddFields_management(in_file[i], [['GT_2009', 'TEXT'], ['GT_2015', 'TEXT']])


