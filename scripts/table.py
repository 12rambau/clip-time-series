import os
from pathlib import Path
import shutil

import pandas as pd 
import geemap

from utils import messages as ms

def isConform(file):
    """perform several checks on the file given by the user retrun an error message if something is wrong else 0"""
    
    #check if the file exist
    if not os.path.isfile(file):
        return ms.NOT_A_FILE.format(file)
    
    #try to read the file 
    try:
        df = pd.read_csv(file)
    except:
        return ms.ERROR_READING_FILE.format(file)
    
    #validate
    return 0

def setMap(pts, m):
    """create a map and a df list of points"""
    
    #add the pts on the map
    markers, popups = [], []
    for index, row in pts.iterrows():
        marker = geemap.Marker(location=(row.lat, row.lng), draggable=False)
        markers.append(marker)
        popups.append(index)
        
    #remove the previous markers
    if len(m.layers) > 1: #only 1 layer + cardoDB.Positron
        m.remove_last_layer()
        
    #display on the map
    marker_cluster = geemap.MarkerCluster(markers=tuple(markers), popups=popups)
    m.add_layer(marker_cluster)
    
    #recenter the map
    m.set_center(0, 0, zoom=2)

    return 

def download_test_file(output):
    
    #get the file name 
    filename = 'clip_test_points.csv'
    
    # get the test and download folders
    dst_file = Path('~', 'downloads').expanduser()
    src_file = Path(__file__).parents[1].joinpath('test_data', filename)
    
    # download the file to the download directory 
    shutil.copy(src_file, dst_file)
    
    # update the output
    output.add_live_msg(f"The test dataset have been downloaded. It will be available in the `~/downloads/{filename}` folder of your sepal account.") #" The file has been automatically set as source file in the select table tile.")
    
    return dst_file 