"""
Dissertation - [insert title here]
@author [11070578]
"""
from time import perf_counter

# set start time
start_time = perf_counter()	

# --- NO CODE ABOVE HERE -------

# All Imports -------------------------------

import geopandas as gpd
from shapely import unary_union
from shapely import maximum_inscribed_circle
from shapely.geometry import Point, LineString

# All Functions ---------------------------------

#erasing bad contours function - instead of long code
def erase_contours(gdf, erase_geom, land_type):
    
    """
    Function used to erase contour polygon from the land type polygon
    - easy so that can call function at any time 
    
    gdf = geodataframe - shapefile used
    erase_geom = the contour area that needs to be erased 
    land_type = either natural or manmade land
    """
    
    #empty list to store all new polygons rows created after erasing
    output_polygons = []

    #iterate through each polygon - looping through
    for idx, row in gdf.iterrows():

        #extracting the polygon geometry from geodataframe 
        geom = row.geometry
        
        #skip invalid or empty geometries 
        if geom is None or geom.is_empty:
            continue
        
        #intersection test - 
        #if each land-type polygon DOESNT intersects with the contour polygon 
        if not geom.intersects(erase_geom): 
        
            #add non intersecting polygons to new variable
            new_geom = geom
            
        else:
    
            #difference tool - A.difference(B) = A - B results in portion of A
            #subtracts the contour area from the land polygon (landuse polygon minus contour polygon)
            new_geom = geom.difference(erase_geom)
            
        #if the landuse polygon is entirely removed by the contour erase 
        if new_geom.is_empty: 
            
            #then skip it - continue tool
            continue
        
        #not splitting multiparts - appending the new geom to output
        output_polygons.append({
            "ID": idx,
            "Land_type": land_type, 
            "geometry": new_geom })

    #output new shapes with all new natural land polygons
    return gpd.GeoDataFrame(
        output_polygons, 
        geometry = "geometry",
        crs=gdf.crs)



#USER DEFINED PARAMETERS - FOR COMPUTING THE MAX CIRCLE

# minimum tank radius (m)
MIN_RADIUS = 4

# clearance - buffer from the polygon edges (m)
BOUNDARY_BUFFER = 4
    

#creating the max inscribed circle within each polygon
def compute_mic(gdf, min_radius, boundary_buffer): 
    
    """
    Maximum inscirbed circle -  finds the max circle within each polygon 
    - works with polygons with holes and multipolygons 
    
    Finds Pole of inaccessability
    - finds the point in the polygon with the farthest distance from the boundary
    - optimisation process rather than sampling multiple points 
    """

    #empty list to store all new circles
    mic_results = []
    
    #iterate through each polygon - looping through
    for idx, row in gdf.iterrows():

        #extracting the polygon geometry from geodataframe 
        poly = row.geometry
        
        #skip invalid or empty geometries 
        if poly is None or poly.is_empty:
            continue
        
        #applying the boundary clearance inside the polygon 
        #before applying circles 
        safe_poly = poly.buffer(-boundary_buffer)
        
        #skipping invalid or empty safe polygons
        if safe_poly.is_empty:
            continue
        
        #running the max inscribed circle tool 
        mic_line = maximum_inscribed_circle(safe_poly)
        
        #output should be one line coords
        #checking if not outputting linestring or length is not equal to 2 - skip
        if not isinstance(mic_line, LineString) or len(mic_line.coords) != 2:
            continue
        
        #creating variables for each point and line that we want
        #centre point (x), nearest boundary point (y)
        centre = Point(mic_line.coords[0])
        boundary_pt = Point(mic_line.coords[1])
        
        #radius is distance from centre to boundary pt
        radius = centre.distance(boundary_pt)
        
        #if the radius is more than the minimum radius parameter - then skip/ignore
        if radius < min_radius: 
            continue 
        
        #creating a circle variable to output
        circle = centre.buffer(radius)
        
        #append the circles in the new array
        mic_results.append({
            "ID": idx, 
            "Radius": radius, 
            "Diameter": radius *2,
            "geometry": circle })
        
    #output new shapes with all new circles within polygon buffer
    return gpd.GeoDataFrame(
        mic_results, 
        geometry = "geometry",
        crs=gdf.crs)
        

