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
from shapely.geometry import box

from a_settings import *

input_data_path = PATH + "00_input_data\\"
osm_data_path = PATH + "01_osm_data\\"

# download the data with region name (cannot perform with large area)
# osm_data = pyrosm.get_data(place_name)
# osm = pyrosm.OSM(osm_data)

# download pbf in interested area from the website below
# https://extract.bbbike.org/
osm = pyrosm.OSM(input_data_path + "mozambique_part.osm.pbf")

# https://wiki.openstreetmap.org/wiki/Map_features

# boundary
boundary = osm.get_boundaries(boundary_type = "all")
boundary = boundary.set_crs('epsg:4326')
boundary = boundary.to_crs(epsg=EPSG)
boundary.to_file(osm_data_path + "boundary.shp")

# water = osm.get_data_by_custom_criteria(custom_filter={'natural':['water']}, filter_type="keep", keep_nodes=False, keep_ways=False, keep_relations=True)
# # Check if water is None before proceeding
# if water is not None:
#     water = water.set_crs('epsg:4326')
#     water = water.to_crs(epsg=EPSG)
#     water.to_file(osm_data_path + "water_osm.shp")
# else:
#     print("No water data found in the query.")

# rivers
rivers = osm.get_data_by_custom_criteria(custom_filter={'waterway':['river','dam']}, filter_type="keep", keep_nodes=False, keep_ways=True, keep_relations=True)
if rivers is not None:
    rivers = rivers.set_crs('epsg:4326')
    rivers = rivers.to_crs(epsg=EPSG)
    rivers = rivers.buffer(200)
    rivers.to_file(osm_data_path + "buffered_rivers.shp")
else:
    print("No river data found in the query.")

#roads
roads = osm.get_network(network_type="driving")
# Check if driving is None before proceeding
if roads is not None:
    roads = roads.set_crs('epsg:4326')
    roads = roads.to_crs(epsg=EPSG)
    roads.to_file(osm_data_path + "roads.shp")
else:
    print("No roads data found in the query.")

# main roads
main_roads = osm.get_data_by_custom_criteria(custom_filter={'highway':['trunk','primary','secondary']}, filter_type="keep", keep_nodes=False, keep_ways=True, keep_relations=False)
if main_roads is not None:
    main_roads = main_roads.set_crs('epsg:4326')
    main_roads = main_roads.to_crs(epsg=EPSG)
    main_roads.to_file(osm_data_path + "main_roads.shp")
else:
    print("No main roads data found in the query.")

#substation
substations = osm.get_data_by_custom_criteria(custom_filter={'power':['substation']}, filter_type="keep", keep_nodes=True, keep_ways=True, keep_relations=True)
# Check if substation is None before proceeding
if substations is not None:
    # Convert to the desired CRS if sub is not None
    substations = substations.set_crs('epsg:4326')
    substations = substations.to_crs(epsg=EPSG)
    
    # Save the data to a file
    substations.to_file(osm_data_path + "substations.shp")
else:
    print("No substations data found in the query.")