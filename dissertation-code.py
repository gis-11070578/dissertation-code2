"""
Dissertation - [insert title here]
@author [11070578]
"""
from time import perf_counter

# set start time
start_time = perf_counter()	

# --- NO CODE ABOVE HERE -------

# All Imports -------------------------------

import numpy as np
import geopandas as gpd
from shapely import unary_union
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from shapely import maximum_inscribed_circle
from shapely.geometry import Point, LineString
from matplotlib_scalebar.scalebar import ScaleBar
from matplotlib.pyplot import subplots, savefig, title

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
MAX_RADIUS = 20 

# max radius change to 10 or 20m based on previous tanks in the same catchment 

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
        
        #OR radius is smaller than min radius - skip
        if radius < MIN_RADIUS:
            continue 
        
        #INSTEAD OF disgarding radius larger than max radius
        #cap radius at max size 
        if radius > MAX_RADIUS: 
            radius = MAX_RADIUS
        
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
floodzone_2 = gpd.read_file("data/EAFloodZone_2_Clip.shp")

#load all flood zone 3 - raster 
floodzone_3 = gpd.read_file("data/EAFloodZone_3_Clip.shp")

#ensure all the same CRS ---------

contours = contours.to_crs(landuse.crs)
cso = cso.to_crs(landuse.crs)
outfall = outfall.to_crs(landuse.crs)
cso2outfall = cso2outfall.to_crs(landuse.crs)
floodzone_2 = floodzone_2.to_crs(landuse.crs)
floodzone_3 = floodzone_3.to_crs(landuse.crs)


# pre-processing for plotting the maps ------
#select by attributes - rivers
inland_water = landuse[landuse["Name"].str.contains("Inland Water")]

#select by attributes - roads
roads = landuse[landuse["Name"].str.contains("Roads")]

#select by attributes - buildings
buildings = landuse[landuse["Name"].str.contains("Buildings")]


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
landuse_MIC_safe = gpd.pd.concat([natural_MIC_safe, manmade_MIC_safe])

#export to shapefile
landuse_MIC_safe.to_file("out/landuse_MIC_safe.shp")


# SECTION 3 - Creating weighted overlays (user defined) ------------------

#read file for combined land use MIC - only natural and manmade surfaces
MIC_landuse = gpd.read_file("out/landuse_MIC_safe.shp")

# USER DEFINED WEIGHTING (must sum up to 1.0) ------
# creating 5 different scenarios because need to have everything on one grid
# create dictionary for each scenario with diff weights

scenarios = {
#even scenario weighting so all is 0.2 
    "Even Weighting": {
    "W_DISTANCE": 0.20,
    "W_LANDUSE": 0.20,
    "W_TANKSIZE": 0.20,
    "W_FLOODZONE_2": 0.20,
    "W_FLOODZONE_3": 0.20}, 
    
#distance priority - then landuse - then tank - then FZ
    "Distance Priority": {
    "W_DISTANCE": 0.50,
    "W_LANDUSE": 0.20,
    "W_TANKSIZE": 0.15,
    "W_FLOODZONE_2": 0.075,
    "W_FLOODZONE_3": 0.075}, 
  
#flood zones priority - then distance + landuse same - then tank
    "Flood Zones Priority": {
    "W_DISTANCE": 0.15,
    "W_LANDUSE": 0.15,
    "W_TANKSIZE": 0.10,
    "W_FLOODZONE_2": 0.30,
    "W_FLOODZONE_3": 0.30}, 

#tanksize priority - then distance - then landuse - then FZ
    "Tank Size Priority": {
    "W_DISTANCE": 0.20,
    "W_LANDUSE": 0.15,
    "W_TANKSIZE": 0.50,
    "W_FLOODZONE_2": 0.075,
    "W_FLOODZONE_3": 0.075}, 
    
#landuse priority - then distance - then tanksize - then FZ
    "Land Use Priority": {
    "W_DISTANCE": 0.20,
    "W_LANDUSE": 0.50,
    "W_TANKSIZE": 0.15,
    "W_FLOODZONE_2": 0.075,
    "W_FLOODZONE_3": 0.075},

#distance and flood priority - then distance - then tanksize - then FZ
    "Distance and Flood Priority": {
    "W_DISTANCE": 0.30,
    "W_LANDUSE": 0.10,
    "W_TANKSIZE": 0.10,
    "W_FLOODZONE_2": 0.25,
    "W_FLOODZONE_3": 0.25}}



