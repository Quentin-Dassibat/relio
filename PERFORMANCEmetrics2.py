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

#for catch in range(1,nb_subcatch+1): #catchment=0 is a "fake" catchment generated by pcraster.subcatchment(), so forget it
for catch in [17,34,83]:

    path = f"{outputDirectory}/StationsMergedResampling_{layer}_{modelRun}_band{str(bandNumber)}_catch{str(catch)}.gpkg" 
    
    if os.path.exists(path) is True:
    
        print("Catchment", str(catch))
    
        print("Load StationsMergedResampling layer")
        gdf = gpd.read_file(path)
        
        print("Compute perfromance metrics") #same metrics as in Wisser et al 2010, p.7
        
        #Mean Biased Error = Sigma_i(PRED_i - OBS_i) / nb_OBS
        gdf[f"PRED-OBS_month{str(bandNumber)}"] = gdf[f"ResampledDischarge_month{str(bandNumber)}_km3/yr"] - gdf[f"{layer}_km3/yr"]
        gdf[f"MB_month{str(bandNumber)}"] = gdf[f"PRED-OBS_month{str(bandNumber)}"].sum()/len(gdf)
        #Mean Absolute Error = Sigma_i( abs(PRED_i - OBS_i) ) / nb_OBS
        gdf[f"MAE_month{str(bandNumber)}"] = np.absolute(gdf[f"PRED-OBS_month{str(bandNumber)}"].sum())/len(gdf)
        #Relative Mean Biased Error = Sigma_i((PRED_i - OBS_i)/OBS_i) / nb_OBS
        gdf[f"PRED-OBS/OBS_month{str(bandNumber)}"] = gdf[f"PRED-OBS_month{str(bandNumber)}"]/gdf[f"{layer}_km3/yr"]
        gdf[f"RMBE_month{str(bandNumber)}"] = gdf[f"PRED-OBS/OBS_month{str(bandNumber)}"].sum()/len(gdf)
        #Relative Mean Absolute Error = Sigma_i( abs(PRED_i - OBS_i) ) / nb_OBS
        gdf[f"RMAE_month{str(bandNumber)}"] = np.absolute(gdf[f"PRED-OBS/OBS_month{str(bandNumber)}"].sum())/len(gdf)

        #Spearman coefficient
        #tmp = gdf.drop(labels="geometry",axis=1)
        coeff = gdf[f"{layer}_km3/yr"].corr(gdf[f"ResampledDischarge_month{str(bandNumber)}_km3/yr"], method="spearman")
        gdf.loc[:,f"Spearman_QOBSvsQPRED_month{str(bandNumber)}"] = coeff
        

        gdf.to_file(f"{tmpDirectory}/StationsMergedResampling_MMFmu_month{str(bandNumber)}_{str(timeRange[0])}{str(timeRange[1])}_catch{str(catch)}_metrics.gpkg")
        
        print("Write to disk: add dataframe for new month processed to the file that gather all months for a same catchment")

        dst = f"{tmpDirectory}/StationsMergedResampling_catch{str(catch)}_metrics.gpkg"

        if bandNumber == 1:
            
            new = gdf[["code_station",
                       f"MMFmu_month{str(bandNumber)}_{str(timeRange[0])}{str(timeRange[1])}_km3/yr",
                       f"ResampledDischarge_month{str(bandNumber)}_km3/yr",
                       f"PRED-OBS/OBS_month{str(bandNumber)}",
                       f"RMBE_month{str(bandNumber)}",
                       f"Spearman_QOBSvsQPRED_month{str(bandNumber)}","geometry"]]
            new2gdf = gpd.GeoDataFrame(new, crs=f"EPSG:{str(EPSG)}")
            new2gdf.set_geometry("geometry",inplace=True)
            new2gdf.to_file(dst)

            del new, new2gdf

            print(dst)

        else:
                
            old = gpd.read_file(dst)
            new = gdf[["code_station",
                       f"MMFmu_month{str(bandNumber)}_{str(timeRange[0])}{str(timeRange[1])}_km3/yr",
                       f"ResampledDischarge_month{str(bandNumber)}_km3/yr",
                       f"PRED-OBS/OBS_month{str(bandNumber)}",
                       f"RMBE_month{str(bandNumber)}",
                       f"Spearman_QOBSvsQPRED_month{str(bandNumber)}"]]
            merge = old.merge(new,left_on="code_station",right_on="code_station",how="left")
            merge2gdf = gpd.GeoDataFrame(merge, crs=f"EPSG:{str(EPSG)}")
            merge2gdf.set_geometry("geometry",inplace=True)
            merge2gdf.to_file(dst)
            
            print(dst)
            
            del old, new, merge, merge2gdf

        del gdf, dst

    else:
        print(f"{path} does not exist")
        

print("Total Elapsed Time: ", datetime.datetime.now()-globstart)

with open(f"{tmpDirectory}/log.txt", "a") as file:
    file.write(f"PERFORMANCEmetrics2.py Elapsed Time: {str(datetime.datetime.now()-globstart)}\n")