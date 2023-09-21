"""
Created by Kimberly Mason
November 2022

Modified by Chungkang Choi
September 2023

Description: Performs a site suitability ranking
"""
import numpy as np
from shapely.geometry import box
from osgeo import ogr
import rasterio
import warnings
from rasterstats import zonal_stats
import pandas as pd

from settings import *
from custom_functions import *

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message="Setting nodata to -999; specify nodata explicitly")
warnings.filterwarnings("ignore", message="Column names longer than 10 ")

####################### FILE PATHS #############################################
data_download_path = PATH + PROJECT + "01_data_download\\"
filtering_path = PATH + PROJECT + "02_filtering\\"
rasterizing_path = PATH + PROJECT + "03_rasterizing\\"
exclusion_path = PATH + PROJECT + "04_exclusion\\"
clipping_path = PATH + PROJECT + "05_clipping\\"
proximity_path = PATH + PROJECT + "06_proximity\\"
weighting_path = PATH + PROJECT + "07_weighting\\"

fp_boundary_tif = rasterizing_path + "boundary.tif"
fp_land = "Data_Sources\\Land_cover\\C3S-LC-L4-LCCS-Map-300m-P1Y-2020-v2.1.1.nc"

shp_driver = ogr.GetDriverByName("ESRI Shapefile")
boundary_data = shp_driver.Open(data_download_path + "boundary.shp")
boundary = boundary_data.GetLayer()

x_min, x_max, y_min, y_max = boundary.GetExtent()
x_res = int((x_max - x_min) / PIXEL_SIZE)
y_res = int((y_max - y_min) / PIXEL_SIZE)
bbox = box(x_min, y_min, x_max, y_max)

exclusion = rasterio.open(exclusion_path + "exclusion.tif")

####################### WEIGHTING ##############################################

print("Starting weighting")

### DSM ###
#worst day 180 60 altitude, 115 10, 245 10
#https://www.timeanddate.com/sun/@1227604?month=12\&year=2022
raster_dsm = rasterio.open(clipping_path + "DSM_clip.tif")
dsm = raster_dsm.read(1)
if HEMISPHERE == "N":
    hill = hillshade(dsm, 180, 60)
else:
    hill = hillshade(dsm, 0, 60)

pixel_size_x = (x_max - x_min) / len(dsm[0])
pixel_size_y = (y_max - y_min) / len(dsm)

save_raster(hill, len(hill[0]), len(hill), pixel_size_x, pixel_size_y, weighting_path + "dsm_hillshade.tif", False, fp_boundary_tif, x_min, y_max)

raster_hill = rasterio.open(weighting_path + "dsm_hillshade.tif")
hill_class = raster_hill.read(1)
hill_class[np.where(hill_class < 100)] = 100
hill_class = (9 * ((hill_class - 100) / (255 - 100))) + 1

save_raster(hill_class, raster_dsm.shape[1], raster_dsm.shape[0], pixel_size_x, pixel_size_y, weighting_path + "dsm_class.tif", False, fp_boundary_tif, x_min, y_max)

y_factor = exclusion.shape[0] / len(hill_class)
x_factor = exclusion.shape[1] / len(hill_class[0])
resize_raster(weighting_path + "dsm_class.tif",x_factor, y_factor, weighting_path + "weight_dsm.tif")

### land cover ###
get_landcover(fp_land, x_min, y_min, x_max, y_max, fp_boundary_tif, EPSG, weighting_path + "landcover.tif")

raster_land = rasterio.open(weighting_path + "landcover.tif")
land = raster_land.read(1)

category_2 = np.array([160, 170, 180, 190, 220]) # urban area
category_5 = np.array([0,10,11,20,30, 40, 50, 60, 61, 62, 70, 71, 72, 80, 81, 82, 90, 100, 110, 120, 121, 122, 140]) # cropland, tree
category_10 = np.array([130, 150, 152, 153, 200, 210]) # grassland, bare area, water body

# Get the indices of array elements
land[np.isin(land, category_2)] = 2
land[np.isin(land, category_5)] = 5
land[np.isin(land, category_10)] = 10

pixel_size_x = (x_max - x_min) / len(land[0])
pixel_size_y = (y_max - y_min) / len(land)
save_raster(land, len(land[0]), len(land), pixel_size_x, pixel_size_y, weighting_path + "landcover_class.tif", False, fp_boundary_tif, x_min, y_max)

y_factor = exclusion.shape[0] / len(land)
x_factor = exclusion.shape[1] / len(land[0])
resize_raster(weighting_path + "landcover_class.tif", x_factor, y_factor, weighting_path + "weight_land.tif")

### GHI ###
raster_ghi = rasterio.open(clipping_path + "ghi_clip.tif")
ghi = raster_ghi.read(1)
ghi[np.where(ghi == -32768)] = (-(2057 - 1570) / 9) + 1570
ghi = (9 * (ghi - 1570) / (2057 - 1570)) + 1

pixel_size_x = (x_max - x_min) / len(ghi[0])
pixel_size_y = (y_max - y_min) / len(ghi)
save_raster(ghi, len(ghi[0]), len(ghi), pixel_size_x, pixel_size_y, weighting_path + "ghi_class.tif", False, fp_boundary_tif, x_min, y_max)

