# -*- coding: utf-8 -*-
"""
Created by Kimberly Mason
November 2022
"""
# Public
PATH = "projects\\" # path to Projects folder
PROJECT = "MZ_AfDB_Chicamba\\"

# Search https://nominatim.openstreetmap.org/ui/search.html for the place name,
# only necessary when using the Data_Download script to extract data from OpenStreetMap
PLACE_NAME = "mozambique"
EPSG = 3857            # coordinate reference system code, search https://epsg.io/ for the epsg code of the
HEMISPHERE = "S"        # WGS 84 / UTM zone ??N where the project is located

PIXEL_SIZE = 50         # resolution in metres
MIN_AREA = 100          # minimum size for reservoirs in ha
MAX_PV_SIZE = 75        # maximum size of PV plant in MW

# sum of weights should be 1
GHI_WEIGHT = 0.26
WIND_WEIGHT = 0.02
LANDCOVER_WEIGHT = 0.06
ROAD_WEIGHT = 0.19
GSS_WEIGHT = 0.19
DSM_WEIGHT = 0.16
PROTECTED_AREA_WEIGHT = 0.12

# cost in Sri Lanka
PV_COST = 0.64          # cost per Wp
MOORINT_COST = 0.03     # cost per Wp
CABLE_COST = 0.05       # cost per Wp
TRANSMISSION_COST = 900 # cost per m
ROAD_COST = 1500        # cost per m
O_M_COST = 10           # cost per kWp per year
PV_TARRIFF = 0.08        # tariff per kWp
PV_LIFETIME = 25        # lifetime of PV plant in years
