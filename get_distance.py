import math
import re
import urllib
import random
from collections import OrderedDict
from itertools import permutations
from json import loads
from urllib import request
from urllib.request import urlopen

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
import shapely
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon

from creds import api_key


def get_travel_time(origins, destinations, mode, arrival_time="now"):
    origins = [point_to_api_string(point) for point in origins]
    destinations = [point_to_api_string(point) for point in destinations]
    url = f"""https://maps.googleapis.com/maps/api/distancematrix/json?destinations={"%7C".join(destinations)}&language=en-EN&mode={mode}&origins={"%7C".join(origins)}&arrival_time={arrival_time}&key={api_key}"""
    payload = {}
    headers = {}

    response = requests.request("GET", url, headers=headers, data=payload)
    response_dict = loads(response.text)
    distance_matrix = [
        [
            item["duration"]["value"] if "duration" in item else 0
            for item in row["elements"]
        ]
        for row in response_dict["rows"]
    ]  # origins within rows, destinations within columns
    return [sum(distances) / len(distances) for distances in distance_matrix]


def get_travel_time_multi_origins(destinations, origins, mode, departure_time="now"):
    origins = [point_to_api_string(point) for point in origins]
    destinations = [point_to_api_string(point) for point in destinations]
    url = f"""https://maps.googleapis.com/maps/api/distancematrix/json?destinations={"%7C".join(destinations)}&language=en-EN&mode={mode}&origins={"%7C".join(origins)}&departure_time={departure_time}&key={api_key}"""
    payload = {}
    headers = {}

    response = requests.request("GET", url, headers=headers, data=payload)
    response_dict = loads(response.text)
    distance_matrix = [
        [
            item["duration"]["value"] if "duration" in item else 0
            for item in row["elements"]
        ]
        for row in response_dict["rows"]
    ]  # origins within rows, destinations within columns
    return distance_matrix[0]


def load_census_tracts(
    census_tract_shp_path,
    municipalities_shapefile_path,
    municipality_name,
    output_filename,
    batch_size=25,
):
    dfs = []

    census_tracts = gpd.read_file(census_tract_shp_path)
    municipalities = gpd.read_file(municipalities_shapefile_path)
    muni_boundaries = municipalities.loc[municipalities.CDNAME == municipality_name]

    muni_census_tracts = census_tracts.loc[
        census_tracts.within(list(muni_boundaries.geometry)[0])
    ]

    muni_census_tracts.geometry = muni_census_tracts.geometry.to_crs(4326)

    muni_census_tracts["centroid"] = [ct.centroid for ct in muni_census_tracts.geometry]
    muni_census_tracts["centroid_string"] = [
        point_to_api_string(centroid) for centroid in muni_census_tracts["centroid"]
    ]
    for i in range(0, len(muni_census_tracts), batch_size):
        batch = muni_census_tracts[i : min(len(muni_census_tracts), i + batch_size)]
        batch["driving_duration"] = get_travel_time_multi_origins(
            batch.centroid,
            [Point(-79.380851, 43.645570)],
            "driving",
            departure_time="1670018400",
        )
        batch["transit_duration"] = get_travel_time_multi_origins(
            batch.centroid,
            [Point(-79.380851, 43.645570)],
            "transit",
            departure_time="1670018400",
        )
        batch["transit_to_drive_ratio"] = [
            t / d if d > 0 else 0
            for t, d in zip(
                batch["transit_duration"],
                batch["driving_duration"],
            )
        ]
        dfs.append(batch)

    combined_result = pd.concat(dfs)
    combined_result.to_csv(f"{output_filename}.csv")
    combined_result = gpd.GeoDataFrame(combined_result, crs="epgsg:4326")
    combined_result.to_file(f"{output_filename}.shp")


def point_to_api_string(point):
    """
    Formats
    """
    return f"{point.y},{point.x}"


load_census_tracts(
    "/Users/zuzubak/Downloads/lda_000b21a_e/lda_000b21a_e.shp",
    "/Users/zuzubak/Downloads/lcd_000a16a_e/lcd_000a16a_e.shp",
    "Toronto",
    "Toronto_5pm_2Dec_census_blocks_forecasted",
)
