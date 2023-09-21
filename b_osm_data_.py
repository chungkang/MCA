# -*- coding: utf-8 -*-
"""
Created by Kimberly Mason
November 2022

Modified by Chungkang Choi
September 2023

Description: Extracts data layers from OpenStreetMap
"""
import geopandas as gpd
import pyrosm

from settings import *

input_data_path = PATH + PROJECT + "00_input_data\\"
data_download_path = PATH + PROJECT + "01_data_download\\"

# download the data with region name (cannot perform with large area)
# osm_data = pyrosm.get_data(place_name)
# osm = pyrosm.OSM(osm_data)

# download pbf in interested area from the website below
# https://extract.bbbike.org/
osm = pyrosm.OSM("C:\workspace\FloatingPV-SiteTool-Chicamba\Data_Sources\chicamba.osm.pbf")

# https://wiki.openstreetmap.org/wiki/Map_features

# boundary
boundary = osm.get_boundaries()
boundary = boundary.set_crs('epsg:4326')
boundary = boundary.to_crs(epsg=EPSG)
boundary = boundary.buffer(0)
boundary.to_file(data_download_path + "boundary.shp")


# waterbody cannot be extracted properly -> manually extraction with https://overpass-turbo.eu/ as geojson
water = gpd.read_file(input_data_path + "water.geojson")
water.to_crs(epsg=EPSG)
water.to_file(data_download_path + "water.shp", driver='ESRI Shapefile')

# water = osm.get_data_by_custom_criteria(custom_filter={'natural':['water']}, filter_type="keep", keep_nodes=False, keep_ways=False, keep_relations=True)
# # Check if water is None before proceeding
# if water is not None:
#     water = water.set_crs('epsg:4326')
#     water = water.to_crs(epsg=EPSG)
#     water.to_file(data_download_path + "water_osm.shp")
# else:
#     print("No water data found in the query.")


#road
road = osm.get_network(network_type="driving")
# Check if driving is None before proceeding
if road is not None:
    road = road.set_crs('epsg:4326')
    road = road.to_crs(epsg=EPSG)
    road.to_file(data_download_path + "road.shp")
else:
    print("No driving data found in the query.")


#substation
substation = osm.get_data_by_custom_criteria(custom_filter={'power':['substation']}, filter_type="keep", keep_nodes=True, keep_ways=True, keep_relations=True)
# Check if substation is None before proceeding
if substation is not None:
    # Convert to the desired CRS if sub is not None
    substation = substation.set_crs('epsg:4326')
    substation = substation.to_crs(epsg=EPSG)
    
    # Save the data to a file
    substation.to_file(data_download_path + "substation.shp")
else:
    print("No substation data found in the query.")