# DISTANCE FROM CSO - NEED LOCATION -----
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


# LANDUSE SCORING -------
#loop through each row in the MIC circles
for i, row in MIC_landuse.iterrows(): 
    
    #circle geometry for each MIC 
    circle = row.geometry

    #if mic intersects manmade surfaces - score new field
    if manmade_land.intersects(circle).any(): 
        MIC_landuse.loc[i, "score_landuse"] = 1
    
    #if mic intersects natural land - score new field
    elif natural_land.intersects(circle).any(): 
        MIC_landuse.loc[i, "score_landuse"] = 0.5
    
    #else then score 0
    else: 
        MIC_landuse.loc[i, "score_landuse"] = 0.3


# TANK SIZE SCORING -------
#control variable
TANK_HEIGHT = 10

MIN_AREA = np.pi * MIN_RADIUS**2 
MAX_AREA = np.pi * MAX_RADIUS**2

#creating a new field with 0
MIC_landuse["score_tanksize"] = 0.0 

#loop through each row in the MIC circles
for i, row in MIC_landuse.iterrows(): 
    
    #geometry of the area circles
    tank_area = row.geometry.area
    
    #formula - volume based score
    score = ((tank_area * TANK_HEIGHT) - (MIN_AREA * TANK_HEIGHT)) / ((MAX_AREA * TANK_HEIGHT) - (MIN_AREA * TANK_HEIGHT))

    #values between 0 and 1 
    if score < 0: 
        score = 0.0 
    elif score > 1: 
        score = 1.0
        
    MIC_landuse.loc[i, "score_tanksize"] = score


# FLOOD RISK SCORING ------

#insuring that all non intersecting circles are highly rated
MIC_landuse["score_flood_2"] = 1.0
MIC_landuse["score_flood_3"] = 1.0

# FLOOD ZONE 2 ----
#flood zone 2 - medium risk 

#loop through each row in the MIC circles
for i, row in MIC_landuse.iterrows(): 
    
    #circle geometry for each MIC 
    circle = row.geometry

    #if mic intersect with flood zone 2 - score (between 0-1)
    if floodzone_2.intersects(circle).any():
        MIC_landuse.loc[i, "score_flood_2"] = 0.4

# FLOOD ZONE 3 ----
#flood zone 3 - high risk 

    #if mic intersect with flood zone 3 - score (between 0-1)
    if floodzone_3.intersects(circle).any():
        MIC_landuse.loc[i, "score_flood_3"] = 0.5



# PLOTTING ALL 5 SCENARIOS + CALCS USING LOOP -----------------------------------

# plot the dataset - 5 different maps -----------
fig, my_ax = subplots(2, 3, figsize=(14, 9))
fig.suptitle('Tank Sensitivity Testing - 5 Differently Weighted Scenarios ', fontsize=20, weight='bold')

#flattening 2D array into 1D - so that its easy to loop
axes = my_ax.flatten()



# FINAL WEIGHTING SCORE LOOP -------

