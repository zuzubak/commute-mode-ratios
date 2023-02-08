import math
import re
import urllib
import random
from collections import OrderedDict
from itertools import permutations
from json import loads
from typing import List
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


def compute_commute_mode_ratios(
    locations_gdf: gpd.GeoDataFrame,
    commute_direction: str,
    commute_hub: str,
    output_filename: str,
    batch_size=25,
):
    """
    Compute the ratio between transit and driving times for all census tracts in the input
        GeoDataFrame.

    Args:
        locations_gdf: GeoPandas GeoDataFrame containing the polygon geometries of
            the census tracts, plus a column labelled "centroid" with the centroids in
            the format "lat,lon"; the output of load_location_data
        commute_direction: Either "inbound" or "outbound". Determines whether the trips
            are going into the city centre or originating there.
        commute_hub: The location of commute hub from which all trips begin, or where they
            terminate depending on the directionality. Formatted as "lat,lon"
        output_filename: The path to save the resulting shapefile to, without an extension.
        batch_size: The number of locations to include in a batch when making API calls.
            25 is the default since it is the max allowed in the Google Distance Matrix
            API.
    Returns:
        None. Results saved to CSV and SHP files at output_filename.
    """
    # Check commute direction
    if commute_direction == "inbound":
        api_call_func = _get_travel_time
    elif commute_direction == "outbound":
        api_call_func = _get_travel_time_multi_destinations
    else:
        raise ValueError(f"The commute direction must be either inbound or outbound, not {commute_direction}")

    # Batch locations for API call
    location_batches = list(_batch_locations_for_api_call(locations_gdf, batch_size))
    
    # Get driving and transit times, calculate ratios
    for batch in location_batches:
        batch["driving_duration"] = api_call_func(
            batch["centroid"],
            [commute_hub],
            "driving",
        )
        batch["transit_duration"] = api_call_func(
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
    census_tract_shp_path: str,
    municipalities_shapefile_path: str,
    municipality_name: str,
    max_entries=2,
):

    """
    Load census tracts into shapefile, filter to a specific municipality, and
    compute centroids.

    Args:
        census_tract_shp_path: Filepath to Shapefile containing census tracts -- see README
            for download instructions
        municipalities_shapefile_path: Shapefile containing municipality boundaries
        municipality_name: the municipality of interest, in title case.
        max_entries: Number of tracts to limit to, for testing purposes and to prevent
            accidental API over-usage.
    Returns:
        muni_census_tracts: GeoPandas GeoDataFrame containing the polygon geometries of
            the census tracts, plus a column labelled "centroid" with the centroids in
            the format "lat,lon".
    """

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

def _get_travel_time(
    origins: List[str], destinations: List[str], mode: str, arrival_time="now"
):
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


def _get_travel_time_multi_destinations(
    destinations: List[str], origins: List[str], mode: str, departure_time="now"
):
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

def _batch_locations_for_api_call(locations_df, batch_size):
    """
    Generator to divide location GeoDataFrames into batches for API calls.
    """
    for i in range(0, len(locations_df), batch_size):
        yield locations_df[i : min(len(locations_df), i + batch_size)]


def _point_to_api_string(point):
    """
    Formats a shapely Point to the lat,lon string format expected by the Google Distance
        Matrix API.
    """
    return f"{point.y},{point.x}"
