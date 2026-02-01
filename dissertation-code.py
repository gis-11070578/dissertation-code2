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
from matplotlib.pyplot import subplots, savefig

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



#USER DEFINED PARAMETERS - FOR COMPUTING THE MAX CIRCLE ----

# minimum tank radius (m)
MIN_RADIUS = 3

# maximum tank radius (m)
MAX_RADIUS = 55

# clearance - buffer from the polygon edges (m)
BOUNDARY_BUFFER = 3
    

#creating the max inscribed circle within each polygon
def compute_mic(gdf, min_radius, max_radius, boundary_buffer): 
    
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
        
        #if radius is larger than max radius - skip
        #OR radius is smaller than min radius - skip
        if radius > max_radius or radius < min_radius:
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

#load Bath CSO - vector
cso = gpd.read_file("data/BathLambridgeCSO.shp")

#load Bath Outfall - vector
outfall = gpd.read_file("data/BathLambridgeOutfall.shp")

#load Bath CSO to outfall - vector
cso2outfall = gpd.read_file("data/BathCSO2Outfall.shp")

#load all flood zone 2 - raster 
floodzone_2 = gpd.read_file("data/EAFloodZone_2_Clip")

#load all flood zone 3 - raster 
floodzone_3 = gpd.read_file("data/EAFloodZone_3_Clip")

#ensure all the same CRS ---------

contours = contours.to_crs(landuse.crs)
cso = cso.to_crs(landuse.crs)
outfall = outfall.to_crs(landuse.crs)
cso2outfall = cso2outfall.to_crs(landuse.crs)
floodzone_2 = floodzone_2.to_crs(landuse.crs)
floodzone_3 = floodzone_3.to_crs(landuse.crs)


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
#print(f"Contour rows removed: {len(bad_contours)}")

#merging all bad contours (so that its easy to erase)
bad_geom = unary_union(bad_contours.geometry)

#print("Any intersections at all?:",
      #landuse.intersects(bad_geom).sum())

#("Bad geom is empty?:", bad_geom.is_empty)


# Splitting Land Use Types -----
#for efficiency instead of redoing this section of code twice

#select by attributes - natural land
natural_land = landuse[landuse["Name"].str.contains("Natural Land")]

#select by attributes - manmade surface
manmade_land = landuse[landuse["Name"].str.contains("Manmade Surface")]

#printing a count of all raw polygons in attributes
#print(f"Natural RAW Polygons: {len(natural_land)}")
#print(f"Manmade RAW Polygons: {len(manmade_land)}")


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
    max_radius = MAX_RADIUS,
    boundary_buffer = BOUNDARY_BUFFER )

manmade_mic = compute_mic(
    manmade_clean, 
    min_radius = MIN_RADIUS, 
    max_radius = MAX_RADIUS,
    boundary_buffer = BOUNDARY_BUFFER )


# Saving outputs to a new shapefile -------

#new natural land polygons to new shapefile
natural_mic.to_file("out/natural_MIC_safe.shp")

#new manmade land polygons to new shapefile
manmade_mic.to_file("out/manmade_MIC_safe.shp")

#read new landuse land polygons
natural_MIC_safe = gpd.read_file("out/natural_MIC_safe.shp")
manmade_MIC_safe = gpd.read_file("out/manmade_MIC_safe.shp")

#set to same coord system
natural_MIC_safe = natural_MIC_safe.to_crs(landuse.crs)
manmade_MIC_safe = manmade_MIC_safe.to_crs(landuse.crs)

#merge and combine both shapefiles
landuse_MIC_safe = gpd.concat([natural_MIC_safe, manmade_MIC_safe])

#export to shapefile
landuse_MIC_safe.to_file("out/landuse_MIC_safe.shp")


# SECTION 3 - Creating weighted overlays (user defined) ------------------

#read file for combined land use MIC - only natural and manmade surfaces
MIC_landuse = gpd.read_file("out/landuse_MIC_safe.shp")

# USER DEFINED WEIGHTING (must sum up to 1.0) ----
W_DISTANCE = 0.2
W_LANDUSE = 0.2
W_TANKSIZE = 0.2
W_FLOODZONE_2 = 0.2
W_FLOODZONE_3 = 0.2


# DISTANCE FROM CSO - NEED LOCATION ----
#create user defined buffer zone - from cso point
MAX_DISTANCE = 1000 #1km - meters

