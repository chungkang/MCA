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

from settings import *

# customized functions
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
LCOE_path = PATH + PROJECT + "08_LCOE\\"

fp_boundary = data_download_path + "boundary.shp"
# fp_substationcost = Path+Project+"\\In_Data\\Transmission\\gsscost.tif"
fp_main_roads = LCOE_path + "main_roads.shp"
fp_bathymetry = data_download_path + "GLOBathy.tif"

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
raster_rivers = rasterio.open(rasterizing_path + "rivers.tif")
 
exclusion = raster_protected.read(1) * raster_rivers.read(1)

water = gpd.read_file(filtering_path + "water.shp")

exclusion = rasterio.open(exclusion_path + "exclusion.tif")
ex = exclusion.read(1)

print("Starting cost estimation")

water_buffer50 = water.buffer(50)
water_buffer50.to_file(LCOE_path + "water_buffer50.shp")
water_ring = water_buffer50.difference(water)
water_ring.to_file(LCOE_path + "waterdonut.shp")

### roads ###
b_custom_functions.rasterize(fp_main_roads, 'Processing\\main_roads_r', shp_crs, PIXEL_SIZE, x_res, y_res, 1, 0, x_min, y_max)
b_custom_functions.proximity(Path+Project+"\\Out_Data\\Processing\\main_roads_r.tif", 'Processing\\main_roads_custom_functions.proximity.tif')

with rasterio.open(Path+Project+"\\Out_Data\\Processing\\main_roads_custom_functions.proximity.tif") as src:
    affine = src.transform
    array = src.read(1)
    df_zonal_stats = pd.DataFrame(zonal_stats(waterbodies_ring, array, affine=affine))
    
df_zonal_stats = df_zonal_stats.add_prefix('road_cost_')
waterbodies_scored = pd.concat([waterbodies_scored, df_zonal_stats['road_cost_mean']], axis=1)
waterbodies_scored['road_cost_mean'] = waterbodies_scored['road_cost_mean'] * road_cost


### substations ###
# with rasterio.open(fp_substationcost) as src:
#     affine = src.transform
#     array = src.read(1)
#     array = array[0:-1]
#     df_zonal_stats = pd.DataFrame(zonal_stats(waterbodies_ring, array, affine=affine))
    
# df_zonal_stats = df_zonal_stats.add_prefix('line_cost_')
# waterbodies_scored = pd.concat([waterbodies_scored, df_zonal_stats['line_cost_mean']], axis=1)
# waterbodies_scored['line_cost_mean'] = waterbodies_scored['line_cost_mean'] * transmission_cost
# waterbodies_scored.to_file(Path+Project+"\\Out_Data\\waterbodies_lcoe.shp")


#waterbodies_scored = waterbodies_scored.drop(['lcoe_min','lcoe_max','rank_min','rank_max'],axis=1)
#waterbodies_scored.to_file(Path+Project+"\\waterbodies_lcoe.kml", driver='KML')
#waterbodies_csv = waterbodies_scored.drop(['geometry'],axis=1)
#waterbodies_csv.to_csv(Path+Project+"\\waterbodies_lcoe.csv")


### wind ###
raster_wind = rasterio.open(Path+Project+"\\Out_Data\\weight_wind.tif")
wind = raster_wind.read(1)
wind[np.where(wind == 4)] = 110
wind[np.where(wind == 7)] = 105
wind[np.where(wind == 10)] = 100

b_custom_functions.save_raster(wind, x_res, y_res, PIXEL_SIZE, PIXEL_SIZE, "cost_wind.tif", 
            True, "Processing\\r_recreation.tif", x_min, y_max)
#show(wind)


b_custom_functions.rasterize(Path+Project+"\\Out_Data\\waterbodies.shp", 'Processing\\waterbodies_r', shp_crs, 
          PIXEL_SIZE, x_res, y_res, 0, 1, x_min, y_max)

b_custom_functions.proximity(Path+Project+"\\Out_Data\\Processing\\waterbodies_r.tif", 'Processing\\cost_waterbodies.tif')

raster_water = rasterio.open(Path+Project+"\\Out_Data\\Processing\\cost_waterbodies.tif")
water_cost = raster_water.read(1)
water_cost[np.where(water_cost < 100)] = 0
water_cost[np.where((100 <= water_cost) & (water_cost <= 500))] = 100
water_cost[np.where(water_cost > 500)] = 110

b_custom_functions.save_raster(water_cost, x_res, y_res, PIXEL_SIZE, PIXEL_SIZE, "cost_water.tif", 
            True, "Processing\\r_recreation.tif", x_min, y_max)
#show(water_cost)


