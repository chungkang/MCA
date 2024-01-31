"""
Created by Chungkang Choi
January 2024

Description: Rasterize Vector + Equalize Resolution
"""

import os
import pandas as pd
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from osgeo import gdal, ogr, osr
import shutil  # library for copying files

def rasterize_vector(input_vector_path, output_raster_path, pixel_size, target_crs, no_data_value=0, burn_value=1):
    # Read vector data
    vector_ds = ogr.Open(input_vector_path)
    vector_layer = vector_ds.GetLayer()

    # Get the spatial reference of the input vector
    source_srs = vector_layer.GetSpatialRef()

    # Create a spatial reference object for the target CRS
    target_srs = osr.SpatialReference()
    target_srs.ImportFromEPSG(target_crs)

    # Get the extent of the input vector
    x_min, x_max, y_min, y_max = vector_layer.GetExtent()

    # Calculate the number of pixels
    x_res = int((x_max - x_min) / pixel_size)
    y_res = int((y_max - y_min) / pixel_size)

    # Create a raster dataset with one band
    # Define GDAL creation options for high compression
    creation_options = [
        'TILED=YES',
        'COMPRESS=DEFLATE',  # Use DEFLATE compression
        'PREDICTOR=1',       # Use predictor 1 (suitable for integer data)
        'ZLEVEL=9'           # Set the compression level (1=fastest, 9=best compression)
    ]

    target_ds = gdal.GetDriverByName('GTiff').Create(output_raster_path, x_res, y_res, 1, gdal.GDT_Byte, options=creation_options)
    target_ds.SetGeoTransform((x_min, pixel_size, 0, y_max, 0, -pixel_size))
    target_ds.SetProjection(target_srs.ExportToWkt())
    band = target_ds.GetRasterBand(1)
    band.SetNoDataValue(no_data_value)

    # Perform the rasterization
    gdal.RasterizeLayer(target_ds, [1], vector_layer, burn_values=[burn_value])

    # Clean up
    band = None
    target_ds = None
    vector_ds = None


input_path = r'data\\step3\\'
output_path = r'data\\step4\\'
input_excel_path = input_path + r'step3_excel_template.xlsx'

# Read the input Excel file
df_input_excel = pd.read_excel(input_excel_path)

# Initialize a list to keep track of processed files for the Excel output
processed_files = []

# Process '.shp' files for rasterization
shp_df = df_input_excel[df_input_excel['file_name'].str.lower().str.endswith('.shp')]

# Find the row where AOI is 1
aoi_row = df_input_excel[df_input_excel['AOI'] == 1]

for idx, row in shp_df.iterrows():
    input_vector_path = os.path.join(input_path, row['file_name'])
    output_raster_path = os.path.join(output_path, os.path.splitext(row['file_name'])[0] + '_rasterized.tif')
    pixel_size = row['target_resolution(m)']
    target_crs = int(row['target_CRS'].split(':')[-1])  # Assuming the CRS is given in 'EPSG:xxxx' format

    rasterize_vector(input_vector_path, output_raster_path, pixel_size, target_crs)

    # Add file details to the processed_files list
    processed_files.append({
        'file_name': os.path.basename(output_raster_path),
        'source_resolution(m)': None,  # Shapefiles do not have a resolution
        'target_resolution(m)': pixel_size,
        'source_CRS': row['source_CRS'],
        'target_CRS': row['target_CRS'],
        'AOI': row['AOI'],
        'exclusion': None,
        'proximity': None
    })

# Process '.tif' files for resolution equalization
tif_df = df_input_excel[df_input_excel['file_name'].str.lower().str.endswith('.tif')]

for idx, row in tif_df.iterrows():
    input_file_path = os.path.join(input_path, row['file_name'])

    # when resolutions of input and output are different, reprocessing and saving
    if row['source_resolution(m)'] is not None and row['source_resolution(m)'] != row['target_resolution(m)']:    
        output_file_name = os.path.splitext(row['file_name'])[0] + '_equalized.tif'
        output_file_path = os.path.join(output_path, output_file_name)
    
        with rasterio.open(input_file_path) as src:
            transform, width, height = calculate_default_transform(
                src.crs, src.crs, src.width, src.height, *src.bounds,
                dst_width=int(src.width * (src.res[0] / row['target_resolution(m)'])),
                dst_height=int(src.height * (src.res[1] / row['target_resolution(m)']))
            )

            kwargs = src.meta.copy()
            kwargs.update({'crs': src.crs, 'transform': transform, 'width': width, 'height': height})
            # Define compression options
            kwargs.update({'tiled': True, 'compress': 'DEFLATE', 'predictor': 1, 'zlevel': 9})

            with rasterio.open(output_file_path, 'w', **kwargs) as dst:
                for i in range(1, src.count + 1):
                    reproject(source=rasterio.band(src, i), destination=rasterio.band(dst, i), src_transform=src.transform, src_crs=src.crs, dst_transform=transform, dst_crs=src.crs, resampling=Resampling.nearest)
    
    # copy input file as output file
    else:
        output_file_name = row['file_name']
        output_file_path = os.path.join(output_path, output_file_name)
        shutil.copy(input_file_path, output_file_path)

    # add file info to excel
    processed_files.append({
        'file_name': output_file_name,
        'source_resolution(m)': row['source_resolution(m)'],
        'target_resolution(m)': row['target_resolution(m)'],
        'source_CRS': row['source_CRS'],
        'target_CRS': row['target_CRS'],
        'AOI': row['AOI'],
        'exclusion': None,
        'proximity': None
    })

# Create a DataFrame from the processed_files list
df_processed = pd.DataFrame(processed_files)

# Define the path for the output Excel file
output_excel_path = os.path.join(output_path, 'step4_excel_template.xlsx')

# Save the DataFrame to an Excel file
df_processed.to_excel(output_excel_path, index=False)