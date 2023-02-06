import glob

import geopandas as gpd

from commute_mode_ratios.get_distance import (
    get_travel_time,
    get_travel_time_multi_origins,
    load_location_data,
    compute_commute_mode_ratios,
)

_CENSUS_TRACTS = "data/canadian_census_tracts/lda_000b21a_e.shp"
_CENSUS_DIVISIONS = "data/canadian_census_divisions/lcd_000a16a_e.shp"
_MUNICIPALITY = "Toronto"
_COMMUTE_HUB = "43.645570,-79.380851"
_OUTPUT_FILENAME = "tests/artifacts/test_load_census_tracts"
_MAX_ENTRIES = 2
_TEST_LOCATION_SHP_FILEPATH = "tests/data/test_location_data.shp"


def test_load_location_data():
    locations_gdf = load_location_data(
        _CENSUS_TRACTS,
        _CENSUS_DIVISIONS,
        _MUNICIPALITY,
        max_entries=2,
    )
    assert len(locations_gdf) == 2


def test_compute_commute_mode_ratios():
    test_location_data = gpd.read_file(_TEST_LOCATION_SHP_FILEPATH)
    compute_commute_mode_ratios(test_location_data, _COMMUTE_HUB, _OUTPUT_FILENAME)
    output_files = glob.glob(f"{_OUTPUT_FILENAME}*")
    assert len(output_files) == 6  # .CSV, .SHP, .CPG, .DBF, .PRJ, .SHX
    shp_result = gpd.read_file(f"{_OUTPUT_FILENAME}.shp")
    assert len(shp_result) == 2
