"""
Created by Chungkang Choi
January 2024

Description: Calculate Proximity
"""

import os
import pandas as pd
import rasterio
from osgeo import gdal

def calculate_proximity(input_raster_path, output_raster_path, max_distance):
    # Open the source raster file
    src_ds = gdal.Open(input_raster_path, gdal.GA_ReadOnly)
    if src_ds is None:
        print(f"Unable to open {input_raster_path} for reading")
        return

    # Create the output raster file
    driver = gdal.GetDriverByName('GTiff')
    out_ds = driver.CreateCopy(output_raster_path, src_ds, 0)
    if out_ds is None:
        print(f"Unable to create {output_raster_path}")
        return

    # Calculate proximity
    options = ['MAXDIST={}'.format(max_distance), 'VALUES=1']
    gdal.ComputeProximity(src_ds.GetRasterBand(1), out_ds.GetRasterBand(1), options)

    # Clean up
    src_ds = None
    out_ds = None
    print(f"Proximity calculation completed for {input_raster_path}")


input_path = r'data\\step4\\'
output_path = r'data\\step5\\'
input_excel_path = input_path + r'step4_excel_template.xlsx'

# Read the input Excel file
df_input_excel = pd.read_excel(input_excel_path)

# Initialize a list to keep track of processed files for the Excel output
processed_files = []

tif_df = df_input_excel[df_input_excel['file_name'].str.lower().str.endswith('.tif')]

# Process '.tif' files for proximity calculation
for idx, row in tif_df.iterrows():
    input_file_path = os.path.join(input_path, row['file_name'])
    if row['proximity'] == 1:
        output_file_name = os.path.splitext(row['file_name'])[0] + '_proximity.tif'
        output_file_path = os.path.join(output_path, output_file_name)
        calculate_proximity(input_file_path, output_file_path, 50000)  # 50 km in meters

        # Add file details to the processed_files list
        processed_files.append({
            'file_name': output_file_name,
            'source_resolution(m)': row['source_resolution(m)'],
            'target_resolution(m)': row['target_resolution(m)'],
            'source_CRS': row['source_CRS'],
            'target_CRS': row['target_CRS'],
            'AOI': row['AOI'],
            'proximity': '1'
        })
    else:
        # For files not requiring proximity calculation, simply copy the existing details
        processed_files.append(row.to_dict())

# Create a DataFrame from the processed_files list
df_processed = pd.DataFrame(processed_files)

# Define the path for the output Excel file
output_excel_path = os.path.join(output_path, 'step5_excel_template.xlsx')

# Save the DataFrame to an Excel file
df_processed.to_excel(output_excel_path, index=False)
