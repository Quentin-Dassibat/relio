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
import datetime
from osgeo import gdal, osr
gdal.UseExceptions()

#Set parameters
EPSG = 4326
modelRun = "DIST"

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
AoI = f"{hydrographicDirectory}/DEMx_SRTM30_wgs84_envelope5.tif"
bboxAoI = relio.extract_Rasterbbox(AoI)
modelRaster = f"{InputModelDirectory}/cmp_eur_ro12.grd"#f"{InputModelDirectory}/WBM_TerraClimate_OUTPUTQ_{modelRun}_mLTM_2000-2020.tif"


##################
# Execute module #
##################
globstart = datetime.datetime.now()

print("Split mutliband raster to single band rasters if more than one band")

src = modelRaster
load = gdal.Open(src)

if int(load.RasterCount)>1:

    relio.split_multiband(src,EPSG)
    
    print("Clip splitted rasters to the AoI")
    
    for b in range(12):
        
        src = f"{modelRaster[:-4]}_band{str(b+1)}.tif"
        #f"{InputModelDirectory}/WBM_TerraClimate_OUTPUTQ_{modelRun}_mLTM_2000-2020_band{b+1}.tif"
        dst = f"{src[:-4]}_clip.tif"
        relio.clip(src,dst,EPSG,bboxAoI)
        del src, dst

else:
    pass

load = None 

print("Clip raster to the AoI")

dst = f"{src[:-4]}_clip.tif"
relio.clip(modelRaster,dst,EPSG,bboxAoI)
del src, dst

print("Total Elapsed Time: ", datetime.datetime.now()-globstart)

with open(f"{tmpDirectory}/log.txt", 'a') as file:
    file.write(f"MODELinputs.py Elapsed Time: {str(datetime.datetime.now()-globstart)}\n")
