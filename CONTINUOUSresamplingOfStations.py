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
import pandas as pd
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
EPSG = 4326
epsilonAccuflux = 1e3
epsilonOutlet = 1e3
modelRun = "DIST"
bandNumber = 12
timeRange = [2000,2020]
layer = f"MMFmu_month{str(bandNumber)}_{str(timeRange[0])}{str(timeRange[1])}"
DEM = f"{hydrographicDirectory}/DEMx_SRTM30_wgs84_envelope5.tif"
algo = "invdist"
param = ""


##################
# Execute module #
##################
globstart = datetime.datetime.now()


#Continuous resampling of a gauging stations layer from which biggest stations flows are extracted and then resampled to a SRTM30-like grid cells

print("Make a continuous resampling of 10 gauging stations accounting each for a 10th percentile of flow distribution")

src = f"{hydrographicDirectory}/DEMx_SRTM30_wgs84_gauging_stations_mmf_period{str(timeRange[0])}{str(timeRange[1])}.gpkg"
stations = gpd.read_file(src)
del src
points_list = []

for q in np.arange(0.1,1.1,0.1): #starts at quantile 10% and ends at quantile 100% with a 10% increment
    station = stations.loc[stations[layer] == stations[layer].quantile(q,interpolation='nearest')]
    points_list.append(station)
df_points = pd.concat(points_list)
dst = f"{tmpDirectory}/ContinuousResamplingOfStations_band{str(bandNumber)}_points2resample.gpkg"
df_points.to_file(dst)
del dst, df_points
src = f"{tmpDirectory}/ContinuousResamplingOfStations_band{str(bandNumber)}_points2resample.gpkg"
dst = f"{tmpDirectory}/ContinuousResamplingOfStations_band{str(bandNumber)}_points2resample.csv"
relio.convert_to_csv(src,dst)
del src, dst 
src = f"{tmpDirectory}/ContinuousResamplingOfStations_band{str(bandNumber)}_points2resample.csv"
l = f"ContinuousResamplingOfStations_band{str(bandNumber)}_points2resample"
z = f"MMFmu_month{str(bandNumber)}_20002020"
relio.convert_to_vrt(src,l,z,"X","Y")
del src
src = f"{tmpDirectory}/ContinuousResamplingOfStations_band{str(bandNumber)}_points2resample.vrt"
relio.interpolate(src,l,DEM,EPSG,algo,param)
del src, l, z

print("Extract observed gauging discharges at resampled pixels")

#Load dataframes
src = f"{tmpDirectory}/ContinuousResamplingOfStations_band{str(bandNumber)}_points2resample_gridded_{algo}_{param}.tif"
dic = relio.extract_cellsValues(src)
resampled = relio.cells_to_points(dic,EPSG)
del src, dic
src = f"{hydrographicDirectory}/DEMx_SRTM30_wgs84_gauging_stations_mmf_period{str(timeRange[0])}{str(timeRange[1])}.gpkg"
observed = gpd.read_file(src)
del src
join = gpd.sjoin_nearest(observed,resampled,how='left',lsuffix='obs', rsuffix='pred')
#convert to km3 yr-1
conversion_factor = 1e-3*1e-9*60*60*24*365
join[f"{layer}_km3/yr"] = join[f"{layer}"]*conversion_factor
join.loc[:,f"ResampledDischarge_month{str(bandNumber)}_km3/yr"] = join.loc[:,"values"]
join.drop("values", axis=1, inplace=True)
#Clear dataframe
fields = ['code_station',f"{layer}_km3/yr",f"ResampledDischarge_month{str(bandNumber)}_km3/yr",'geometry']
gdf = join[fields]
#Compute error 
gdf['PRED-OBS/OBS'] = (gdf[f"ResampledDischarge_month{str(bandNumber)}_km3/yr"]-gdf[f"{layer}_km3/yr"])/gdf[f"{layer}_km3/yr"]

print("Save point geodataframe to disk")

dst = f"{outputDirectory}/ContinuousResamplingOfStations_{layer}_{algo}_{param}.gpkg"
gdf.to_file(dst)

print("Total Elapsed Time: ", datetime.datetime.now()-globstart)

with open(f"{tmpDirectory}/log.txt", 'a') as file:
    file.write(f"CONTINUOUSresamplingOfStations.py Elapsed Time: {str(datetime.datetime.now()-globstart)}\n")
