"""
Created by Chungkang Choi
January 2024

Description: Clip Extend
"""

import os
import pandas as pd
from osgeo import gdal
import shutil  # library for copying files

# find AOI extent
def get_aoi_extent(aoi_raster_path):
    aoi_ds = gdal.Open(aoi_raster_path)
    if not aoi_ds:
        raise RuntimeError(f"Failed to open AOI raster file: {aoi_raster_path}")

    geo_transform = aoi_ds.GetGeoTransform()
    min_x = geo_transform[0]
    max_y = geo_transform[3]
    max_x = min_x + geo_transform[1] * aoi_ds.RasterXSize
    min_y = max_y + geo_transform[5] * aoi_ds.RasterYSize
    aoi_ds = None

    return min_x, min_y, max_x, max_y

def clip_extend(input_raster_path, output_raster_path, aoi_extent):
    # AOI extent is passed directly
    min_x, min_y, max_x, max_y = aoi_extent


    # Define GDAL creation options for high compression
    creation_options = [
        'TILED=YES',
        'COMPRESS=DEFLATE',  # Use DEFLATE compression
        'PREDICTOR=1',       # Use predictor 1 (suitable for integer data)
        'ZLEVEL=9',           # Set the compression level (1=fastest, 9=best compression)
        'BIGTIFF=YES',  # Optional, for handling large files
    ]

    # Clip the input raster with this extent
    warp_options = gdal.WarpOptions(format='GTiff', outputType=gdal.GDT_Float32, outputBounds=[min_x, min_y, max_x, max_y], dstNodata=0, creationOptions=creation_options)
    gdal.Warp(output_raster_path, input_raster_path, options=warp_options)


input_path = r'data\\step5\\'
output_path = r'data\\step6\\'
input_excel_path = input_path + r'step5_excel_template.xlsx'

# Read the input Excel file
df_input_excel = pd.read_excel(input_excel_path)

# Initialize a list to keep track of processed files for the Excel output
processed_files = []

tif_df = df_input_excel[df_input_excel['file_name'].str.lower().str.endswith('.tif')]

AOI_df = tif_df[tif_df['AOI'] == 1]
aoi_file_name = AOI_df.iloc[0]['file_name']  # Assuming first row contains the AOI raster
aoi_file_path = os.path.join(input_path, aoi_file_name)
aoi_extent = get_aoi_extent(aoi_file_path)

# Process '.tif' files for proximity calculation
for idx, row in tif_df.iterrows():
    input_file_path = os.path.join(input_path, row['file_name'])

    if row['AOI'] == 1:
        output_file_name = row['file_name']
        output_file_path = os.path.join(output_path, output_file_name)
        shutil.copy(input_file_path, output_file_path)

    else:
        # Define paths for AOI and output raster
        output_file_name = os.path.splitext(row['file_name'])[0] + '_clip.tif'
        output_file_path = os.path.join(output_path, output_file_name)
        aoi_raster_path = input_file_path  # Assuming AOI raster is the same as input

        # Perform clipping
        clip_extend(input_file_path, output_file_path, aoi_extent)  # Use the aoi_extent for clipping

    # Add file info to excel
    processed_files.append({
        'file_name': output_file_name,
        'source_resolution(m)': row['source_resolution(m)'],
        'target_resolution(m)': row['target_resolution(m)'],
        'source_CRS': row['source_CRS'],
        'target_CRS': row['target_CRS'],
        'AOI': row['AOI'],
        'exclusion': row['exclusion'],
        'most_suitable': None,
        'suitable': None,
        'least_suitable': None,
        'exclusive_range': None,
        'layer_weight': None
    })

# Create a DataFrame from the processed_files list
df_processed = pd.DataFrame(processed_files)

# Define the path for the output Excel file
output_excel_path = os.path.join(output_path, 'step6_excel_template.xlsx')

# Save the DataFrame to an Excel file
df_processed.to_excel(output_excel_path, index=False)