y_factor = exclusion.shape[0] / len(ghi)
x_factor = exclusion.shape[1] / len(ghi[0])
resize_raster(weighting_path + "ghi_class.tif", x_factor, y_factor, weighting_path + "weight_ghi.tif")

### substation, road, protected areas ###
# substation, raster rater 읽기
proximity(rasterizing_path + "substation.tif", proximity_path + 'substation_proximity.tif')
proximity(rasterizing_path +"roads.tif", proximity_path + 'roads_proximity.tif')
proximity(rasterizing_path +"protected_area.tif", proximity_path + 'protected_area_proximity.tif')

substation_proximity = rasterio.open(proximity_path + "substation_proximity.tif")
substation = substation_proximity.read(1)
substation[np.where(substation > 15000)] = 15000
substation = abs(((9 * (substation / 15000)) + 1) - 10) + 1
save_raster(substation, x_res, y_res, PIXEL_SIZE, PIXEL_SIZE, weighting_path + "weight_substation.tif", False, fp_boundary_tif, x_min, y_max)

roads_proximity = rasterio.open( proximity_path+ "roads_proximity.tif")
roads = roads_proximity.read(1)
roads[np.where(roads > 5000)] = 5000
roads = abs(((9 * (roads / 5000)) + 1) - 10) + 1
save_raster(roads, x_res, y_res, PIXEL_SIZE, PIXEL_SIZE, weighting_path + "weight_roads.tif", False, fp_boundary_tif, x_min, y_max)

protected_area_proximity = rasterio.open(proximity_path + "protected_area_proximity.tif")
protected_area = protected_area_proximity.read(1)
protected_area[np.where(protected_area > 15000)] = 15000
protected_area = (9 * (protected_area / 15000)) + 1
save_raster(protected_area, x_res, y_res, PIXEL_SIZE, PIXEL_SIZE, weighting_path + "weight_protected_area.tif", False, fp_boundary_tif, x_min, y_max)

### wind ###
raster_wind = rasterio.open(clipping_path + "wind_clip.tif")
wind = raster_wind.read(1)
wind = 10 - (10 * (wind - 0) / (10.7 - 0))
pixel_size_wind_x = (x_max - x_min) / len(wind[0])
pixel_size_wind_y = (y_max - y_min) / len(wind)
save_raster(wind, x_res, y_res, pixel_size_wind_x, pixel_size_wind_y, weighting_path + "weight_wind.tif", False, fp_boundary_tif, x_min, y_max)


raster_solar = rasterio.open(weighting_path + "weight_ghi.tif")
raster_wind = rasterio.open(weighting_path +  "weight_wind.tif")
raster_land = rasterio.open(weighting_path +  "weight_land.tif")
raster_roads = rasterio.open(weighting_path +  "weight_roads.tif")
raster_substation = rasterio.open(weighting_path +  "weight_substation.tif")
raster_dsm = rasterio.open(weighting_path +  "weight_dsm.tif")
raster_protected = rasterio.open(weighting_path +  "weight_protected_area.tif")
exclusion = rasterio.open(exclusion_path +  "exclusion.tif")

r1 = raster_solar.read(1)
r2 = raster_wind.read(1)
r3 = raster_land.read(1) 
r4 = raster_roads.read(1)
r5 = raster_substation.read(1)
r6 = raster_dsm.read(1)
r7 = raster_protected.read(1)
ex = exclusion.read(1)

weighting = (
                r1 * GHI_WEIGHT + \
                r2 * WIND_WEIGHT + \
                r3 * LANDCOVER_WEIGHT + \
                r4 * ROAD_WEIGHT + \
                r5 * GSS_WEIGHT + \
                r6 * DSM_WEIGHT + \
                r7 * PROTECTED_AREA_WEIGHT
            ) * ex

save_raster(weighting, x_res, y_res, PIXEL_SIZE, PIXEL_SIZE, PATH + PROJECT + "weighting.tif", False, fp_boundary_tif, x_min, y_max)



# scoring
water = gpd.read_file(data_download_path + "water.shp")
data500 = water.buffer(500)
data500.to_file(data_download_path + "water500.shp")

data500 = gpd.read_file(data_download_path + "water500.shp")

with rasterio.open(PATH + PROJECT + "weighting.tif") as src:
    affine = src.transform
    array = src.read(1)
    df_zonal_stats = pd.DataFrame(zonal_stats(data500, array, affine=affine))

# adding statistics back to original GeoDataFrame
df_zonal_stats = df_zonal_stats.add_prefix('rank_')
water_scored = pd.concat([water, df_zonal_stats], axis=1)
water_scored = water_scored.drop(['rank_count'],axis=1)
water_scored.to_file(PATH + PROJECT + "scored_water.shp")
gpd.io.file.fiona.drvsupport.supported_drivers['LIBKML'] = 'rw'
gpd.io.file.fiona.drvsupport.supported_drivers['KML'] = 'rw'
water_scored.to_file(PATH + PROJECT + "scored_water.kml", driver='KML')
water_csv = water_scored.drop(['geometry'],axis=1)
water_csv.to_csv(PATH + PROJECT + "scored_water.csv")


# idea: use the function below or overlay below to calculate the scoring only over area that is not in the exclusion zone
''' 
def good_area(x):
    good = sum(i > 6 for i in x)
    good_area = good * 0.25
    return good_area
    
water = waterbodies.overlay(protected, how='difference')
#water.plot()
water.to_file('water.shp')
'''
print("Weighting complete")