#files_string = " ".join(files_to_mosaic)
#command = f"gdal_merge.py -o {Path}+{Project}+\\Out_Data\\Bathymetry_Mosaic.tif -of gtiff " + files_string
#print(os.popen(command).read())

files_to_mosaic = glob.glob(fp_bathymetry)
g = gdal.Warp(Path+Project+"\\Out_Data\\Processing\\bathymetry.tif", files_to_mosaic, format="GTiff",
              dstSRS=f'EPSG:{epsg}', options=["COMPRESS=LZW", "TILED=YES"])
g = None # Close file and flush to disk

raster_bathymetry = rasterio.open(Path+Project+"\\Out_Data\\Processing\\bathymetry.tif")
bathymetry = raster_bathymetry.read(1)
bathymetry[np.where(bathymetry > 20)] = 200
bathymetry[np.where(bathymetry < 2)] = 0
bathymetry[np.where((2 <= bathymetry) & (bathymetry <= 10))] = 100
bathymetry[np.where((10 < bathymetry) & (bathymetry <= 20))] = 130

PIXEL_SIZE_x = (x_max - x_min) / len(bathymetry[0])
PIXEL_SIZE_y = (y_max - y_min) / len(bathymetry)
b_custom_functions.save_raster(bathymetry, len(bathymetry[0]), len(bathymetry), PIXEL_SIZE_x, PIXEL_SIZE_y, 
            "Processing\\bathy_cost.tif", True, "Processing\\bathymetry.tif", x_min, y_max)

src = gdal.Open(Path+Project+"\\Out_Data\\Processing\\bathy_cost.tif")
ulx, PIXEL_SIZE_x, xskew, uly, yskew, PIXEL_SIZE_y  = src.GetGeoTransform()
lrx = ulx + (src.RasterXSize * PIXEL_SIZE_x)
lry = uly + (src.RasterYSize * PIXEL_SIZE_y)
proj = src.GetProjection()
xres = ((lrx) - (ulx)) / PIXEL_SIZE_x
yres = ((uly) - (lry)) / -PIXEL_SIZE_y

npad = int((max(abs(x_min-ulx),abs(x_max-lrx),abs(y_min-lry),abs(y_max-uly))) / PIXEL_SIZE_x)
topad = gdal.Open(Path+Project+"\\Out_Data\\Processing\\bathy_cost.tif")
gt = topad.GetGeoTransform()
colortable = topad.GetRasterBand(1).GetColorTable()
data_type = topad.GetRasterBand(1).DataType
Itopad = topad.ReadAsArray()

ulx = gt[0] - gt[1] * npad
uly = gt[3] - gt[5] * npad
gt_new = (ulx, gt[1], gt[2], uly, gt[4], gt[5])
raster = np.pad(Itopad, npad, mode='constant', constant_values=0)

band = gdal.GetDriverByName('GTiff').Create(Path+Project+"\\Out_Data\\Processing\\bathy_pad.tif", 
                                        len(raster[0]), len(raster), 1)
band.SetGeoTransform((ulx-(npad*PIXEL_SIZE_x), PIXEL_SIZE_x, 0, uly+(npad*PIXEL_SIZE_x), 
                      0, PIXEL_SIZE_y))
band.GetRasterBand(1).WriteArray(raster)
band.SetGeoTransform(gt_new)
band.SetProjection(proj)
band.FlushCache()

b_custom_functions.clip_raster(Path+Project+"\\Out_Data\\Processing\\bathy_pad.tif", bbox, epsg, 
            Path+Project+"\\Out_Data\\Processing\\bathy_clip.tif")

raster_bathymetry = rasterio.open(Path+Project+"\\Out_Data\\Processing\\bathy_clip.tif")
bathymetry = raster_bathymetry.read(1)
y = exclusion.shape[0] / len(bathymetry)
x = exclusion.shape[1] / len(bathymetry[0])
b_custom_functions.resize_raster(Path+Project+"\\Out_Data\\Processing\\bathy_clip.tif",y,x,
              Path+Project+"\\Out_Data\\cost_bathymetry.tif")

raster_bathymetry = rasterio.open(Path+Project+"\\Out_Data\\cost_bathymetry.tif")
bathymetry = raster_bathymetry.read(1)
#show(bathymetry)


waterbodies_scored = gpd.read_file(Path+Project+"\\Out_Data\\waterbodies_lcoe.shp")

#custom_functions.clip_raster(fp_pvout, bbox, epsg, Path+Project+"\\Out_Data\\Processing\\pvout_clip.tif")
#waterbodies_4326 = waterbodies_scored.to_crs(epsg=epsg)
with rasterio.open(Path+Project+"\\In_Data\\Solar\\PVOUT_local.tif") as src:
    affine = src.transform
    array = src.read(1)
    df_zonal_stats = pd.DataFrame(zonal_stats(waterbodies_scored, array, boundless=False, affine=affine))
    
