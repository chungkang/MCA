"""
Created by Chungkang Choi
January 2024

Description: Convert CRS
"""

import os
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import shutil

input_data_path = r'data\\step1\\'
input_excel_path = r'data\\step2\\'
output_path = r'data\\step3\\'
input_excel_path = input_excel_path + r'step2_excel_template.xlsx'

# create panda data frame for each purpose
df_input_excel = pd.read_excel(input_excel_path)

# Initialize a list to keep track of processed files for the Excel output
processed_files = []

#  process '.shp', '.geojson' files
shp_geojson_df = df_input_excel[df_input_excel['file_name'].str.lower().str.endswith(('.shp', '.geojson'))]

for idx, row in shp_geojson_df.iterrows():
    gdf = gpd.read_file(os.path.join(input_data_path, row['file_name']))  # add path

    # convert CRS
    if row['source_CRS'] != row['target_CRS']:
        gdf = gdf.to_crs(row['target_CRS'])

    # only rename and save as shape file
    output_file_name = os.path.splitext(row['file_name'])[0] + '_CRS.shp'  # change file name
    output_file_path = os.path.join(output_path, output_file_name)  # add path
    gdf.to_file(output_file_path, driver='ESRI Shapefile')  # save as Shapefile

    # Add file details to the processed_files list
    processed_files.append({
        'file_name': output_file_name,
        'source_resolution(m)': None,  # Shapefiles do not have a resolution
        'target_resolution(m)': row['target_resolution(m)'],
        'source_CRS': row['source_CRS'],
        'target_CRS': row['target_CRS'],
        'AOI': row['AOI']
    })

# process '.tif' file
tif_df = df_input_excel[df_input_excel['file_name'].str.lower().str.endswith('.tif')]

for idx, row in tif_df.iterrows():
    input_file_path = os.path.join(input_data_path, row['file_name'])  # add path
    output_file_name = os.path.splitext(row['file_name'])[0] + '_CRS.tif'  # change file name
    output_file_path = os.path.join(output_path, output_file_name)  # add path
    
    if row['source_CRS'] != row['target_CRS']:
        with rasterio.open(input_file_path) as src:
            transform, width, height = calculate_default_transform(src.crs, row['target_CRS'], src.width, src.height, *src.bounds)
            kwargs = src.meta.copy()
            kwargs.update({'crs': row['target_CRS'], 'transform': transform, 'width': width, 'height': height})
            
            with rasterio.open(output_file_path, 'w', **kwargs) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=row['target_CRS'],
                        resampling=Resampling.nearest)
    else:
        shutil.copy(input_file_path, output_file_path)
    
    # Add file details to the processed_files list
    processed_files.append({
        'file_name': output_file_name,
        'source_resolution(m)': row['source_resolution(m)'],
        'target_resolution(m)': row['target_resolution(m)'],
        'source_CRS': row['source_CRS'],
        'target_CRS': row['target_CRS'],
        'AOI': row['AOI']
    })


# Create a DataFrame from the processed_files list
df_processed = pd.DataFrame(processed_files)

# Define the path for the output Excel file
output_excel_path = os.path.join(output_path, 'step3_excel_template.xlsx')

# Save the DataFrame to an Excel file
df_processed.to_excel(output_excel_path, index=False)
