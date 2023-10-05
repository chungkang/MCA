"""
Created by Kimberly Mason
November 2022

Modified by Chungkang Choi
September 2023

Description: Performs a site cost estimation and exports heatmaps
"""

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box
from osgeo import ogr
from osgeo import gdal
import rasterio
from rasterstats import zonal_stats
import glob
import warnings

from a_settings import *

# customized functions
from src.functions.custom_functions import *

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message="Setting nodata to -999; specify nodata explicitly")
warnings.filterwarnings("ignore", message="Column names longer than 10 ")

####################### FILE PATHS #############################################
osm_data_path = PATH + "01_osm_data\\"
filtering_path = PATH + "02_filtering\\"
rasterizing_path = PATH + "03_rasterizing\\"
exclusion_path = PATH + "04_exclusion\\"
clipping_path = PATH + "05_clipping\\"
proximity_path = PATH + "06_proximity\\"
weighting_path = PATH + "07_weighting\\"
LCOE_path = PATH + "08_LCOE\\"

fp_boundary = osm_data_path + "boundary.shp"
####################### FUNCTIONS ##############################################

shp_driver = ogr.GetDriverByName("ESRI Shapefile")
boundary_data = shp_driver.Open(fp_boundary)
boundary = boundary_data.GetLayer()

shp_crs = boundary.GetSpatialRef()

x_min, x_max, y_min, y_max = boundary.GetExtent()
x_res = int((x_max - x_min) / PIXEL_SIZE)
y_res = int((y_max - y_min) / PIXEL_SIZE)

bbox = box(x_min, y_min, x_max, y_max)

####################### COST ESTIMATION ########################################

raster_protected = rasterio.open(rasterizing_path + "protected_area.tif")
raster_river = rasterio.open(rasterizing_path + "buffered_river.tif")
 
exclusion = raster_protected.read(1) * raster_river.read(1)

water = gpd.read_file(weighting_path + "scored_water.shp")

exclusion = rasterio.open(exclusion_path + "exclusion.tif")
ex = exclusion.read(1)

print("Starting cost estimation")

water_buffer50 = water.buffer(50)
water_buffer50.to_file(LCOE_path + "water_buffer50.shp")
water_ring = water_buffer50.difference(water)
water_ring.to_file(LCOE_path + "water_ring50.shp")

### roads ###
with rasterio.open(proximity_path + "main_roads_proximity.tif") as src:
    affine = src.transform
    array = src.read(1)
    df_zonal_stats = pd.DataFrame(zonal_stats(water_ring, array, affine=affine))
    
df_zonal_stats = df_zonal_stats.add_prefix('road_cost_')
water = pd.concat([water, df_zonal_stats['road_cost_mean']], axis=1)
water['road_cost_mean'] = water['road_cost_mean'] * ROAD_COST


## substations ###
with rasterio.open(proximity_path + "substation_proximity.tif") as src:
    affine = src.transform
    array = src.read(1)
    array = array[0:-1]
    df_zonal_stats = pd.DataFrame(zonal_stats(water_ring, array, affine=affine))
    
df_zonal_stats = df_zonal_stats.add_prefix('line_cost_')
water_scored = pd.concat([water, df_zonal_stats['line_cost_mean']], axis=1)
water_scored['line_cost_mean'] = water_scored['line_cost_mean'] * TRANSMISSION_COST
water_scored.to_file(LCOE_path + "water_LCOE.shp")

waterbodies_scored = water_scored.drop(['lcoe_min','lcoe_max','rank_min','rank_max'],axis=1)
waterbodies_scored.to_file(LCOE_path + "water_LCOE.kml", driver='KML')
waterbodies_csv = waterbodies_scored.drop(['geometry'],axis=1)
waterbodies_csv.to_csv(LCOE_path + "water_LCOE.csv")


### wind ###
raster_wind = rasterio.open(weighting_path + "weight_wind.tif")
wind = raster_wind.read(1)
wind[np.where(wind == 4)] = 110
wind[np.where(wind == 7)] = 105
wind[np.where(wind == 10)] = 100

save_raster(wind, x_res, y_res, PIXEL_SIZE, PIXEL_SIZE, LCOE_path + "cost_wind.tif", True, rasterizing_path + "boundary.tif", x_min, y_max)

water_proximity = rasterio.open(proximity_path + "water_proximity.tif")
water_cost = water_proximity.read(1)
water_cost[np.where(water_cost < 100)] = 0
water_cost[np.where((100 <= water_cost) & (water_cost <= 500))] = 100
water_cost[np.where(water_cost > 500)] = 110

