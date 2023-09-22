"""
Created by Kimberly Mason
November 2022

Modified by Chungkang Choi
September 2023

Description: Performs a site filtering and exclusion
"""
import geopandas as gpd
from shapely.geometry import box
from osgeo import ogr
import rasterio
import warnings

from a_settings import *
from custom_functions import *

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message="Setting nodata to -999; specify nodata explicitly")
warnings.filterwarnings("ignore", message="Column names longer than 10 ")

####################### FILE PATHS #############################################
input_data_path = PATH + "00_input_data\\"
data_download_path = PATH + "01_data_download\\"
filtering_path = PATH + "02_filtering\\"
rasterizing_path = PATH + "03_rasterizing\\"
exclusion_path = PATH + "04_exclusion\\"
clipping_path = PATH + "05_clipping\\"
proximity_path = PATH + "06_proximity\\"

shp_driver = ogr.GetDriverByName("ESRI Shapefile")
boundary_data = shp_driver.Open(data_download_path + "boundary.shp")
boundary = boundary_data.GetLayer()

shp_crs = boundary.GetSpatialRef()
boundary_x_min, boundary_x_max, boundary_y_min, boundary_y_max = boundary.GetExtent()
boundary_x_resolusion = int((boundary_x_max - boundary_x_min) / PIXEL_SIZE)
boundary_y_resslusion = int((boundary_y_max - boundary_y_min) / PIXEL_SIZE)

####################### FILTERING ##############################################
water = gpd.read_file(input_data_path + "water.shp")
water = water.to_crs(epsg=EPSG)
water['area'] = water.geometry.area  # This will calculate the area in square meters
filtered_water = water[water['area']/10000 > MIN_AREA]
filtered_water.to_file(filtering_path + "filtered_water.shp")

print("Filtering complete")

####################### RASTERIZING ##############################################
# input data
rasterize(input_data_path + "protected_area.shp" , rasterizing_path + "protected_area.tif", shp_crs, PIXEL_SIZE, boundary_x_resolusion, boundary_y_resslusion, 1, 0, boundary_x_min, boundary_y_max)

# downloaed data from osm
rasterize(data_download_path + "boundary.shp", rasterizing_path + "boundary.tif", shp_crs, PIXEL_SIZE, boundary_x_resolusion, boundary_y_resslusion, 1, 0, boundary_x_min, boundary_y_max) # POI area
rasterize(data_download_path + "substation.shp", rasterizing_path + 'substation.tif', shp_crs, PIXEL_SIZE, boundary_x_resolusion, boundary_y_resslusion, 1, 0, boundary_x_min, boundary_y_max)
rasterize(data_download_path + "roads.shp", rasterizing_path + 'roads.tif', shp_crs, PIXEL_SIZE, boundary_x_resolusion, boundary_y_resslusion, 1, 0, boundary_x_min, boundary_y_max)
rasterize(data_download_path + "buffered_river.shp", rasterizing_path + 'buffered_river.tif', shp_crs, PIXEL_SIZE, boundary_x_resolusion, boundary_y_resslusion, 1, 0, boundary_x_min, boundary_y_max)

# filtered data
rasterize(filtering_path + "filtered_water.shp", rasterizing_path + 'water.tif', shp_crs, PIXEL_SIZE, boundary_x_resolusion, boundary_y_resslusion, 1, 0, boundary_x_min, boundary_y_max) # consider non water body as exclusion area
rasterize(filtering_path + "filtered_water.shp", rasterizing_path + 'non_water.tif', shp_crs, PIXEL_SIZE, boundary_x_resolusion, boundary_y_resslusion, 0, 1, boundary_x_min, boundary_y_max) # consider non water body as exclusion area
rasterize(filtering_path + "main_roads.shp", rasterizing_path + 'main_roads.tif', shp_crs, PIXEL_SIZE, boundary_x_resolusion, boundary_y_resslusion, 1, 0, boundary_x_min, boundary_y_max)

print("Rasterizing complete")

####################### EXCLUSION ##############################################
raster_protected = rasterio.open(rasterizing_path + "protected_area.tif")
raster_non_water = rasterio.open(rasterizing_path + "non_water.tif")

exclusion = raster_protected.read(1) * raster_non_water.read(1)
save_raster(exclusion, boundary_x_resolusion, boundary_y_resslusion, PIXEL_SIZE, PIXEL_SIZE, exclusion_path + "exclusion.tif", True, rasterizing_path + "boundary.tif", boundary_x_min, boundary_y_max)

print("Exclusion complete")

####################### CLIPPING ##############################################
boundary_bbox_raster = get_raster_bbox(rasterizing_path + "boundary.tif")
clip_raster(input_data_path + "DSM.tif", boundary_bbox_raster, EPSG, clipping_path + "DSM_clip.tif")
clip_raster(input_data_path + "wind.tif", boundary_bbox_raster, EPSG, clipping_path + "wind_clip.tif")
clip_raster(input_data_path + "GHI.tif", boundary_bbox_raster, EPSG, clipping_path + "GHI_clip.tif")
clip_raster(input_data_path + "PVOUT.tif", boundary_bbox_raster, EPSG, clipping_path + "PVOUT_clip.tif")

print("Clipping complete")

####################### PROXIMITY ##############################################
proximity(rasterizing_path + "substation.tif", proximity_path + 'substation_proximity.tif')
proximity(rasterizing_path +"roads.tif", proximity_path + 'roads_proximity.tif')
proximity(rasterizing_path +"protected_area.tif", proximity_path + 'protected_area_proximity.tif')
proximity(rasterizing_path + "main_roads.tif", proximity_path + 'main_roads_proximity.tif')
proximity(rasterizing_path + "water.tif", proximity_path + 'water_proximity.tif')


print("Proximity complete")
