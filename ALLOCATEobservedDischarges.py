# Copyright (c) Quentin DASSIBAT <qdassibat@gmail.com>

#Ecole des Mines de Saint-Etienne (EMSE)
#Ecole Nationale des Travaux Publics de l'Etat (ENTPE)
#Ecole Urbaine de Lyon (EUL)

# Source Code License (GPLv3)

#This software and its source code are licensed under the GNU General Public License (GPL), version 3.0 or later. See the LICENSE file for details.

# Output License (CC BY 4.0)

#Any outputs generated by this software, such as data files, images, or other results, are licensed under the Creative Commons Attribution 4.0 International License (CC BY 4.0).

#You are free to share, adapt, and use these outputs, provided you give appropriate credit to the original author(s). See the LICENSE file for details.

# For details about each license, please refer to:
#- GNU General Public License (GPL), version 3.0: https://www.gnu.org/licenses/gpl-3.0.html
#- Creative Commons Attribution 4.0 International License (CC BY 4.0): http://creativecommons.org/licenses/by/4.0/ 


##################
# Set parameters #
##################

#Import libraries
import os
import relio
import numpy as np
import geopandas as gpd
from osgeo import gdal, osr
gdal.UseExceptions()
import datetime

#Set path and working directories
wd = os.getcwd()
InputModelDirectory = f"{wd}/MODEL_inputs"
hydrographicDirectory = f"{wd}/HYDRO_inputs"

tmpDirectory = f"{wd}/tmp"
if os.path.isdir(tmpDirectory) is False:
    os.mkdir(f"{wd}/tmp")
else:
    pass

outputDirectory = f"{wd}/RESAMPLINGoutputs"
if os.path.isdir(outputDirectory) is False:
    os.mkdir(f"{wd}/RESAMPLINGoutputs")
else:
    pass

#Parameters 
timeRange = [2000,2020]
EPSG = 4326
epsilonAccuflux = 1e3
epsilonOutlet = 1e3
modelRun = "DIST"
bandNumber = 12
layer = f"MMFmu_month{str(bandNumber)}_{str(timeRange[0])}{str(timeRange[1])}"
#Number of WBM catchments
subcatchmentsRaster = f"{outputDirectory}/OutletsLocations_sup{str(epsilonOutlet)}_modDIST_band1_subcatchments.map"
r = gdal.Open(subcatchmentsRaster)
band = r.GetRasterBand(1)
subcatch = band.ReadAsArray().astype(int)
nb_subcatch = np.max(subcatch)
del r


##################
# Execute module #
##################
globstart = datetime.datetime.now()

print("Band Number",bandNumber)

print("Join StationsMergedAccuflux_correct with station MMF month_#")
#StationsMergedCorrect was created based on MMF_month1 for calibration purpose, now for other months, the calibrated location of stations is kept but discharge values are updated for current month_#
if bandNumber != 1:
    
    src = f"{tmpDirectory}/StationsMergedAccuflux_MMFmu_month1_{str(timeRange[0])}{str(timeRange[1])}_correct.gpkg"
    StationsMergedAccuflux_correct = gpd.read_file(src)
    del src
    src = f"{hydrographicDirectory}/DEMx_SRTM30_wgs84_gauging_stations_mmf_period{str(timeRange[0])}{str(timeRange[1])}.gpkg"
    StationsDischarges = gpd.read_file(src)
    del src
    StationsMergedAccuflux_correct_clip = StationsMergedAccuflux_correct[["code_station","index_raster","values","uid","station_coordinates","geometry"]]
    StationsDischargeCurrentMonth = StationsDischarges[["code_station",layer]]
    StationsMergedAccuflux = StationsMergedAccuflux_correct_clip.merge(StationsDischargeCurrentMonth,left_on="code_station",right_on="code_station",how="left")
    StationsMergedAccuflux2gdf = gpd.GeoDataFrame(StationsMergedAccuflux, crs=f"EPSG:{str(EPSG)}")
    StationsMergedAccuflux2gdf.set_geometry("geometry",inplace=True)
    StationsMergedAccuflux2gdf.to_file(f"{tmpDirectory}/StationsMergedAccuflux_{layer}.gpkg")
    del StationsMergedAccuflux_correct, StationsDischargeCurrentMonth, StationsMergedAccuflux_correct_clip, StationsMergedAccuflux, StationsMergedAccuflux2gdf

    src = f"{tmpDirectory}/StationsMergedAccuflux_{layer}.gpkg"
    
else:
    
    src = f"{tmpDirectory}/StationsMergedAccuflux_{layer}_correct.gpkg"


print("Clip StationsMergedAccuflux_correct to each subcatchment") 

StationsMergedAccuflux = gpd.read_file(src)
del src
vect = f"{tmpDirectory}/OutletsLocations_sup{str(epsilonOutlet)}_modDIST_band1_subcatchments_polygons.gpkg"
if os.path.exists(vect) is False:
    relio.raster_to_polygons(subcatchmentsRaster,vect,EPSG,"catch_id")
    src = f"{tmpDirectory}/OutletsLocations_sup{str(epsilonOutlet)}_modDIST_band1_subcatchments_polygons.gpkg"
    catchments = gpd.read_file(src)
    del src
else:
    src = f"{tmpDirectory}/OutletsLocations_sup{str(epsilonOutlet)}_modDIST_band1_subcatchments_polygons.gpkg"
    catchments = gpd.read_file(src)
    del src


for catch in [17,34,83]: #range(1,nb_subcatch+1): #catchment=0 is a "fake" catchment generated by pcraster.subcatchment(), so forget it

    print("Catchment", str(catch))

    print("Clip StationsMergedResampling with each catchment's extent")
    m = catchments['catch_id'] == catch
    current_catchment = catchments.loc[m]
    clipped = StationsMergedAccuflux.clip(current_catchment,keep_geom_type=True)
    del m, current_catchment

    if len(clipped) == 0:
        pass
        
    else:
        
        print("Compute predicted discharge values")
        accufluxOut = clipped['values'].max()
        dischargeOut = clipped.loc[clipped['values'].idxmax(), layer]
        clipped['rho_pixel'] = clipped['values']/accufluxOut 
        clipped[f"Qout_pixel_month{str(bandNumber)}"] = dischargeOut*clipped['rho_pixel']
    
        print("Write to disk")
        dst = f"{tmpDirectory}/StationsMergedAccuflux_{layer}_catch{str(catch)}.gpkg"        
        clipped.to_file(dst)
        del dst, clipped

print("Total Elapsed Time: ", datetime.datetime.now()-globstart)

with open(f"{tmpDirectory}/log.txt", 'a') as file:
    file.write(f"ALLOCATEobservedDischarges.py Elapsed Time: {str(datetime.datetime.now()-globstart)}\n")
