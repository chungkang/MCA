"""
Created by Kimberly Mason
November 2022

Modified by Chungkang Choi
September 2023

Description: customized functions
"""
import numpy as np
import geopandas as gpd
from fiona.crs import from_epsg
from osgeo import ogr, gdal
import rasterio
from rasterio.mask import mask
from rasterio.transform import Affine
from rasterio.warp import reproject, Resampling
from netCDF4 import Dataset
from pyproj import Proj, transform
import json
from shapely.geometry import box

from settings import *

def rasterize(input_shapefile, output_raster_name, shp_crs, pixel_size, x_resolusion, y_resolusion, no, ya, x_min, y_max):
    
    shp_driver = ogr.GetDriverByName("ESRI Shapefile")
    shp_data = shp_driver.Open(input_shapefile)
    shp = shp_data.GetLayer()

    no_data_value = no
    target_r = gdal.GetDriverByName('GTiff').Create(output_raster_name, x_resolusion, y_resolusion, 1)
    target_r.SetGeoTransform((x_min, pixel_size, 0, y_max, 0, -pixel_size))
    band = target_r.GetRasterBand(1)
    band.Fill(no_data_value)

    shp_crs.ImportFromEPSG(int(shp_crs.GetAuthorityCode(None)))
    target_r.SetProjection(shp_crs.ExportToWkt())

    gdal.RasterizeLayer(target_r, [1], shp, None, None, burn_values=[ya], options=['all'])
    band.FlushCache()


def save_raster(input, x, y, pixel_size_x, pixel_size_y, output, geotrans, template, x_min, y_max):
    tif = gdal.Open(template)
    
    band = gdal.GetDriverByName('GTiff').Create(output, x, y, 1)
    band.SetGeoTransform((x_min, pixel_size_x, 0, y_max, 0, -pixel_size_y))
    band.GetRasterBand(1).WriteArray(input)

    if geotrans == True:
        geotrans=tif.GetGeoTransform()
        band.SetGeoTransform(geotrans)
        
    proj = tif.GetProjection()
    band.SetProjection(proj)
    band.FlushCache()


def get_raster_bbox(raster_file):
    with rasterio.open(raster_file) as raster:
        raster_bounds = raster.bounds
    return box(raster_bounds.left, raster_bounds.bottom, raster_bounds.right, raster_bounds.top)


def clip_raster(input_raster, bbox, crs, output_raster):
    raster_r = rasterio.open(input_raster)
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
    
    with rasterio.open(output_raster, "w", **out_meta) as dest:
        #dest.nodata = 0
        dest.write(out_img)


def hillshade(input, azimuth, angle_altitude):
    azimuth = 360.0 - azimuth 
    
    x, y = np.gradient(input)
    slope = np.pi/2. - np.arctan(np.sqrt(x*x + y*y))
    aspect = np.arctan2(-x, y)
    azimuthrad = azimuth*np.pi/180.
    altituderad = angle_altitude*np.pi/180.
 
    shaded = np.sin(altituderad)*np.sin(slope) + np.cos(altituderad)*np.cos(slope)*np.cos((azimuthrad - np.pi/2.) - aspect)
    
    return 255*(shaded + 1)/2


def get_landcover(landcover_input, x_min, y_min, x_max, y_max, template, epsg, output): # extracts land cover for the project area from the global netCDF
    
    land_nc = Dataset(landcover_input)

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
    
    save_raster(subset[0], len(subset[0][0]), len(subset[0]), pixel_size_x, pixel_size_y, output, False, template, x_min, y_max)
    

def proximity(input_tif, output):
    src_ds = gdal.Open(input_tif)
    srcband=src_ds.GetRasterBand(1)
    
    drv = gdal.GetDriverByName('GTiff')
    dst_ds = drv.Create( output, src_ds.RasterXSize, src_ds.RasterYSize, 1, gdal.GetDataTypeByName('Float32'))
    dst_ds.SetGeoTransform(src_ds.GetGeoTransform())
    dst_ds.SetProjection(src_ds.GetProjectionRef())
    
    dstband = dst_ds.GetRasterBand(1)
        
    gdal.ComputeProximity(srcband,dstband,["VALUES='0'","DISTUNITS=GEO"])
    srcband = None
    dstband = None
    src_ds = None
    dst_ds = None
    

def resize_raster(input_raster, x_factor, y_factor, output):
    # Open the input raster using rasterio
    with rasterio.open(input_raster) as src:
        # Read the data as a numpy array
        data = src.read(1)

        # Get the transform information
        transform = src.transform

        # Calculate the new dimensions
        new_height = int(src.height * y_factor)
        new_width = int(src.width * x_factor)

        # Create a new transform for the resized raster
        new_transform = Affine(
            transform.a / x_factor,
            transform.b,
            transform.c,
            transform.d,
            transform.e / y_factor,
            transform.f
        )

        # Perform the resizing using bilinear interpolation
        resized_data = np.empty((new_height, new_width), dtype=data.dtype)
        reproject(
            data,
            resized_data,
            src_transform=transform,
            dst_transform=new_transform,
            src_crs=src.crs,
            dst_crs=src.crs,
            resampling=Resampling.bilinear
        )

        # Update the metadata
        new_meta = src.meta.copy()
        new_meta.update({
            'width': new_width,
            'height': new_height,
            'transform': new_transform
        })

        # Write the resized raster to the output file
        with rasterio.open(output, 'w', **new_meta) as dst:
            dst.write(resized_data, 1)