df_zonal_stats = df_zonal_stats.add_prefix('pvout_')
waterbodies_scored = pd.concat([waterbodies_scored, df_zonal_stats['pvout_mean']], axis=1)
#waterbodies_scored['pvout_perkWp_year'] = waterbodies_scored['pvout_mean'] * pv_tariff
#waterbodies_scored = waterbodies_scored.drop(['pvout_mean'],axis=1)
#waterbodies_scored.to_file(Path+Project+"\\waterbodies_pvout.shp")
#waterbodies_scored = waterbodies_scored.drop(['geometry'],axis=1)
#waterbodies_scored.to_csv(Path+Project+"\\waterbodies_pvout.csv")
#y = exclusion.shape[0] / len(pvout)
#x = exclusion.shape[1] / len(pvout[0])
#custom_functions.resize_raster(Path+Project+"\\Out_Data\\Processing\\pvout_clip.tif",y,x,
              #Path+Project+"\\Out_Data\\cost_pvout.tif")

#check this formula including pvout scaling (automate)
system = (((wind / 100) * pv_cost) + ((bathymetry / 100) * mooring_cost) + ((water_cost / 100) * cable_cost)) * 100
#show(system)
b_custom_functions.save_raster(system, x_res, y_res, PIXEL_SIZE, PIXEL_SIZE, "system.tif", True, "Processing\\r_recreation.tif", x_min, y_max)

bathymetry[np.where(bathymetry != 0)] = 1
water_cost[np.where(water_cost != 0)] = 1
lcoe_mask = system * bathymetry * water_cost
b_custom_functions.save_raster(lcoe_mask, x_res, y_res, PIXEL_SIZE, PIXEL_SIZE, "lcoe_mask.tif", 
            True, "Processing\\r_recreation.tif", x_min, y_max)

with rasterio.open(Path+Project+"\\Out_Data\\lcoe_mask.tif", 'r+') as src:
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

waterbodies_scored['cost'] = waterbodies_scored['road_cost_'] + \
    waterbodies_scored['line_cost_'] + (waterbodies_scored['pv_area_pixels'] * \
        (waterbodies_scored['pv_per100Wp_mean'] / 100) * 250000)

waterbodies_scored['pvout_kWh_year'] = waterbodies_scored['pv_area_pixels'] * 250 * \
    waterbodies_scored['pvout_mean']
    
waterbodies_scored['O&M_year'] = waterbodies_scored['pv_area_pixels'] * 250 * o_m_cost

waterbodies_scored['lcoe'] = (waterbodies_scored['cost'] + \
                              (waterbodies_scored['O&M_year'] * pv_lifetime)) / \
    (waterbodies_scored['pvout_kWh_year'] * pv_lifetime)
    
# O&M costs, operational years, 

lcoe = rasterio.open(Path+Project+"\\Out_Data\\lcoe_mask.tif", nodata = 0)
lcoe_data = lcoe.read(1)

minval = np.min(lcoe_data[np.nonzero(lcoe_data)])
maxval = np.max(lcoe_data[np.nonzero(lcoe_data)])

lcoe_data[np.where(lcoe_data == 0)] = (-5 * (maxval - minval) / -4) + minval
lcoe_data = (-4 * (lcoe_data - minval) / (maxval - minval)) + 5

rank = rasterio.open(Path+Project+"\\Out_Data\\weighting.tif")
rank_data = rank.read(1)

final = (rank_data + lcoe_data) * ex
b_custom_functions.save_raster(final, x_res, y_res, PIXEL_SIZE, PIXEL_SIZE, "final.tif", 
            True, "Processing\\r_recreation.tif", x_min, y_max)

with rasterio.open(Path+Project+"\\Out_Data\\final.tif", 'r+') as src:
    affine = src.transform
    array = src.read(1)
    df_zonal_stats = pd.DataFrame(zonal_stats(waterbodies_scored, array, affine=affine))

# adding statistics back to original GeoDataFrame
df_zonal_stats = df_zonal_stats.add_prefix('final_')
waterbodies_scored = pd.concat([waterbodies_scored, df_zonal_stats['final_mean']], axis=1)

waterbodies_scored.to_file(Path+Project+"\\Out_Data\\waterbodies_lcoe.shp")
#waterbodies_lcoe = waterbodies_lcoe.drop(['lcoe_min','lcoe_max','rank_min','rank_max'],axis=1)
waterbodies_scored.to_file(Path+Project+"\\waterbodies_lcoe.kml", driver='KML')
waterbodies_csv = waterbodies_scored.drop(['geometry'],axis=1)
waterbodies_csv.to_csv(Path+Project+"\\waterbodies_lcoe.csv")

print("Cost estimation complete")
