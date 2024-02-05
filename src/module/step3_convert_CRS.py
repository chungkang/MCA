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

def convert_crs(input_file_path, output_file_path, source_crs, target_crs, is_raster):
    if is_raster:
        with rasterio.open(input_file_path) as src:
            if source_crs != target_crs:
                transform, width, height = calculate_default_transform(src.crs, target_crs, src.width, src.height, *src.bounds)
                kwargs = src.meta.copy()
                kwargs.update({'crs': target_crs, 'transform': transform, 'width': width, 'height': height})
                with rasterio.open(output_file_path, 'w', **kwargs) as dst:
                    for i in range(1, src.count + 1):
                        reproject(
                            source=rasterio.band(src, i),
                            destination=rasterio.band(dst, i),
                            src_transform=src.transform,
                            src_crs=src.crs,
                            dst_transform=transform,
                            dst_crs=target_crs,
                            resampling=Resampling.nearest)
            else:
                shutil.copy(input_file_path, output_file_path)
    else:
        gdf = gpd.read_file(input_file_path)
        if source_crs != target_crs:
            gdf = gdf.to_crs(target_crs)
        gdf.to_file(output_file_path, driver='ESRI Shapefile')

def process_files(df_input_excel, input_data_path, output_path):
    processed_files = []

    for idx, row in df_input_excel.iterrows():
        input_file_path = os.path.join(input_data_path, row['file_name'])
        file_ext = '.shp' if os.path.splitext(row['file_name'])[1].lower() in ['.geojson', '.shp'] else os.path.splitext(row['file_name'])[1]
        output_file_name = os.path.splitext(row['file_name'])[0] + '_CRS' + file_ext
        output_file_path = os.path.join(output_path, output_file_name)

        is_raster = file_ext == '.tif'
        convert_crs(input_file_path, output_file_path, row['source_CRS'], row['target_CRS'], is_raster)

        processed_files.append({
            'file_name': output_file_name,
            'source_CRS': row['source_CRS'],
            'target_CRS': row['target_CRS'],
            'source_resolution(m)': row['source_resolution(m)'] if is_raster else None,
            'target_resolution(m)': row['target_resolution(m)'],
            'AOI': row['AOI']
        })

    return processed_files

input_path = r'data\\step1\\'
output_path = r'data\\step3\\'
setting_excel_path = r'data\\setting_excel\\'
input_excel_path = setting_excel_path + r'step2_excel_template.xlsx'
output_excel_path = setting_excel_path + r'step3_excel_template.xlsx'

df_input_excel = pd.read_excel(input_excel_path)

processed_files = process_files(df_input_excel, input_path, output_path)
df_processed = pd.DataFrame(processed_files)
df_processed.to_excel(output_excel_path, index=False)
