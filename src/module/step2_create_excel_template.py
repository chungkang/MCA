"""
Created by Chungkang Choi
January 2024

Description: Create Excel Template
"""

import os
import pandas as pd
import rasterio
import geopandas as gpd
from shapely.geometry import box

def get_file_list(directory, file_extensions):
    file_list = []

    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if filename.endswith(tuple(file_extensions)):
            file_info = {'file_name': filename, 'source_CRS': None, 'target_CRS': None, 'source_resolution(m)': None, 'target_resolution(m)': None, 'AOI': None}
            
            if filename.endswith('.tif'):
                with rasterio.open(file_path) as dataset:
                    file_info.update({
                        'source_resolution(m)': dataset.res[0],
                        'source_CRS': dataset.crs.to_string(),
                    })
            else:  # For .shp and .geojson files
                gdf = gpd.read_file(file_path)
                extent = gdf.geometry.total_bounds
                file_info.update({
                    'source_CRS': gdf.crs.to_string(),
                    'AOI': '1' if filename.lower().startswith('aoi') else None
                })

            file_list.append(file_info)

    return file_list

path_read = 'data/step1/'
path_write = 'data/step2/'
extensions = ['.tif', '.shp', '.geojson']

file_data = get_file_list(path_read, extensions)
df = pd.DataFrame(file_data)

# Save to Excel
excel_path = os.path.join(path_write, 'step2_excel_template.xlsx')
df.to_excel(excel_path, index=False)