save_raster(water_cost, x_res, y_res, PIXEL_SIZE, PIXEL_SIZE, LCOE_path + "cost_water.tif", True, rasterizing_path + "boundary.tif", x_min, y_max)


files_to_mosaic = glob.glob(osm_data_path + "GLOBathy.tif")
gdal.Warp(LCOE_path + "GLOBathy_mosaic.tif", files_to_mosaic, format="GTiff", dstSRS=f'EPSG:{EPSG}', options=["COMPRESS=LZW", "TILED=YES"])

mosaic_bathymetry = rasterio.open(LCOE_path + "GLOBathy_mosaic.tif")
bathymetry = mosaic_bathymetry.read(1)
bathymetry[np.where(bathymetry > 20)] = 200
bathymetry[np.where(bathymetry < 2)] = 0
bathymetry[np.where((2 <= bathymetry) & (bathymetry <= 10))] = 100
bathymetry[np.where((10 < bathymetry) & (bathymetry <= 20))] = 130

pixel_size_x = (x_max - x_min) / len(bathymetry[0])
pixel_size_y = (y_max - y_min) / len(bathymetry)
save_raster(bathymetry, len(bathymetry[0]), len(bathymetry), pixel_size_x, pixel_size_y, LCOE_path + "GLObathy_cost.tif", True, rasterizing_path + "boundary.tif", x_min, y_max)

src = gdal.Open(LCOE_path + "GLOBathy_cost.tif")
ulx, PIXEL_SIZE_x, xskew, uly, yskew, PIXEL_SIZE_y  = src.GetGeoTransform()
lrx = ulx + (src.RasterXSize * PIXEL_SIZE_x)
lry = uly + (src.RasterYSize * PIXEL_SIZE_y)
proj = src.GetProjection()
xres = ((lrx) - (ulx)) / PIXEL_SIZE_x
yres = ((uly) - (lry)) / -PIXEL_SIZE_y

npad = int((max(abs(x_min-ulx),abs(x_max-lrx),abs(y_min-lry),abs(y_max-uly))) / PIXEL_SIZE_x)
topad = gdal.Open(LCOE_path + "GLOBathy_cost.tif")
gt = topad.GetGeoTransform()
colortable = topad.GetRasterBand(1).GetColorTable()
data_type = topad.GetRasterBand(1).DataType
Itopad = topad.ReadAsArray()

ulx = gt[0] - gt[1] * npad
uly = gt[3] - gt[5] * npad
gt_new = (ulx, gt[1], gt[2], uly, gt[4], gt[5])
raster = np.pad(Itopad, npad, mode='constant', constant_values=0)

band = gdal.GetDriverByName('GTiff').Create(LCOE_path + "GLOBathy_pad.tif", len(raster[0]), len(raster), 1)
band.SetGeoTransform((ulx-(npad*PIXEL_SIZE_x), PIXEL_SIZE_x, 0, uly+(npad*PIXEL_SIZE_x), 0, PIXEL_SIZE_y))
band.GetRasterBand(1).WriteArray(raster)
band.SetGeoTransform(gt_new)
band.SetProjection(proj)
band.FlushCache()

clip_raster(LCOE_path + "GLOBathy_pad.tif", bbox, EPSG, LCOE_path + "GLOBathy_clip.tif")

raster_bathymetry = rasterio.open(LCOE_path + "GLOBathy_clip.tif")
bathymetry = raster_bathymetry.read(1)
y = exclusion.shape[0] / len(bathymetry)
x = exclusion.shape[1] / len(bathymetry[0])
resize_raster(LCOE_path + "GLOBathy_clip.tif", y, x, LCOE_path + "GLOBathy_cost2.tif")

raster_bathymetry = rasterio.open(LCOE_path + "GLOBathy_cost2.tif")
bathymetry = raster_bathymetry.read(1)

waterbodies_scored = gpd.read_file(LCOE_path + "water_LCOE.shp")

with rasterio.open(clipping_path + "PVOUT_clip.tif") as src:
    affine = src.transform
    array = src.read(1)
    df_zonal_stats = pd.DataFrame(zonal_stats(waterbodies_scored, array, boundless=False, affine=affine))
    
df_zonal_stats = df_zonal_stats.add_prefix('pvout_')
waterbodies_scored = pd.concat([waterbodies_scored, df_zonal_stats['pvout_mean']], axis=1)