#create a CSO point to buffer from
cso_point = cso.geometry.iloc[0]

#CSO buffer made from point - using max distance
cso_buffer = cso_point.buffer(MAX_DISTANCE)

#creating a new field with 0
MIC_landuse["score_distance"] = 0.0 

#loop through each row in the MIC circles
for i, row in MIC_landuse.iterrows():
    
    #geometry of the centre of the circles
    centre = row.geometry.centroid 
    
    #geometry - distance from the CSO to the centre of the circle
    dist = centre.distance(cso_point)

    #if the distance from the cso is less than the max distance 
    if dist <= MAX_DISTANCE: 
        
        #new score - higher score (1 at CSO, 0 at max distance)
        score = 1 - (dist / MAX_DISTANCE)
        
        #new field "score distance" = update
        MIC_landuse.loc[i, "score_distance"] = score
        
    #else - then make the score 0
    else:
        MIC_landuse.loc[i, "score_distance"] = 0.0


# LANDUSE SCORING ----
#total land use is equal to 1

#if mic intersects manmade surfaces - score 

#if mic intersects natural land - score

#total score = 

#score = int(man_made.intersects(circle))


# TANK SIZE SCORING ----

#score = ((tank.area * height) - (min_area * height)) / ((max_area * height) - (min_area * height))


# FLOOD RISK SCORING ----

#flood zone 2 - medium risk 
#if mic intersect with flood zone 2 - score

#flood zone 3 - high risk
#if mic intersect with flood zone 3 - score



# FINAL WEIGHTING SCORE ----

# sum(score) x weight

# final_score = sum([score * weight for score, weight in zip(scores, weights)])


# Plotting all Maps ------------------------------

#select by attributes - rivers
inland_water = landuse[landuse["Name"].str.contains("Inland Water")]

#select by attributes - roads
roads = landuse[landuse["Name"].str.contains("Roads")]

#select by attributes - buildings
buildings = landuse[landuse["Name"].str.contains("Buildings")]


# plot the dataset -------------
fig, my_ax = subplots(figsize=(8, 4))

# remove axes
my_ax.axis('off')

#creating title
fig.suptitle('Visualising MIC circles', fontsize=10, weight='bold')

#USER DEFINED PARAMETER
#buffer around the border itself - to give us some context
CSO_ZOOM_BUFFER = 350

# extract the bounds from the CSO layer
cso_buffer = cso.geometry.buffer(CSO_ZOOM_BUFFER)
minx, miny, maxx, maxy = cso_buffer.total_bounds

my_ax.set_xlim([minx, maxx])
my_ax.set_ylim([miny, maxy])


# plotting cleaned land use polygons -------

#natural land cleaned
natural_clean.plot(ax = my_ax, color = '#ccebc5', edgecolor = 'green',  linewidth = 0.3)

#manmade land cleaned
manmade_clean.plot(ax = my_ax, color = 'lightgrey', edgecolor = 'grey',  linewidth = 0.3)


#land use extras -----

#natural land cleaned
inland_water.plot(ax = my_ax, color = 'lightblue', edgecolor = 'blue',  linewidth = 0.3)

#natural land cleaned
roads.plot(ax = my_ax, color = '#fed9a6', edgecolor = 'orange',  linewidth = 0.3)

#natural land cleaned
buildings.plot(ax = my_ax, color = '#cbc3e3', edgecolor = 'purple',  linewidth = 0.3)


# plotting MIC safe circles -------

#natural land MIC
natural_mic.plot(ax = my_ax, 
                   color = '#ccebc5', 
                   edgecolor = 'darkgreen',  
                   linewidth = 1)

#manmade land MIC
manmade_mic.plot(ax = my_ax, 
                   color = 'lightgrey', 
                   edgecolor = 'black',  
                   linewidth = 1)


#CSO Plot ---------
cso2outfall.plot(ax = my_ax, color = 'black', linewidth = 1)
cso.plot(ax = my_ax, color = 'red', markersize =9)
outfall.plot(ax = my_ax, color = 'blue', markersize =9)


# save the result
savefig('out/Visualising Maps.png', bbox_inches='tight')
#print("done!")  

# --- NO CODE BELOW HERE ---

# report runtime
print(f"completed in: {perf_counter() - start_time} seconds")
