import glob

import geopandas as gpd

from commute_mode_ratios.get_distance import (
    get_travel_time,
    get_travel_time_multi_origins,
    load_census_tracts,
)

_CENSUS_TRACTS = "data/canadian_census_tracts/lda_000b21a_e.shp"
_CENSUS_DIVISIONS = "data/canadian_census_divisions/lcd_000a16a_e.shp"
_MUNICIPALITY = "Toronto"
_OUTPUT_FILENAME = "tests/artifacts/test_load_census_tracts"
_MAX_ENTRIES = 2


def test_load_census_tracts():
    load_census_tracts(
        _CENSUS_TRACTS,
        _CENSUS_DIVISIONS,
        _MUNICIPALITY,
        _OUTPUT_FILENAME,
        max_entries=2,
    )
    output_files = glob.glob(f"{_OUTPUT_FILENAME}*")
    assert len(output_files) == 6  # CSV, SHP & 4 SHP-associated files
    shp_result = gpd.read_file(f"{_OUTPUT_FILENAME}.shp")
    1 == 1
