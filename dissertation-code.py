"""
Dissertation - [insert title here]
@author [11070578]
"""
from time import perf_counter

# set start time
start_time = perf_counter()	

# --- NO CODE ABOVE HERE -------

# All Imports -------------------------------

from geopandas import read_file, gpd
from rasterio import open as rio_open
from rasterio.transform import rowcol
from rasterio.plot import show as rio_show

# All Functions ---------------------------------

# Main Code -------------------------------------




# --- NO CODE BELOW HERE ---

# report runtime
print(f"completed in: {perf_counter() - start_time} seconds")
