# -*- coding: utf-8 -*-
"""
Created by Kimberly Mason
November 2022

Description: Performs a site suitability ranking, cost estimation and exports heatmaps
"""

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box, shape
import fiona
from fiona.crs import from_epsg
import osgeo.osr as osr
from osgeo import ogr
from osgeo import gdal
import rasterio
from rasterio.mask import mask
from rasterio.plot import show
from rasterio.enums import MergeAlg
from rasterstats import zonal_stats
from netCDF4 import Dataset
from pyproj import Proj, transform
import matplotlib.pyplot as plt
import json
import glob
import warnings

from a_settings import *

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message="Setting nodata to -999; specify nodata explicitly")
warnings.filterwarnings("ignore", message="Column names longer than 10 ")

####################### FILE PATHS #############################################

fp_boundary = Path+Project+"\\In_Data\\Boundary\\boundary.shp"

fp_water = Path+Project+"\\In_Data\\Waterbodies\\waterbodies.shp"

fp_protected = Path+Project+"\\In_Data\\Protected\\"
a = "WDPA_WDOECM_May2022_Public_LKA_shp_0\\WDPA_WDOECM_May2022_Public_LKA_shp-polygons.shp"
b = "WDPA_WDOECM_May2022_Public_LKA_shp_1\\WDPA_WDOECM_May2022_Public_LKA_shp-polygons.shp"
c = "WDPA_WDOECM_May2022_Public_LKA_shp_2\\WDPA_WDOECM_May2022_Public_LKA_shp-polygons.shp"
fp_recreation = Path+Project+"\\In_Data\\Recreation\\recreation_buffered.shp"
fp_military = Path+Project+"\\In_Data\\Military\\military_buffered.shp"
fp_rivers = Path+Project+"\\In_Data\\Current\\current_buffered.shp"

fp_dsm = Path+Project+"\\In_Data\\DSM\\output_AW3D30.tif"
fp_ghi = Path+Project+"\\In_Data\\Solar\\GHI.tif"
fp_wind = Path+Project+"\\In_Data\\Wind\\zones.tif"
fp_endangered = Path+Project+"\\In_Data\\Endangered\\endangered.shp"
fp_land = Path[:-10]+"\\Data_Sources\\Land_cover\\C3S-LC-L4-LCCS-Map-300m-P1Y-2020-v2.1.1.nc"
fp_tourism = Path+Project+"\\In_Data\\Tourism\\tourism.shp"
fp_roads = Path+Project+"\\In_Data\\Roads\\roads.shp"
fp_substations = Path+Project+"\\In_Data\\Transmission\\substations.shp"

fp_pvout = Path+Project+"\\In_Data\\Solar\\PVOUT.tif"
fp_substationcost = Path+Project+"\\In_Data\\Transmission\\gsscost.tif"
fp_main_roads = Path+Project+"\\In_Data\\Roads\\main_roads.shp"
fp_bathymetry = Path+Project+"\\In_Data\\Bathymetry\\*_bathymetry.tif"

####################### FUNCTIONS ##############################################

shp_driver = ogr.GetDriverByName("ESRI Shapefile")
boundary_data = shp_driver.Open(fp_boundary)
boundary = boundary_data.GetLayer()

shp_crs = boundary.GetSpatialRef()

x_min, x_max, y_min, y_max = boundary.GetExtent()
x_res = int((x_max - x_min) / pixel_size)
y_res = int((y_max - y_min) / pixel_size)

bbox = box(x_min, y_min, x_max, y_max)


def rasterize(shapefile, raster_name, shp_crs, pixel_size, x_res, y_res, no, ya):
    
    shp_driver = ogr.GetDriverByName("ESRI Shapefile")
    shp_data = shp_driver.Open(shapefile)
    shp = shp_data.GetLayer()

    no_data_value = no
    target_r = gdal.GetDriverByName('GTiff').Create(Path+Project+"\\Out_Data\\"+raster_name+".tif", 
                                                    x_res, y_res, 1)
    target_r.SetGeoTransform((x_min, pixel_size, 0, y_max, 0, -pixel_size))
    band = target_r.GetRasterBand(1)
    band.Fill(no_data_value)

    shp_crs.ImportFromEPSG(int(shp_crs.GetAuthorityCode(None)))
    target_r.SetProjection(shp_crs.ExportToWkt())

    gdal.RasterizeLayer(target_r, [1], shp, None, None, burn_values=[ya], options=['all'])
    band.FlushCache()
    
    