#loop through each each scenario and do the calc weights
#for each index, in each ax, loop through dictionary scenarios and their weights
for idx, (ax, (scenario_name, weights)) in enumerate(zip(axes, scenarios.items())): 
    
    #for each scenario looping through
    #copying base dataset so that each scenario is different
    scenario_gdf = MIC_landuse.copy()
    
    #final calulating of score - sum(score) x weight
    #directly creating new field that had calculation
    scenario_gdf["final_score"] = (
    
        scenario_gdf["score_distance"] * weights["W_DISTANCE"] + 
        scenario_gdf["score_landuse"] * weights["W_LANDUSE"] +
        scenario_gdf["score_tanksize"] * weights["W_TANKSIZE"] +
        scenario_gdf["score_flood_2"] * weights["W_FLOODZONE_2"] +
        scenario_gdf["score_flood_3"] * weights["W_FLOODZONE_3"])
    
    # final_score = sum([score * weight for score, weight in zip(scores, weights)])
    
    #EXPORT SHAPEFILE -----
    #exporting new shapefile independently - diff name
    scenario_gdf.to_file(f"out/MIC_{scenario_name}.shp")


    # looping the axes plot dataset -----------------
    # new variable ax is the index of each axis section
    #ax = my_ax[idx]
    
    #turn off axes 
    ax.axis('off')

    #creating title
    ax.set_title(f"{scenario_name} Map", fontsize = 12, weight='bold')

    #USER DEFINED PARAMETER
    #buffer around the border itself - to give us some context
    CSO_ZOOM_BUFFER = 350

    # extract the bounds from the CSO layer
    cso_buffer = cso.geometry.buffer(CSO_ZOOM_BUFFER)
    minx, miny, maxx, maxy = cso_buffer.total_bounds

    ax.set_xlim([minx, maxx])
    ax.set_ylim([miny, maxy])


    # plotting cleaned land use polygons -------
    #natural land cleaned
    natural_clean.plot(ax = ax, color = '#ccebc5', edgecolor = 'green',  linewidth = 0.3)

    #manmade land cleaned
    manmade_clean.plot(ax = ax, color = '#aa74b0', edgecolor = 'purple',  linewidth = 0.3)


    #land use extras ------
    #natural land cleaned
    inland_water.plot(ax = ax, color = 'lightblue', edgecolor = 'blue',  linewidth = 0.3)

    #natural land cleaned
    roads.plot(ax = ax, color = 'lightgrey', edgecolor = 'grey',  linewidth = 0.3)

    #natural land cleaned
    buildings.plot(ax = ax, color = 'lightgrey', edgecolor = 'grey',  linewidth = 0.3)


    #plotting flood zones -----
    # only for scenarios 3 and 6 - with flood zones 
    if scenario_name in ["Flood Zones Priority", "Distance and Flood Priority"]:
        
        #flood zone 2
        floodzone_2.plot(ax = ax, color = '#5CFFFC', edgecolor = 'lightblue',  linewidth = 0.5, alpha=0.5)

        #flood zone 3
        floodzone_3.plot(ax = ax, color = '#CACFFC', edgecolor = 'lightblue',  linewidth = 0.5, alpha=0.5)
    

    # plotting MIC safe circles -------
    #natural land MIC
    #natural_mic.plot(ax = my_ax, color = '#ccebc5', edgecolor = 'darkgreen',  linewidth = 1)

    #manmade land MIC
    #manmade_mic.plot(ax = my_ax, color = 'lightgrey', edgecolor = 'black',  linewidth = 1)


    #plotting the RESULT LAYER -------
    scenario_gdf.plot(
        ax=ax,
        column="final_score",
        cmap="Reds",
        legend=True,
        edgecolor="black",
        linewidth=0.6)

    #CSO Plot ---------
    cso.plot(ax = ax, color = 'yellow', edgecolor='black', markersize=20, linewidths=0.2)
    cso2outfall.plot(ax = ax, color = 'black', linewidth = 1)
    #outfall.plot(ax = ax, color = 'blue', markersize =12)


    # Extras on the map ---------

    # add north arrow
    # arrow - left/right, up/down, north sign up/down
    x, y, arrow_length = 0.95, 0.98, 0.1
    ax.annotate('N', xy=(x, y), xytext=(x, y-arrow_length),
                   arrowprops=dict(facecolor='black', width=5, headwidth=15),
                   ha='center', va='center', fontsize=10, xycoords=ax.transAxes)

    # add legend
    ax.legend(handles=[
        Patch(facecolor='#ccebc5', edgecolor='green', label="Natural Land"),
        Patch(facecolor='#aa74b0', edgecolor='purple', label="Manmade Surface"),
        Line2D([0], [0], color='black',  lw=2, label='CSO to Outfall' ),
        Line2D([0], [0], marker='o', linestyle='None', markerfacecolor='yellow', markeredgecolor='black', markersize=5, label='Lambridge CSO'),
        #Line2D([0], [0], marker='o', linestyle='None', markerfacecolor='blue', markeredgecolor='black', markersize=5, label='Lambridge Outfall')
        ],loc='upper left', fontsize=6)
        
    #adding flood zone legend only for 2 scenarios 
    if scenario_name in ["Flood Zones Priority", "Distance and Flood Priority"]:
        
        ax.legend(handles=[
        #flood zone 2 and 3 patch colours
        Patch(facecolor='#5CFFFC', edgecolor='lightblue', label="Flood Zone 2"),
        Patch(facecolor='#CACFFC', edgecolor='lightblue', label="Flood Zone 3")
        ],loc='upper left', fontsize=6)


# add scalebar - for all 
ax.add_artist(ScaleBar(dx=1, units="m", location="lower left", length_fraction=0.25))


#tight layout so theres no gaps
fig.tight_layout()

# save the result
savefig('out/All_Scenarios.png', bbox_inches='tight')
#print("done!")  

# --- NO CODE BELOW HERE ---

# report runtime
print(f"completed in: {perf_counter() - start_time} seconds")
