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
from shapely import unary_union

# All Functions ---------------------------------

# Main Code -------------------------------------

# Load all spatial data ----------

#load all contours - vector
#contours = gpd.read_file("../data/SlopeContour_polygon.shp")
contours = gpd.read_file("C:/Users/Sophia Soni/OneDrive - The University of Manchester/University/4 - YEAR 4 FINAL GEO/DISSERTATION/dissertation-code2/data/SlopeContour_polygon.shp")

#load all landuse - vector
#landuse = gpd.read_file("../data/Land-Use-All.shp")
landuse = gpd.read_file("C:/Users/Sophia Soni/OneDrive - The University of Manchester/University/4 - YEAR 4 FINAL GEO/DISSERTATION/dissertation-code2/data/Land-Use-All.shp")

#NOT COMPLETED YET
#load all flood zone 2 - raster 
#floodzone_2 = rio_open("../data/")

#load all flood zone 3 - raster 
#floodzone_3 = rio_open("../data/")

#ensure all the same CRS -------
contours = contours.to_crs(landuse.crs)


# SECTION 1 - Cutting each landuse polygon based on elevation cut off --------

# Part 1 - Natural Land - looking at each polygon and cutting ----

#count all polygons that contain "natural land" in the NAME field
natural_counts = landuse.groupby(["Name"]).size() 
print(natural_counts)

# create user defined elevation contour cut off ----
#contour min field = 0 to 45 in 5m intervals 
#contour max field = 5 to 50 in 5m intervals 

ELEV_MIN = 15
ELEV_MAX = 60

#Filter contours by threshold ----
bad_contours = contours[
    (contours["ContourMin"] >= ELEV_MIN) &
    (contours["ContourMax"] <= ELEV_MAX)]

print(len(bad_contours))

#merging all bad contours (so that its easy to erase)
bad_geom = unary_union(bad_contours.geometry)


#iterate through each polygon 

#if each polygon intersects with the contour polygon 

#get the shape area of the contour polygon overlapping with natural land polygon 

#use erase tool to erase the contour polygon shape from the natural land

#output new shapes with all new natural land polygons


# Part 2 - Manmade Surface - looking at each polygon and cutting ----


# SECTION 2 - Finding max inscribed circle in each polygon ------------------------


# SECTION 3 - Creating weighted overlays (user defined) ------------------



# Plotting all Maps ------------------------------




# --- NO CODE BELOW HERE ---

# report runtime
print(f"completed in: {perf_counter() - start_time} seconds")