def save_raster(array, x, y, pixel_size_x, pixel_size_y, out_name, geotrans, template):
    
    tif = gdal.Open(Path+Project+"\\Out_Data\\"+template)
    
    band = gdal.GetDriverByName('GTiff').Create(Path+Project+"\\Out_Data\\"+out_name, 
                                            x, y, 1)
    band.SetGeoTransform((x_min, pixel_size_x, 0, y_max, 0, -pixel_size_y))
    band.GetRasterBand(1).WriteArray(array)

    if geotrans == True:
        geotrans=tif.GetGeoTransform()
        band.SetGeoTransform(geotrans)
        
    proj = tif.GetProjection()
    band.SetProjection(proj)
    band.FlushCache()


def clip_raster(raster, bbox, crs, out):

    raster_r = rasterio.open(raster)
    new = gpd.GeoDataFrame({'geometry':bbox}, index=[0], crs=from_epsg(crs))
    new = new.to_crs(crs = raster_r.crs.data)

    coords = [json.loads(new.to_json())['features'][0]['geometry']]

    out_img, out_transform = mask(dataset=raster_r, shapes=coords, crop=True)
    out_meta = raster_r.meta.copy()
    epsg_code = int(raster_r.crs.data['init'][5:])
    out_meta.update({"driver": "GTiff",
                     "height": out_img.shape[1],
                     "width": out_img.shape[2],
                     "transform": out_transform,
                     "crs": epsg_code})
    
    with rasterio.open(out, "w", **out_meta) as dest:
            #dest.nodata = 0
            dest.write(out_img)


def hillshade(array, azimuth, angle_altitude):
    azimuth = 360.0 - azimuth 
    
    x, y = np.gradient(array)
    slope = np.pi/2. - np.arctan(np.sqrt(x*x + y*y))
    aspect = np.arctan2(-x, y)
    azimuthrad = azimuth*np.pi/180.
    altituderad = angle_altitude*np.pi/180.
 
    shaded = np.sin(altituderad)*np.sin(slope) + np.cos(altituderad)*np.cos(slope)*np.cos((azimuthrad - np.pi/2.) - aspect)
    
    return 255*(shaded + 1)/2


def get_landcover(fp, x_min, y_min, x_max, y_max, bound, epsg): # extracts land cover for the project area from the global netCDF
    
    land_nc = Dataset(fp)

    p0 = Proj('epsg:4326', preserve_units=False)
    p1 = Proj(f'epsg:{epsg}', preserve_units=False)

    x_world1, y_world1 = transform(p1, p0, x_min, y_min)
    x_world2, y_world2 = transform(p1, p0, x_max, y_max)

    latbounds = [x_world1, x_world2]
    lonbounds = [y_world1, y_world2]
    lats = land_nc.variables['lat'][:] 
    lons = land_nc.variables['lon'][:]

    latli = np.argmin(np.abs(lats - latbounds[0]))
    latui = np.argmin(np.abs(lats - latbounds[1])) 

    lonli = np.argmin(np.abs(lons - lonbounds[0]))
    lonui = np.argmin(np.abs(lons - lonbounds[1]))  

    subset = land_nc.variables['lccs_class'][ : , latui:latli, lonli:lonui] 

    pixel_size_x = (x_max - x_min) / len(subset[0][0])
    pixel_size_y = (y_max - y_min) / len(subset[0])
    
    save_raster(subset[0], len(subset[0][0]), len(subset[0]), pixel_size_x, 
                pixel_size_y, "Processing\\landcover.tif", False, "Processing\\r_recreation.tif")
    

