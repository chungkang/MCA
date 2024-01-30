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

def get_file_list(directory, file_extension):
    file_dict = {}
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        for extension in file_extension:
            if filename.endswith(extension):
                file_type = 'etc'
                if extension == '.tif':
                    file_type = 'raster'
                elif (extension == '.shp') or (extension == '.geojson'):
                    file_type = 'vector'

                if file_type == 'raster':
                    # Open a TIFF file
                    with rasterio.open(file_path) as dataset:
                        # Access resolution, CRS
                        resolution = dataset.res[0]
                        crs = dataset.crs
                    file_dict[file_path] = {
                        'file_name': filename,
                        'source_resolution(m)': resolution,
                        'target_resolution(m)': None,
                        'source_CRS': crs,
                        'target_CRS': None,
                        'AOI': None,
                    }
                elif file_type == 'vector':
                    # Check CRS of shapefile or geojson
                    gdf = gpd.read_file(file_path)
                    crs = gdf.crs
                    extent = gdf.geometry.total_bounds
                    aoi = box(extent[0], extent[1], extent[2], extent[3]).wkt
                    file_dict[file_path] = {
                        'file_name': filename,
                        'source_resolution(m)': None,
                        'target_resolution(m)': None,
                        'source_CRS': crs,
                        'target_CRS': None,
                        'AOI': '1' if filename.lower().startswith('aoi') else None
                    }
    return file_dict

path_read = r'data\\step1\\'
path_write = r'data\\step2\\'
extension = ['.tif', '.shp', '.geojson']

files = get_file_list(path_read, extension)

df = pd.DataFrame(files)

# change row and column
df_transposed = df.transpose()

# add headers
df_transposed.columns = [
    'file_name',
    'source_resolution(m)',
    'target_resolution(m)',
    'source_CRS',
    'target_CRS',
    'AOI',
]

# save excel
excel_path = path_write + r'step2_excel_template.xlsx'
df_transposed.to_excel(excel_path, index=False)