# Main Code -------------------------------------

# Load all spatial data ----------

#load all contours - vector
contours = gpd.read_file("data/SlopeContour_polygon.shp")

#load all landuse - vector
landuse = gpd.read_file("data/Land-Use-All.shp")

#NOT COMPLETED YET
#load all flood zone 2 - raster 
#floodzone_2 = rio_open("../data/")

#load all flood zone 3 - raster 
#floodzone_3 = rio_open("../data/")

#ensure all the same CRS -------
contours = contours.to_crs(landuse.crs)



# SECTION 1 - Cutting each landuse polygon based on elevation cut off --------

#count all polygons that contain "natural land" in the NAME field
natural_counts = landuse.groupby(["Name"]).size() 
#print(natural_counts)

# create user defined elevation contour cut off ----
#contour min field = 0 to 45 in 5m intervals 
#contour max field = 5 to 50 in 5m intervals 

# USER DEFINED PARAMETER - ELEVATION
# ArcGIS attribute table - elevation to remove from polygons
ELEV_MIN = 15
ELEV_MAX = 60


#Filter contours by threshold ----
#only selecting contours whos elevation is inside min and max
bad_contours = contours[
    (contours["ContourMin"] >= ELEV_MIN) &
    (contours["ContourMax"] <= ELEV_MAX)]

#number of attribute rows that were removed - from arcgis 
print(f"Contour rows removed: {len(bad_contours)}")

#merging all bad contours (so that its easy to erase)
bad_geom = unary_union(bad_contours.geometry)

print("Any intersections at all?:",
      landuse.intersects(bad_geom).sum())

print("Bad geom is empty?:", bad_geom.is_empty)


# Splitting Land Use Types -----
#for efficiency instead of redoing this section of code twice

#select by attributes - natural land
natural_land = landuse[landuse["Name"].str.contains("Natural Land")]

#select by attributes - manmade surface
manmade_land = landuse[landuse["Name"].str.contains("Manmade Surface")]

#printing a count of all raw polygons in attributes
print(f"Natural RAW Polygons: {len(natural_land)}")
print(f"Manmade RAW Polygons: {len(manmade_land)}")


# Running the erase contour function -----

#calling function to erase contours for natural land 
natural_clean = erase_contours(natural_land, bad_geom, "Natural Land")

#calling function to erase contours for manmade surface 
manmade_clean = erase_contours(manmade_land, bad_geom, "Manmade Surface")

#printing new count of all cut down polygons after erase function
#print(f"Natural Polygons after CUT: {len(natural_clean)}")
#print(f"Manmade Polygons after CUT: {len(manmade_clean)}")


# Saving outputs to a new shapefile -----

#new natural land polygons to new shapefile
natural_clean.to_file("out/natural_clean.shp")

#new manmade land polygons to new shapefile
manmade_clean.to_file("out/manmade_clean.shp")



# SECTION 2 - Finding max inscribed circle in each polygon ------------------------

#load all natural land - vector
natural_clean = gpd.read_file("out/natural_clean.shp")

#load all manmade surfaces - vector
manmade_clean = gpd.read_file("out/manmade_clean.shp")


# Running Max Inscribed Circle Function ------

natural_mic = compute_mic(
    natural_clean, 
    min_radius = MIN_RADIUS, 
    boundary_buffer = BOUNDARY_BUFFER )

manmade_mic = compute_mic(
    natural_clean, 
    min_radius = MIN_RADIUS, 
    boundary_buffer = BOUNDARY_BUFFER )


# Saving outputs to a new shapefile -----

#new natural land polygons to new shapefile
natural_mic.to_file("out/natural_MIC_safe.shp")

#new manmade land polygons to new shapefile
manmade_mic.to_file("out/manmade_MIC_safe.shp")


# SECTION 3 - Creating weighted overlays (user defined) ------------------



# Plotting all Maps ------------------------------




# --- NO CODE BELOW HERE ---

# report runtime
print(f"completed in: {perf_counter() - start_time} seconds")