def proximity(tif, name):
    src_ds = gdal.Open(tif)
    srcband=src_ds.GetRasterBand(1)
    
    drv = gdal.GetDriverByName('GTiff')
    dst_ds = drv.Create( Path+Project+"\\Out_Data\\"+name,
                         src_ds.RasterXSize, src_ds.RasterYSize, 1,
                         gdal.GetDataTypeByName('Float32'))
    
    dst_ds.SetGeoTransform(src_ds.GetGeoTransform())
    dst_ds.SetProjection(src_ds.GetProjectionRef())
    
    dstband = dst_ds.GetRasterBand(1)
        
    gdal.ComputeProximity(srcband,dstband,["VALUES='0'","DISTUNITS=GEO"])
    srcband = None
    dstband = None
    src_ds = None
    dst_ds = None
    

def resize_raster(raster, y_factor, x_factor, out):
    # Open raster and get band
    in_ds = gdal.Open(raster)
    in_band = in_ds.GetRasterBand(1)

    # Multiply output size by 3 
    out_rows = int(in_band.YSize * y_factor)
    out_columns = int(in_band.XSize * x_factor)

    # Create new data source (raster)
    gtiff_driver = gdal.GetDriverByName('GTiff')
    out_ds = gtiff_driver.Create(out, out_columns, out_rows)
    out_ds.SetProjection(in_ds.GetProjection())
    geotransform = list(in_ds.GetGeoTransform())

    # Edit the geotransform so pixels are one-sixth previous size
    geotransform[1] /= y_factor
    geotransform[5] /= x_factor
    out_ds.SetGeoTransform(geotransform)
    
    data = in_band.ReadAsArray(buf_xsize=out_columns, buf_ysize=out_rows)  # Specify a larger buffer size when reading data
    out_band = out_ds.GetRasterBand(1)
    out_band.WriteArray(data)

    out_band.FlushCache()
    #out_band.ComputeStatistics(False)
    #out_ds.BuildOverviews('average', [2, 4, 8, 16, 32, 64])

    del out_ds

####################### FILTERING ##############################################

waterbodies = gpd.read_file(fp_water)
waterbodies['area_ha'] = (waterbodies.area/10000)
waterbodies = waterbodies.loc[waterbodies['area_ha']>min_area]
waterbodies.to_file(Path+Project+"\\Out_Data\\waterbodies.shp")
#waterbodies.plot()
print("Filtering complete")

####################### EXCLUSION ##############################################

# needs to be adapted to allow any number of shapefile inputs for the protected areas from Protected Planet
protected_0 = gpd.read_file(fp_protected+a)
protected_1 = gpd.read_file(fp_protected+b)
protected_2 = gpd.read_file(fp_protected+c)
protected = protected_0.append(protected_1, ignore_index=True)
protected = protected.append(protected_2, ignore_index=True)
protected = protected.to_crs(epsg=epsg)
protected.to_file(Path+Project+"\\Out_Data\\Processing\\protected.shp")

rasterize(Path+Project+"\\Out_Data\\Processing\\protected.shp", "Processing\\r_protected", 
          shp_crs, pixel_size, x_res, y_res, 1, 0)
rasterize(fp_recreation, 'Processing\\r_recreation', shp_crs, 
          pixel_size, x_res, y_res, 1, 0)
rasterize(fp_military, 'Processing\\r_military', shp_crs, 
          pixel_size, x_res, y_res, 1, 0)
rasterize(fp_rivers, 'Processing\\r_rivers', shp_crs, 
          pixel_size, x_res, y_res, 1, 0)

raster_protected = rasterio.open(Path+Project+"\\Out_Data\\Processing\\r_protected.tif")
raster_recreation = rasterio.open(Path+Project+"\\Out_Data\\Processing\\r_recreation.tif")
raster_military = rasterio.open(Path+Project+"\\Out_Data\\Processing\\r_military.tif")
raster_rivers = rasterio.open(Path+Project+"\\Out_Data\\Processing\\r_rivers.tif")

