"""
Created by Chungkang Choi
January 2024

Description: Calculate Range
"""

import os
import pandas as pd
from osgeo import gdal
import shutil  # library for copying files

def reclassify_by_range(aoi_raster_path):
   #  reclassify

input_path = r'data\\step6\\'
output_path = r'data\\step7\\'
input_excel_path = input_path + r'step6_excel_template.xlsx'

# Read the input Excel file
df_input_excel = pd.read_excel(input_excel_path)

# Initialize a list to keep track of processed files for the Excel output
processed_files = []

tif_df = df_input_excel[df_input_excel['file_name'].str.lower().str.endswith('.tif')]

# Process '.tif' files for proximity calculation
for idx, row in tif_df.iterrows():
    input_file_path = os.path.join(input_path, row['file_name'])

    # Define paths for AOI and output raster
    output_file_name = os.path.splitext(row['file_name'])[0] + '_scored.tif'
    output_file_path = os.path.join(output_path, output_file_name)
    aoi_raster_path = input_file_path  # Assuming AOI raster is the same as input

    # Add file info to excel
    processed_files.append({
        'file_name': output_file_name,
        'source_resolution(m)': row['source_resolution(m)'],
        'target_resolution(m)': row['target_resolution(m)'],
        'source_CRS': row['source_CRS'],
        'target_CRS': row['target_CRS'],
        'AOI': row['AOI'],
        'exclusion': row['exclusion'],
        'most_suitable': row['most_suitable'],
        'suitable': row['suitable'],
        'least_suitable': row['least_suitable'],
        'exclusive_range': row['exclusive_range'],
        'layer_weight': row['layer_weight']
    })

# Create a DataFrame from the processed_files list
df_processed = pd.DataFrame(processed_files)

# Define the path for the output Excel file
output_excel_path = os.path.join(output_path, 'step7_excel_template.xlsx')

# Save the DataFrame to an Excel file
df_processed.to_excel(output_excel_path, index=False)