#check this formula including pvout scaling (automate)
system = (((wind / 100) * PV_COST) + ((bathymetry / 100) * MOORINT_COST) + ((water_cost / 100) * CABLE_COST)) * 100

save_raster(system, x_res, y_res, PIXEL_SIZE, PIXEL_SIZE, LCOE_path + "system.tif", True, rasterizing_path + "boundary.tif", x_min, y_max)

bathymetry[np.where(bathymetry != 0)] = 1
water_cost[np.where(water_cost != 0)] = 1
lcoe_mask = system * bathymetry * water_cost
save_raster(lcoe_mask, x_res, y_res, PIXEL_SIZE, PIXEL_SIZE, LCOE_path + "lcoe_mask.tif", True, rasterizing_path + "boundary.tif", x_min, y_max)

with rasterio.open(LCOE_path + "lcoe_mask.tif", 'r+') as src:
    affine = src.transform
    array = src.read(1)
    df_zonal_stats = pd.DataFrame(zonal_stats(waterbodies_scored, array, affine=affine, nodata=0))

# here # adding statistics back to original GeoDataFrame
df_zonal_stats = df_zonal_stats.add_prefix('pv_per100Wp_')
waterbodies_scored = pd.concat([waterbodies_scored, df_zonal_stats['pv_per100Wp_mean']], axis=1)
waterbodies_scored = pd.concat([waterbodies_scored, df_zonal_stats['pv_per100Wp_count']], axis=1)
waterbodies_scored['pv_area_ha'] = waterbodies_scored['pv_per100Wp_count'] * 0.25
waterbodies_scored['pv_area_pixels'] = np.minimum(300, waterbodies_scored['pv_per100Wp_count'])
waterbodies_scored['pv_area_ha'] = waterbodies_scored['pv_area_pixels'] * 0.25
waterbodies_scored = waterbodies_scored.drop(['pv_per100Wp_count'],axis=1)

waterbodies_scored['cost'] = waterbodies_scored['road_cost_'] + waterbodies_scored['line_cost_'] + (waterbodies_scored['pv_area_pixels'] * (waterbodies_scored['pv_per100Wp_mean'] / 100) * 250000)

waterbodies_scored['pvout_kWh_year'] = waterbodies_scored['pv_area_pixels'] * 250 * waterbodies_scored['pvout_mean']
    
waterbodies_scored['O&M_year'] = waterbodies_scored['pv_area_pixels'] * 250 * O_M_COST

waterbodies_scored['lcoe'] = (waterbodies_scored['cost'] + (waterbodies_scored['O&M_year'] * PV_LIFETIME)) / (waterbodies_scored['pvout_kWh_year'] * PV_LIFETIME)

# O&M costs, operational years, 
lcoe = rasterio.open(LCOE_path + "lcoe_mask.tif", nodata = 0)
lcoe_data = lcoe.read(1)

minval = np.min(lcoe_data[np.nonzero(lcoe_data)])
maxval = np.max(lcoe_data[np.nonzero(lcoe_data)])

lcoe_data[np.where(lcoe_data == 0)] = (-5 * (maxval - minval) / -4) + minval
lcoe_data = (-4 * (lcoe_data - minval) / (maxval - minval)) + 5

rank = rasterio.open(weighting_path + "weighting.tif")
rank_data = rank.read(1)

final = (rank_data + lcoe_data) * ex
save_raster(final, x_res, y_res, PIXEL_SIZE, PIXEL_SIZE, LCOE_path + "final.tif", True, rasterizing_path + "boundary.tif", x_min, y_max)

with rasterio.open(LCOE_path + "final.tif", 'r+') as src:
    affine = src.transform
    array = src.read(1)
    df_zonal_stats = pd.DataFrame(zonal_stats(waterbodies_scored, array, affine=affine))

# adding statistics back to original GeoDataFrame
df_zonal_stats = df_zonal_stats.add_prefix('final_')
waterbodies_scored = pd.concat([waterbodies_scored, df_zonal_stats['final_mean']], axis=1)

waterbodies_scored.to_file(LCOE_path + "water_lcoe.shp")
waterbodies_scored.to_file(LCOE_path + "water_lcoe.kml", driver='KML')
waterbodies_csv = waterbodies_scored.drop(['geometry'],axis=1)
waterbodies_csv.to_csv(LCOE_path + "water_lcoe.csv")

print("Cost estimation complete")