r1 = raster_protected.read(1)
r2 = raster_recreation.read(1)
r3 = raster_military.read(1)
r4 = raster_rivers.read(1) 
exclusion = r1 * r2 * r3 * r4

save_raster(exclusion, x_res, y_res, pixel_size, pixel_size, "exclusion.tif", 
            True, "Processing\\r_recreation.tif")

#show(exclusion)
print("Exclusion complete")

####################### WEIGHTING ##############################################

print("Starting weighting")

### DSM ###
clip_raster(fp_dsm, bbox, epsg, Path+Project+"\\Out_Data\\Processing\\dsm_clip.tif")

#worst day 180 60 altitude, 115 10, 245 10
#https://www.timeanddate.com/sun/@1227604?month=12\&year=2022

raster_dsm = rasterio.open(Path+Project+"\\Out_Data\\Processing\\dsm_clip.tif")
dsm = raster_dsm.read(1)
if hemisphere == "N":
    hill = hillshade(dsm, 180, 60)
else:
    hill = hillshade(dsm, 0, 60)

pixel_size_x = (x_max - x_min) / len(hill[0])
pixel_size_y = (y_max - y_min) / len(hill)
save_raster(hill, len(hill[0]), len(hill), pixel_size_x, pixel_size_y, "Processing\\dsm_hillshade.tif", 
            False, "Processing\\r_recreation.tif")

raster_hill = rasterio.open(Path+Project+"\\Out_Data\\Processing\\dsm_hillshade.tif")
hill_class = raster_hill.read(1)
hill_class[np.where(hill_class < 100)] = 100
hill_class = (9 * ((hill_class - 100) / (255 - 100))) + 1

save_raster(hill_class, raster_dsm.shape[1], raster_dsm.shape[0], 
            pixel_size_x, pixel_size_y, "Processing\\dsm_class.tif", False, "Processing\\r_recreation.tif")

y = exclusion.shape[0] / len(hill_class)
x = exclusion.shape[1] / len(hill_class[0])
resize_raster(Path+Project+"\\Out_Data\\Processing\\dsm_class.tif",y,x,
              Path+Project+"\\Out_Data\\weight_dsm.tif")

#show(hill_class)


### land cover ###
get_landcover(fp_land, x_min, y_min, x_max, y_max, 
              Path+Project+"\\Out_Data\\Processing\\r_recreation.tif", epsg)

raster_land = rasterio.open(Path+Project+"\\Out_Data\\Processing\\landcover.tif")
land = raster_land.read(1)
land[np.where(land == 0)] = 5
land[np.where(land == 10)] = 5
land[np.where(land == 11)] = 5
land[np.where(land == 20)] = 5
land[np.where(land == 30)] = 5
land[np.where(land == 40)] = 5
land[np.where(land == 50)] = 5
land[np.where(land == 60)] = 5
land[np.where(land == 61)] = 5
land[np.where(land == 70)] = 5
land[np.where(land == 80)] = 5
land[np.where(land == 90)] = 5
land[np.where(land == 100)] = 5
land[np.where(land == 110)] = 5
land[np.where(land == 120)] = 5
land[np.where(land == 121)] = 5
land[np.where(land == 130)] = 10
land[np.where(land == 140)] = 5
land[np.where(land == 150)] = 10
land[np.where(land == 160)] = 2
land[np.where(land == 170)] = 2
land[np.where(land == 180)] = 2
land[np.where(land == 190)] = 2
land[np.where(land == 200)] = 10
land[np.where(land == 210)] = 10
land[np.where(land == 220)] = 2

pixel_size_x = (x_max - x_min) / len(land[0])
pixel_size_y = (y_max - y_min) / len(land)
save_raster(land, len(land[0]), len(land), pixel_size_x, pixel_size_y, 
            "Processing\\land_class.tif", True, "Processing\\landcover.tif")

y = exclusion.shape[0] / len(land)
x = exclusion.shape[1] / len(land[0])
resize_raster(Path+Project+"\\Out_Data\\Processing\\land_class.tif",y,x,
              Path+Project+"\\Out_Data\\weight_land.tif")

#show(land)


