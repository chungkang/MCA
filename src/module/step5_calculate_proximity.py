"""
Created by Chungkang Choi
January 2024

Description: Calculate Proximity
"""

import os
import pandas as pd
from osgeo import gdal
import shutil  # library for copying files

def calculate_proximity(input_raster_path, output_raster_path, max_distance):
    # Open the source raster file
    src_ds = gdal.Open(input_raster_path, gdal.GA_ReadOnly)
    if src_ds is None:
        print(f"Unable to open {input_raster_path} for reading")
        return

    # Define GDAL creation options for high compression
    creation_options = [
        'TILED=YES',
        'COMPRESS=DEFLATE',  # Use DEFLATE compression
        'PREDICTOR=1',       # Use predictor 1 (suitable for integer data)
        'ZLEVEL=9'           # Set the compression level (1=fastest, 9=best compression)
    ]

    # Create the output raster file with compression options
    driver = gdal.GetDriverByName('GTiff')
    out_ds = driver.Create(output_raster_path, src_ds.RasterXSize, src_ds.RasterYSize,1, gdal.GDT_Float32, options=creation_options)
    if out_ds is None:
        print(f"Unable to create {output_raster_path}")
        return

    out_ds.SetGeoTransform(src_ds.GetGeoTransform())
    out_ds.SetProjection(src_ds.GetProjectionRef())

    # Initialize band to 0 (or another suitable no data value)
    out_band = out_ds.GetRasterBand(1)
    out_band.Fill(0)  # or another no data value

    # Calculate proximity
    options = ['MAXDIST={}'.format(max_distance), 'VALUES=1', 'DISTUNITS=GEO']
    gdal.ComputeProximity(src_ds.GetRasterBand(1), out_band, options)

    # Clean up
    src_ds = None
    out_ds = None
    print(f"Proximity calculation completed for {input_raster_path}")


input_path = r'data\\step4\\'
output_path = r'data\\step5\\'
setting_excel_path = r'data\\setting_excel\\'
input_excel_path = setting_excel_path + r'step4_excel_template.xlsx'
output_excel_path = setting_excel_path + r'step5_excel_template.xlsx'

# Read the input Excel file
df_input_excel = pd.read_excel(input_excel_path)

# Initialize a list to keep track of processed files for the Excel output
processed_files = []

tif_df = df_input_excel[df_input_excel['file_name'].str.lower().str.endswith('.tif')]

# Process '.tif' files for proximity calculation
for idx, row in tif_df.iterrows():
    input_file_path = input_path + row['file_name']
  
    if row['proximity'] == 1:
        output_file_name = os.path.splitext(row['file_name'])[0] + '_proximity.tif'
        output_file_path = output_path + output_file_name
        calculate_proximity(input_file_path, output_file_path, 50000)  # 50 km in meters
   
    else:
        output_file_name = row['file_name']
        output_file_path = output_path + output_file_name
        shutil.copy(input_file_path, output_file_path)

    # add file info to excel
    processed_files.append({
        'file_name': output_file_name,
        'source_resolution(m)': row['source_resolution(m)'],
        'target_resolution(m)': row['target_resolution(m)'],
        'source_CRS': row['source_CRS'],
        'target_CRS': row['target_CRS'],
        'AOI': row['AOI'],
        'exclusion': None
    })

    # Check for exclusion
    if row.get('exclusion') == 1:
        exclusion_output_file_name = os.path.splitext(row['file_name'])[0] + '_exclusion.tif'
        exclusion_output_file_path = output_path + exclusion_output_file_name
        shutil.copy(input_file_path, exclusion_output_file_path)

        # Add exclusion file info to processed files
        processed_files.append({
            'file_name': exclusion_output_file_name,
            'source_resolution(m)': row['source_resolution(m)'],
            'target_resolution(m)': row['target_resolution(m)'],
            'source_CRS': row['source_CRS'],
            'target_CRS': row['target_CRS'],
            'AOI': row['AOI'],
            'exclusion': row['exclusion']
        })

# Create a DataFrame from the processed_files list
df_processed = pd.DataFrame(processed_files)

# Save the DataFrame to an Excel file
df_processed.to_excel(output_excel_path, index=False)
