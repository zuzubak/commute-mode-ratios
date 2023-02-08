# commute-mode-ratios

This repo is for calculating the ratio between driving and transit commute times across a city at a given time of day, using the Google Distance Matrix API. Results are output in both CSV and Shapefile formats.

## Setup

### Data
Before getting started, you'll need to download the zipped shapefiles for Canadian census tracts, and census subdivisions.
These can be found at the URL below. Select the "shapefile" option.

https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/index2021-eng.cfm?year=21

Unzip them, place the two unzipped folders in a subdirectory within the repo called "data", and you're good to go!

### Enviroment
To create an anaconda environment to run the code in, run:

`conda env create -f environment.yml`

## Usage

Use load_location_data to create a GeoDataFrame containing the locations to be included,
then pass it to compute_commute_mode_ratios, which will handle the API calls and save the 
results to file.