### GHI ###
clip_raster(fp_ghi, bbox, epsg, Path+Project+"\\Out_Data\\Processing\\ghi_clip.tif")

raster_ghi = rasterio.open(Path+Project+"\\Out_Data\\Processing\\ghi_clip.tif")
ghi = raster_ghi.read(1)
ghi[np.where(ghi == -32768)] = (-(2103 - 1430) / 9) + 1430
ghi = (9 * (ghi - 1430) / (2103 - 1430)) + 1

pixel_size_x = (x_max - x_min) / len(ghi[0])
pixel_size_y = (y_max - y_min) / len(ghi)
save_raster(ghi, len(ghi[0]), len(ghi), pixel_size_x, pixel_size_y, 
            "Processing\\ghi_class.tif", True, "Processing\\ghi_clip.tif")

y = exclusion.shape[0] / len(ghi)
x = exclusion.shape[1] / len(ghi[0])
resize_raster(Path+Project+"\\Out_Data\\Processing\\ghi_class.tif",y,x,
              Path+Project+"\\Out_Data\\weight_ghi.tif")

#show(ghi)


### substations, roads, protected areas ###
rasterize(fp_substations, 'Processing\\substations_r', shp_crs, pixel_size, x_res, y_res, 1, 0)
rasterize(fp_roads, 'Processing\\roads_r', shp_crs, pixel_size, x_res, y_res, 1, 0)

proximity(Path+Project+"\\Out_Data\\Processing\\substations_r.tif", 'Processing\\substations_proximity.tif')
proximity(Path+Project+"\\Out_Data\\Processing\\roads_r.tif", 'Processing\\roads_proximity.tif')
proximity(Path+Project+"\\Out_Data\\Processing\\r_protected.tif", 'Processing\\protected_proximity.tif')

sub_p = rasterio.open(Path+Project+"\\Out_Data\\Processing\\substations_proximity.tif")
sub = sub_p.read(1)
sub[np.where(sub > 15000)] = 15000
sub = abs(((9 * (sub / 15000)) + 1) - 10) + 1

save_raster(sub, x_res, y_res, pixel_size, pixel_size, "weight_substations.tif", 
            True, "Processing\\r_recreation.tif")

road_p = rasterio.open(Path+Project+"\\Out_Data\\Processing\\roads_proximity.tif")
road = road_p.read(1)
road[np.where(road > 5000)] = 5000
road = abs(((9 * (road / 5000)) + 1) - 10) + 1

save_raster(road, x_res, y_res, pixel_size, pixel_size, "weight_roads.tif", 
            True, "Processing\\r_recreation.tif")

pro_p = rasterio.open(Path+Project+"\\Out_Data\\Processing\\protected_proximity.tif")
pro = pro_p.read(1)
pro[np.where(pro > 15000)] = 15000
pro = (9 * (pro / 15000)) + 1

save_raster(pro, x_res, y_res, pixel_size, pixel_size, "weight_protected.tif", 
            True, "Processing\\r_recreation.tif")

#show(sub)
#show(road)
#show(pro)


### endangered ###
rasterize(fp_endangered, 'weight_endangered', shp_crs, 
          pixel_size, x_res, y_res, 10, 1)
# idea: use merge_alg=MergeAlg.add in rasterize step (define a new function for this) so that number of
# endangered species living in an area is summed.


### wind ###
raster_wind = rasterio.open(fp_wind)
wind = raster_wind.read(1)
wind = (6 * (wind - 1) / (3 - 1)) + 4

save_raster(wind, x_res, y_res, pixel_size, pixel_size, "weight_wind.tif", 
            True, "Processing\\r_recreation.tif")

#show(wind)


### tourism ###
# idea: the merge_alg=MergeAlg.add rasterize function could also be used here instead of the heatmap

ty = int(exclusion.shape[0]/100)+1
tx = int(exclusion.shape[1]/100)+1

tourism = gpd.read_file(fp_tourism)
heatmap, xedges, yedges = np.histogram2d(tourism['geometry'].x, 
                                         tourism['geometry'].y, 
                                         bins=(tx,ty),
                                         range=[[x_min, x_max],[y_min, y_max]]) 
