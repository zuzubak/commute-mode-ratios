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


def compute_commute_mode_ratios(
    locations_df,
    commute_hub,
    output_filename,
    batch_size=25,
):

    location_batches = list(_batch_locations_for_api_call(locations_df, batch_size))
    for batch in location_batches:
        batch["driving_duration"] = get_travel_time_multi_origins(
            batch["centroid"],
            [commute_hub],
            "driving",
        )
        batch["transit_duration"] = get_travel_time_multi_origins(
            batch["centroid"],
            [commute_hub],
            "transit",
        )
        batch["transit_to_drive_ratio"] = [
            t / d if d > 0 else np.nan
            for t, d in zip(
                batch["transit_duration"],
                batch["driving_duration"],
            )
        ]

    # Compile and export
    combined_result = pd.concat(location_batches)
    combined_result.to_csv(f"{output_filename}.csv")
    combined_result_gdf = gpd.GeoDataFrame(combined_result, crs=4326)
    combined_result_gdf.to_file(f"{output_filename}.shp")


def load_location_data(
    census_tract_shp_path,
    municipalities_shapefile_path,
    municipality_name,
    max_entries=2,
):
    census_tracts = gpd.read_file(census_tract_shp_path)
    municipalities = gpd.read_file(municipalities_shapefile_path)
    muni_boundaries = municipalities.loc[municipalities.CDNAME == municipality_name]

    muni_census_tracts = census_tracts.loc[
        census_tracts.within(list(muni_boundaries.geometry)[0])
    ]

    muni_census_tracts = muni_census_tracts[:max_entries]

    muni_census_tracts.geometry = muni_census_tracts.geometry.to_crs(4326)

    muni_census_tracts["centroid"] = [
        _point_to_api_string(ct.centroid) for ct in muni_census_tracts.geometry
    ]
    return muni_census_tracts


def _batch_locations_for_api_call(locations_df, batch_size):
    for i in range(0, len(locations_df), batch_size):
        yield locations_df[i : min(len(locations_df), i + batch_size)]


def _point_to_api_string(point):
    """
    Formats a shapely Point to the lat,lon string format expected by Google
    """
    return f"{point.y},{point.x}"
