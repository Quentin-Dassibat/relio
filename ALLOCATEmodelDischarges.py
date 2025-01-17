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

#Set parameters
EPSG = 4326
epsilonAccuflux = 1e3
epsilonOutlet = 1e3
modelRun = "DIST"
bandNumber = 12
#Number of WBM catchments
subcatchmentsRaster = f"{outputDirectory}/OutletsLocations_sup{str(epsilonOutlet)}_mod{modelRun}_band1_subcatchments.map"
r = gdal.Open(subcatchmentsRaster)
band = r.GetRasterBand(1)
subcatch = band.ReadAsArray().astype(int)
nb_subcatch = np.max(subcatch)
del r


##################
# Execute module #
##################
globstart = datetime.datetime.now()

print("Load subcatchments raster")


print("Clip acculfux map to each subcatchment") 

acc = f"{hydrographicDirectory}/DEMx_SRTM30_wgs84_pcraster_accuflux_sup{str(epsilonAccuflux)}.tif"
#for catch in range(1,nb_subcatch+1):
catchList = [17,34,83]
for catch in catchList:
    if os.path.exists(f"{hydrographicDirectory}/DEMx_SRTM30_wgs84_pcraster_accuflux_sup{str(epsilonAccuflux)}_catch{str(catch)}.tif") is False:
        relio.clip_accuflux_to_subcatchments(acc,subcatchmentsRaster,EPSG,catchList)
    else:
        pass
del acc

print("Allocate each subcatchment's discharge value to each pixel based on its weight in the acculfux map")

print("Get the correspondance matrix between catchment index and outlets id")
src = f"{outputDirectory}/OutletsDischarges_sup{str(epsilonOutlet)}_mod{modelRun}_band{str(bandNumber)}_points.gpkg"
ids = 'uid_outlets'
id_matrix = relio.getId_subcatchments(src,ids)

print("Convert each catchment accuflux to point geodataframe and allocate each catchment's discharge value")
outlets = gpd.read_file(f"{outputDirectory}/OutletsDischarges_sup{str(epsilonOutlet)}_mod{modelRun}_band{str(bandNumber)}_points.gpkg")
outlets['uid_outlets'] = outlets['uid_outlets'].astype("string")

#for catch in range(1,nb_subcatch+1): #catchment=0 is a "fake" catchment generated by pcraster.subcatchment(), so forget it
for catch in [17,34,83]:

    print('Catchment',catch)
    start = datetime.datetime.now()
    
    print("Raster to geodataframe")
    src = f"{hydrographicDirectory}/DEMx_SRTM30_wgs84_pcraster_accuflux_sup{str(epsilonAccuflux)}_catch{str(catch)}.tif"
    d = relio.extract_cellsValues(src)
    g = relio.cells_to_points(d,EPSG)
    del src
    
    print("Get discharge and accuflux values at the catchment's outlet based on 'uid_outlets'")
    idx, uid = id_matrix[catch-1]
    mask = outlets['uid_outlets'] == str(uid)
    tmp = outlets.loc[mask]
    dischargeOut = tmp.iloc[0]['Qout_outlet']
    accufluxOut = tmp.iloc[0]['AccufluxValues']
    del mask, tmp
    
    print("Allocate discharge to each pixel based on its weighted accuflux value with reference the accuflux of the catchment's outlet")
    g['rho_pixel'] = g['values']/accufluxOut
    g[f"Qout_pixel_month{str(bandNumber)}"] = dischargeOut*g['rho_pixel']
    
    print("Export to raster") 
    mask = f"{hydrographicDirectory}/DEMx_SRTM30_wgs84_pcraster_accuflux_sup{str(epsilonAccuflux)}_catch{str(catch)}.tif"
    dst = f"{outputDirectory}/ResampledDischarges_OutletSup{str(epsilonOutlet)}_mod{modelRun}_band{str(bandNumber)}_catch{str(catch)}.tif"
    relio.points_to_raster(g,f"Qout_pixel_month{str(bandNumber)}",mask,dst,EPSG)
    del mask, dst, g

    print("Elapsed Time: ", datetime.datetime.now()-start)

print("Total Elapsed Time: ", datetime.datetime.now()-globstart)

with open(f"{tmpDirectory}/log.txt", 'a') as file:
    file.write(f"ALLOCATEmodelDischarges.py Elapsed Time: {str(datetime.datetime.now()-globstart)}\n")