#plt.imshow(heatmap)
heatmap = abs(((9 * (heatmap / 255)) + 1) - 10) + 1
#plt.imshow(heatmap, origin='lower')

pixel_size_y = (y_max - y_min) / ty
pixel_size_x = (x_max - x_min) / tx
#x_res = int((x_max - x_min) / pixel_size)
#y_res = int((y_max - y_min) / pixel_size)

rasterize(fp_tourism, 'Processing\\tourism_r', shp_crs, 
          pixel_size_y, len(heatmap), len(heatmap[0]), 1, 0)

# turn into function!
band = gdal.GetDriverByName('GTiff').Create(Path+Project+"\\Out_Data\\Processing\\tourism.tif", 
                                            len(heatmap), len(heatmap[0]), 1)
#heatmap = heatmap.T
heatmap = np.flip(heatmap, axis=1)
#extent = [x_min, x_max, y_max, y_min]
#plt.clf()
#plt.imshow(heatmap.T, extent=extent, origin='lower')
#plt.show()
band.GetRasterBand(1).WriteArray((heatmap.T))
tif = gdal.Open(Path+Project+"\\Out_Data\\Processing\\tourism_r.tif")

geotrans=tif.GetGeoTransform()
proj = tif.GetProjection()

band.SetGeoTransform(geotrans)
band.SetProjection(proj)
band.FlushCache()
    
y = exclusion.shape[0] / ty
x = exclusion.shape[1] / tx
resize_raster(Path+Project+"\\Out_Data\\Processing\\tourism.tif",y,x,
              Path+Project+"\\Out_Data\\Processing\\tourism_size.tif")

clip_raster(Path+Project+"\\Out_Data\\Processing\\tourism_size.tif", bbox, epsg, 
            Path+Project+"\\Out_Data\\weight_tourism.tif")

#show(heatmap.T)


raster_solar = rasterio.open(Path+Project+"\\Out_Data\\weight_ghi.tif")
raster_wind = rasterio.open(Path+Project+"\\Out_Data\\weight_wind.tif")
raster_species = rasterio.open(Path+Project+"\\Out_Data\\weight_endangered.tif")
raster_land = rasterio.open(Path+Project+"\\Out_Data\\weight_land.tif")
raster_tourism = rasterio.open(Path+Project+"\\Out_Data\\weight_tourism.tif")
raster_roads = rasterio.open(Path+Project+"\\Out_Data\\weight_roads.tif")
raster_subs = rasterio.open(Path+Project+"\\Out_Data\\weight_substations.tif")
raster_dsm = rasterio.open(Path+Project+"\\Out_Data\\weight_dsm.tif")
raster_protected = rasterio.open(Path+Project+"\\Out_Data\\weight_protected.tif")
exclusion = rasterio.open(Path+Project+"\\Out_Data\\exclusion.tif")

r1 = raster_solar.read(1)
r2 = raster_wind.read(1)
r3 = raster_species.read(1)
r4 = raster_land.read(1) 
r5 = raster_tourism.read(1)
r6 = raster_roads.read(1)
r7 = raster_subs.read(1)
r8 = raster_dsm.read(1)
r9 = raster_protected.read(1)
ex = exclusion.read(1)

weighting = (r1 * ghi_weight +  
             r2 * wind_weight + \
             r3 * endangered_weight + \
             r4 * land_weight + \
             r5 * tourism_weight + \
             r6 * road_weight + \
             r7 * gss_weight + \
             r8 * dsm_weight + \
             r9 * protected_weight) * ex

save_raster(weighting, x_res, y_res, pixel_size, pixel_size, "weighting.tif", True, "Processing\\r_recreation.tif")

#show(weighting)

waterbodies = gpd.read_file(Path+Project+"\\Out_Data\\waterbodies.shp")
data500 = waterbodies.buffer(500)
data500.to_file(Path+Project+"\\Out_Data\\Processing\\water500.shp")

