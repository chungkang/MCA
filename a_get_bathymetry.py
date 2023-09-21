# -*- coding: utf-8 -*-
"""
Created by Kimberly Mason
November 2022

Description: Finds the bathymetry tif files located in the project area and copies them to the In_Data folder
"""
import os
import shutil
import rasterio
import geopandas as gpd
import concurrent.futures

from settings import *
####################### FILE PATHS #############################################
input_data_path = PATH + PROJECT + "00_input_data\\"
data_download_path = PATH + PROJECT + "01_data_download\\"

fp_boundary = data_download_path + "boundary.shp"

boundary = gpd.read_file(fp_boundary)
boundary = boundary.set_crs(epsg=EPSG)
boundary = boundary.to_crs('epsg:4326')
bounds = boundary.total_bounds

left,bottom, right, top = bounds[0], bounds[1], bounds[2], bounds[3]

bathymetry_fp = '..\\datasource\\Bathymetry_Rasters\\'
output_fp = data_download_path + 'Bathymetry\\'

# for top_folder in os.listdir(bathymetry_fp):
#     print(f"checking {bathymetry_fp + top_folder}")

#     for folder in os.listdir(bathymetry_fp + top_folder):
#         for file in os.listdir(bathymetry_fp + top_folder + '\\' + folder):
#             filename = os.fsdecode(file)
            
#             if filename.endswith(".tif"):
#                 dataset = rasterio.open(bathymetry_fp + top_folder + '\\' + folder + '\\' + filename)
#                 dataset.bounds
    
#                 if left < dataset.bounds[0] < right or left < dataset.bounds[2] < right:
#                     if bottom < dataset.bounds[1] < top or bottom < dataset.bounds[3] < top:
#                         shutil.copyfile(bathymetry_fp + top_folder + '\\' + folder + '\\' + filename, output_fp + filename)
# print("all tifs checked")

def process_file(file_path):
    with rasterio.open(file_path) as dataset:
        if left < dataset.bounds[0] < right or left < dataset.bounds[2] < right:
            if bottom < dataset.bounds[1] < top or bottom < dataset.bounds[3] < top:
                shutil.copy2(file_path, output_fp + os.path.basename(file_path))

def main():
    file_paths = []
    
    for top_folder in os.listdir(bathymetry_fp):
        for folder in os.listdir(bathymetry_fp + top_folder):
            for file in os.listdir(bathymetry_fp + top_folder + '\\' + folder):
                filename = os.fsdecode(file)
                if filename.endswith(".tif"):
                    file_paths.append(bathymetry_fp + top_folder + '\\' + folder + '\\' + filename)

    # Configuring a Thread Pool for Parallel Processing
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(process_file, file_paths)

if __name__ == "__main__":
    main()