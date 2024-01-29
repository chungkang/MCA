import os
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from pyproj import Transformer

path_data = r'data\\step1\\'
path_read = r'data\\step2\\'
path_write = r'data\\step3\\'
input_excel_path = path_read + r'step2_excel_template.xlsx'

# create panda data frame for each purpose
df_input_excel = pd.read_excel(input_excel_path)

#  process '.shp', '.geojson' files
shp_geojson_df = df_input_excel[df_input_excel['file_name'].str.lower().str.endswith(('.shp', '.geojson'))]

for idx, row in shp_geojson_df.iterrows():
    if row['source_CRS'] != row['target_CRS']:
        gdf = gpd.read_file(os.path.join(path_data, row['file_name']))  # add path
        
        # convert CRS to EPSG:3857
        gdf = gdf.to_crs(row['target_CRS'])
        
        output_file_name = os.path.splitext(row['file_name'])[0] + '_EPSG3857.shp'  # change file name
        output_file_path = os.path.join(path_write, output_file_name)  # add path
        gdf.to_file(output_file_path, driver='ESRI Shapefile')  # save as Shapefile

# process '.tif' file
tif_df = df_input_excel[df_input_excel['file_name'].str.lower().str.endswith('.tif')]

for idx, row in tif_df.iterrows():
    if row['source_CRS'] != row['target_CRS']:
        input_file_path = os.path.join(path_data, row['file_name'])  # add path
        output_file_name = os.path.splitext(row['file_name'])[0] + '_EPSG3857.tif'  # change file name
        output_file_path = os.path.join(path_write, output_file_name)  # add path
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