data500 = gpd.read_file(Path+Project+"\\Out_Data\\Processing\\water500.shp")

with rasterio.open(Path+Project+"\\Out_Data\\weighting.tif") as src:
    affine = src.transform
    array = src.read(1)
    df_zonal_stats = pd.DataFrame(zonal_stats(data500, array, affine=affine))
    #add_stats={'good_area':good_area},

#df_zonal_stats = zonal_stats(waterbodies, Path+Project+"\\Out_Data\\weighting.tif", add_stats={'good_area':good_area})
# adding statistics back to original GeoDataFrame
df_zonal_stats = df_zonal_stats.add_prefix('rank_')
waterbodies_scored = pd.concat([waterbodies, df_zonal_stats], axis=1)
waterbodies_scored = waterbodies_scored.drop(['rank_count'],axis=1)
waterbodies_scored.to_file(Path+Project+"\\Out_Data\\waterbodies.shp")
gpd.io.file.fiona.drvsupport.supported_drivers['LIBKML'] = 'rw'
gpd.io.file.fiona.drvsupport.supported_drivers['KML'] = 'rw'
waterbodies_scored.to_file(Path+Project+"\\waterbodies.kml", driver='KML')
waterbodies_csv = waterbodies_scored.drop(['geometry'],axis=1)
waterbodies_csv.to_csv(Path+Project+"\\waterbodies.csv")


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

####################### COST ESTIMATION ########################################

print("Starting cost estimation")

waterbodies_scored = gpd.read_file(Path+Project+"\\Out_Data\\waterbodies.shp")
data50 = waterbodies_scored.buffer(50)
data50.to_file(Path+Project+"\\Out_Data\\Processing\\water50.shp")
data50 = gpd.read_file(Path+Project+"\\Out_Data\\Processing\\water50.shp")
waterbodies_ring = data50.difference(waterbodies)
waterbodies_ring.to_file(Path+Project+"\\Out_Data\\Processing\\waterdonut.shp")
waterbodies_ring = gpd.read_file(Path+Project+"\\Out_Data\\Processing\\waterdonut.shp")


### roads ###
rasterize(fp_main_roads, 'Processing\\main_roads_r', shp_crs, pixel_size, x_res, y_res, 1, 0)
proximity(Path+Project+"\\Out_Data\\Processing\\main_roads_r.tif", 'Processing\\main_roads_proximity.tif')

with rasterio.open(Path+Project+"\\Out_Data\\Processing\\main_roads_proximity.tif") as src:
    affine = src.transform
    array = src.read(1)
    df_zonal_stats = pd.DataFrame(zonal_stats(waterbodies_ring, array, affine=affine))
    
df_zonal_stats = df_zonal_stats.add_prefix('road_cost_')
waterbodies_scored = pd.concat([waterbodies_scored, df_zonal_stats['road_cost_mean']], axis=1)
waterbodies_scored['road_cost_mean'] = waterbodies_scored['road_cost_mean'] * road_cost


### substations ###
with rasterio.open(fp_substationcost) as src:
    affine = src.transform
    array = src.read(1)
    array = array[0:-1]
    df_zonal_stats = pd.DataFrame(zonal_stats(waterbodies_ring, array, affine=affine))
    
df_zonal_stats = df_zonal_stats.add_prefix('line_cost_')
waterbodies_scored = pd.concat([waterbodies_scored, df_zonal_stats['line_cost_mean']], axis=1)
waterbodies_scored['line_cost_mean'] = waterbodies_scored['line_cost_mean'] * transmission_cost
waterbodies_scored.to_file(Path+Project+"\\Out_Data\\waterbodies_lcoe.shp")
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

save_raster(wind, x_res, y_res, pixel_size, pixel_size, "cost_wind.tif", 
            True, "Processing\\r_recreation.tif")
#show(wind)


rasterize(Path+Project+"\\Out_Data\\waterbodies.shp", 'Processing\\waterbodies_r', shp_crs, 
          pixel_size, x_res, y_res, 0, 1)

