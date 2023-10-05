"""
Created by Kimberly Mason
November 2022

Modified by Chungkang Choi
September 2023

Description: Performs a site filtering and exclusion
"""
import geopandas as gpd
from osgeo import ogr
import rasterio
import warnings

from a_settings import *
from src.functions.custom_functions import *

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message="Setting nodata to -999; specify nodata explicitly")
warnings.filterwarnings("ignore", message="Column names longer than 10 ")

####################### FILE PATHS #############################################
input_data_path = PATH + "00_input_data\\"
osm_data_path = PATH + "01_osm_data\\"
filtering_path = PATH + "02_filtering\\"
rasterizing_path = PATH + "03_rasterizing\\"
exclusion_path = PATH + "04_exclusion\\"
clipping_path = PATH + "05_clipping\\"
proximity_path = PATH + "06_proximity\\"

shp_driver = ogr.GetDriverByName("ESRI Shapefile")
boundary_data = shp_driver.Open(osm_data_path + "boundary.shp")
boundary = boundary_data.GetLayer()

shp_crs = boundary.GetSpatialRef()
boundary_x_min, boundary_x_max, boundary_y_min, boundary_y_max = boundary.GetExtent()
boundary_x_resolusion = int((boundary_x_max - boundary_x_min) / PIXEL_SIZE)
boundary_y_resolusion = int((boundary_y_max - boundary_y_min) / PIXEL_SIZE)

####################### FILTERING ##############################################
# waterbody extracted manually with https://overpass-turbo.eu/ as geojson
"""
[out:json][timeout:25];
(relation["natural"="water"]["water" != "river"]({{bbox}}););
out body;
>;
out skel qt;
"""
waterbodies_geojson = gpd.read_file(osm_data_path + "waterbodies.geojson")
waterbodies_geojson.to_crs(epsg=EPSG)
waterbodies_geojson.to_file(osm_data_path + "waterbodies.shp", driver='ESRI Shapefile')

# filtering waterbodies by size of the area
waterbodies_shp = gpd.read_file(osm_data_path + "waterbodies.shp")
waterbodies_shp = waterbodies_shp.to_crs(epsg=EPSG)
waterbodies_shp['area'] = waterbodies_shp.geometry.area  # This will calculate the area in square meters
filtered_water = waterbodies_shp[waterbodies_shp['area']/10000 > MIN_AREA]
filtered_water.to_file(filtering_path + "filtered_waterbodies.shp")


# # preapre waterbodies.tif extracted from bathymetry
# with rasterio.open(input_data_path + "bathymetry.tif") as src:
#     band1_data = src.read(1)    # Read the data from band 1 into a NumPy array
#     mask = np.where(np.isnan(band1_data), 0, 1)    # Create a mask where non-nan values are set to 1 and nan values are set to 0
#     profile = src.profile    # Create a new output raster with the same metadata as the input
#     profile.update(
#         dtype=rasterio.uint8,  # Data type set to uint8 for 1 and 0 values
#         count=1  # Single-band output
#     )    # Update the profile to specify the data type and number of bands for the output

#     # Open the output raster file for writing
#     with rasterio.open(filtering_path + "waterbodies.tif", "w", **profile) as dst:
#         # Write the mask data to the output raster
#         dst.write(mask, 1)  # Write to band 1

# waterbodies.tif를 shp로 변환 -> 넓이 filtering -> tif로 다시 변환

# 또는 tif 파일 안에서 인접한 1의값으로 면적계산 및 filtering


print("Filtering complete")

####################### RASTERIZING ##############################################
# input data
rasterize(input_data_path + "protected_area.shp" , rasterizing_path + "protected_area.tif", shp_crs, PIXEL_SIZE, boundary_x_resolusion, boundary_y_resolusion, 1, 0, boundary_x_min, boundary_y_max)

# osm data
rasterize(osm_data_path + "boundary.shp", rasterizing_path + "boundary.tif", shp_crs, PIXEL_SIZE, boundary_x_resolusion, boundary_y_resolusion, 1, 0, boundary_x_min, boundary_y_max) # POI area
rasterize(osm_data_path + "substations.shp", rasterizing_path + 'substations.tif', shp_crs, PIXEL_SIZE, boundary_x_resolusion, boundary_y_resolusion, 1, 0, boundary_x_min, boundary_y_max)
rasterize(osm_data_path + "roads.shp", rasterizing_path + 'roads.tif', shp_crs, PIXEL_SIZE, boundary_x_resolusion, boundary_y_resolusion, 1, 0, boundary_x_min, boundary_y_max)
rasterize(osm_data_path + "main_roads.shp", rasterizing_path + 'main_roads.tif', shp_crs, PIXEL_SIZE, boundary_x_resolusion, boundary_y_resolusion, 1, 0, boundary_x_min, boundary_y_max)
rasterize(osm_data_path + "buffered_rivers.shp", rasterizing_path + 'buffered_rivers.tif', shp_crs, PIXEL_SIZE, boundary_x_resolusion, boundary_y_resolusion, 1, 0, boundary_x_min, boundary_y_max)
rasterize(filtering_path + "filtered_waterbodies.shp", rasterizing_path + 'waterbodies.tif', shp_crs, PIXEL_SIZE, boundary_x_resolusion, boundary_y_resolusion, 1, 0, boundary_x_min, boundary_y_max)
rasterize(filtering_path + "filtered_waterbodies.shp", rasterizing_path + 'non_waterbodies.tif', shp_crs, PIXEL_SIZE, boundary_x_resolusion, boundary_y_resolusion, 0, 1, boundary_x_min, boundary_y_max)

print("Rasterizing complete")

####################### EXCLUSION ##############################################
raster_protected = rasterio.open(rasterizing_path + "protected_area.tif")
raster_non_waterbodies = rasterio.open(rasterizing_path + "non_waterbodies.tif")

exclusion = raster_protected.read(1) * raster_non_waterbodies.read(1)
save_raster(exclusion, boundary_x_resolusion, boundary_y_resolusion, PIXEL_SIZE, PIXEL_SIZE, exclusion_path + "exclusion.tif", True, rasterizing_path + "boundary.tif", boundary_x_min, boundary_y_max)

print("Exclusion complete")

####################### CLIPPING ##############################################
boundary_bbox_raster = get_raster_bbox(rasterizing_path + "boundary.tif")
clip_raster(input_data_path + "DEM.tif", boundary_bbox_raster, EPSG, clipping_path + "DEM_clip.tif")
clip_raster(input_data_path + "wind_speed.tif", boundary_bbox_raster, EPSG, clipping_path + "wind_speed_clip.tif")
clip_raster(input_data_path + "GHI.tif", boundary_bbox_raster, EPSG, clipping_path + "GHI_clip.tif")
clip_raster(input_data_path + "PVOUT.tif", boundary_bbox_raster, EPSG, clipping_path + "PVOUT_clip.tif")

print("Clipping complete")

####################### PROXIMITY ##############################################
proximity(rasterizing_path + "substations.tif", proximity_path + 'substations_proximity.tif')
proximity(rasterizing_path +"roads.tif", proximity_path + 'roads_proximity.tif')
proximity(rasterizing_path + "main_roads.tif", proximity_path + 'main_roads_proximity.tif')
proximity(rasterizing_path +"protected_area.tif", proximity_path + 'protected_area_proximity.tif')
proximity(rasterizing_path + "waterbodies.tif", proximity_path + 'waterbodies_proximity.tif')

print("Proximity complete")