proximity(Path+Project+"\\Out_Data\\Processing\\waterbodies_r.tif", 'Processing\\cost_waterbodies.tif')

raster_water = rasterio.open(Path+Project+"\\Out_Data\\Processing\\cost_waterbodies.tif")
water_cost = raster_water.read(1)
water_cost[np.where(water_cost < 100)] = 0
water_cost[np.where((100 <= water_cost) & (water_cost <= 500))] = 100
water_cost[np.where(water_cost > 500)] = 110

save_raster(water_cost, x_res, y_res, pixel_size, pixel_size, "cost_water.tif", 
            True, "Processing\\r_recreation.tif")
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

pixel_size_x = (x_max - x_min) / len(bathymetry[0])
pixel_size_y = (y_max - y_min) / len(bathymetry)
save_raster(bathymetry, len(bathymetry[0]), len(bathymetry), pixel_size_x, pixel_size_y, 
            "Processing\\bathy_cost.tif", True, "Processing\\bathymetry.tif")

src = gdal.Open(Path+Project+"\\Out_Data\\Processing\\bathy_cost.tif")
ulx, pixel_size_x, xskew, uly, yskew, pixel_size_y  = src.GetGeoTransform()
lrx = ulx + (src.RasterXSize * pixel_size_x)
lry = uly + (src.RasterYSize * pixel_size_y)
proj = src.GetProjection()
xres = ((lrx) - (ulx)) / pixel_size_x
yres = ((uly) - (lry)) / -pixel_size_y

npad = int((max(abs(x_min-ulx),abs(x_max-lrx),abs(y_min-lry),abs(y_max-uly))) / pixel_size_x)
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
band.SetGeoTransform((ulx-(npad*pixel_size_x), pixel_size_x, 0, uly+(npad*pixel_size_x), 
                      0, pixel_size_y))
band.GetRasterBand(1).WriteArray(raster)
band.SetGeoTransform(gt_new)
band.SetProjection(proj)
band.FlushCache()

clip_raster(Path+Project+"\\Out_Data\\Processing\\bathy_pad.tif", bbox, epsg, 
            Path+Project+"\\Out_Data\\Processing\\bathy_clip.tif")

raster_bathymetry = rasterio.open(Path+Project+"\\Out_Data\\Processing\\bathy_clip.tif")
bathymetry = raster_bathymetry.read(1)
y = exclusion.shape[0] / len(bathymetry)
x = exclusion.shape[1] / len(bathymetry[0])
resize_raster(Path+Project+"\\Out_Data\\Processing\\bathy_clip.tif",y,x,
              Path+Project+"\\Out_Data\\cost_bathymetry.tif")

raster_bathymetry = rasterio.open(Path+Project+"\\Out_Data\\cost_bathymetry.tif")
bathymetry = raster_bathymetry.read(1)
#show(bathymetry)


waterbodies_scored = gpd.read_file(Path+Project+"\\Out_Data\\waterbodies_lcoe.shp")

#clip_raster(fp_pvout, bbox, epsg, Path+Project+"\\Out_Data\\Processing\\pvout_clip.tif")
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
#resize_raster(Path+Project+"\\Out_Data\\Processing\\pvout_clip.tif",y,x,
              #Path+Project+"\\Out_Data\\cost_pvout.tif")

#check this formula including pvout scaling (automate)
system = (((wind / 100) * pv_cost) + ((bathymetry / 100) * mooring_cost) + ((water_cost / 100) * cable_cost)) * 100
#show(system)
save_raster(system, x_res, y_res, pixel_size, pixel_size, "system.tif", True, "Processing\\r_recreation.tif")

bathymetry[np.where(bathymetry != 0)] = 1
water_cost[np.where(water_cost != 0)] = 1
lcoe_mask = system * bathymetry * water_cost
save_raster(lcoe_mask, x_res, y_res, pixel_size, pixel_size, "lcoe_mask.tif", 
            True, "Processing\\r_recreation.tif")

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
save_raster(final, x_res, y_res, pixel_size, pixel_size, "final.tif", 
            True, "Processing\\r_recreation.tif")

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
