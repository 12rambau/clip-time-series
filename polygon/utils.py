from shapely.geometry import Point
from math import sqrt
import os
from datetime import datetime

import ee 

from parameters import square_size

ee.Initialize()

#########################
####   constants      ###
#########################
end_year = datetime.now().year
nb_line = 4
nb_col = 5
sources = ['landsat', 'sentinel']

##############################
#####     folders          ###
##############################
def create_folder(pathname):
    if not os.path.exists(pathname):
        os.makedirs(pathname)
    return pathname

def getResultDir():
    pathname = os.path.join(os.path.expanduser('~'), 'clip_results') + '/'
    return create_folder(pathname)

def getTmpDir():
    pathname = os.path.join(getResultDir(), 'tmp') + '/'
    return create_folder(pathname)



########################
##   functions        ##
########################

def to_square(polygon):
    
    minx, miny, maxx, maxy = polygon.bounds
    
    #min size in latitude (appro)
    min_size = square_size/111
    
    # get the centroid
    centroid = [(maxx+minx)/2, (maxy+miny)/2]
    # get the diagonal
    diagonal = max(min_size, sqrt((maxx-minx)**2+(maxy-miny)**2))
    
    return Point(centroid).buffer(diagonal/2, cap_style=3)

##########################
##     staelites inputs ##
##########################
def getPositionPdf(i):  
    """Return the position of the square on the pdf page"""
    return [int(i/5), i%5]

def getSatellites(sources):
    
    satellites = {}
    
    if 'sentinel' in sources:
        satellites.update({'sentinel_2': 'COPERNICUS/S2_SR'})
        
    if 'landsat' in sources:
        satellites.update({
            'landsat_8': 'LANDSAT/LC08/C01/T1_SR',
            'landsat_5': 'LANDSAT/LT05/C01/T1_SR',
            'landsat_7': 'LANDSAT/LE07/C01/T1_SR',
        })
        
    return satellites

def getScale(satellite):
    scale = {
        'sentinel_2': 10,
        'landsat_5': 30, 
        'landsat_7': 30,
        'landsat_8': 30
    }
    
    return scale[satellite]

def getShortname(satellite):
    short = {
        'sentinel_2': 'S2',
        'landsat_5': 'L5', 
        'landsat_7': 'L7',
        'landsat_8': 'L8'
    }
    
    return short[satellite]
        

def getAvailableBands():
    """give the bands composition for each name. 
    0 being the landsat 7, 
    1 landsat 5, 
    2, landsat 8 
    3: sentinel 2"""
    
    bands = {
        'Red, Green, Blue' : {
            'landsat_7': ['B3', 'B2', 'B1'], 
            'landsat_5': ['B3', 'B2', 'B1'],
            'landsat_8': ['B4', 'B3', 'B2'],
            'sentinel_2': ['B4', 'B3', 'B2']
        },
        'Nir, Red, Green' : {
            'landsat_7': ['B4', 'B3', 'B2'], 
            'landsat_5': ['B4', 'B3', 'B2'],
            'landsat_8': ['B5', 'B4', 'B3'],
            'sentinel_2': ['B8', 'B4', 'B3']
        },
        'Nir, Swir1, Red' : {
            'landsat_7': ['B4', 'B5', 'B3'],
            'landsat_5': ['B4', 'B5', 'B3'],
            'landsat_8': ['B5', 'B6', 'B4'],
            'sentinel_2': ['B8', 'B11', 'B4']
        },
        'Swir2, Nir, Red' : {
            'landsat_7': ['B7', 'B4', 'B3'], 
            'landsat_5': ['B7', 'B4', 'B3'],
            'landsat_8': ['B7', 'B5', 'B4'],
            'sentinel_2': ['B12', 'B8', 'B4']
        },
        'Swir2, Swir1, Red' : {
            'landsat_7': ['B7', 'B5', 'B3'], 
            'landsat_5': ['B7', 'B5', 'B3'],
            'landsat_8': ['B7', 'B6', 'B4'],
            'sentinel_2': ['B12', 'B11', 'B4']
        },
        'Swir2, Nir, Green' : {
            'landsat_7': ['B7', 'B4', 'B2'], 
            'landsat_5': ['B7', 'B4', 'B2'],
            'landsat_8': ['B7', 'B5', 'B3'],
            'sentinel_2': ['B12', 'B8', 'B3']
        },
        'ndvi' : { #2 useful bands nir and red 
            'landsat_7': ['B4', 'B3'], 
            'landsat_5': ['B4', 'B3'],
            'landsat_8': ['B5', 'B4'],
            'sentinel_2': ['B8', 'B4']
        },
        'ndwi' : { #2 useful bands nir and swir 
            'landsat_7': ['B4', 'B5'], 
            'landsat_5': ['B4', 'B5'],
            'landsat_8': ['B5', 'B6'],
            'sentinel_2': ['B8', 'B11']
        }
    }
    
    return bands

def getCloudMask(satelliteId):
    """ return the cloud masking function adapted to the apropriate satellite"""
    
    if satelliteId in ['landsat_5', 'landsat_7']:
        def cloudMask(image):
            qa = image.select('pixel_qa')
            # If the cloud bit (5) is set and the cloud confidence (7) is high
            # or the cloud shadow bit is set (3), then it's a bad pixel.
            cloud = qa.bitwiseAnd(1 << 5).And(qa.bitwiseAnd(1 << 7)).Or(qa.bitwiseAnd(1 << 3))
            # Remove edge pixels that don't occur in all bands
            mask2 = image.mask().reduce(ee.Reducer.min())
            
            return image.updateMask(cloud.Not()).updateMask(mask2)
    elif satelliteId == 'landsat_8':
        def cloudMask(image):
            # Bits 3 and 5 are cloud shadow and cloud, respectively.
            cloudShadowBitMask = (1 << 3)
            cloudsBitMask = (1 << 5)
            # Get the pixel QA band.
            qa = image.select('pixel_qa')
            # Both flags should be set to zero, indicating clear conditions.
            mask = qa.bitwiseAnd(cloudShadowBitMask).eq(0).And(qa.bitwiseAnd(cloudsBitMask).eq(0))
            
            return image.updateMask(mask)
    elif satelliteId == 'sentinel_2':
        def cloudMask(image):
            qa = image.select('QA60')
            #Bits 10 and 11 are clouds and cirrus, respectively.
            cloudBitMask = (1 << 10)
            cirrusBitMask = (1 << 11)
            #Both flags should be set to zero, indicating clear conditions.
            mask = qa.bitwiseAnd(cloudBitMask).eq(0).And(qa.bitwiseAnd(cirrusBitMask).eq(0))
    
            return image.updateMask(mask)#.divide(10000)
    
    return cloudMask

def getImage(sources, bands, mask, year):
    
    start = str(year) + '-01-01'
    end = str(year) + '-12-31'
    
    #priority selector for satellites
    for satelliteId in getSatellites(sources):
        dataset = ee.ImageCollection(getSatellites(sources)[satelliteId]) \
            .filterDate(start, end) \
            .filterBounds(mask) \
            .map(getCloudMask(satelliteId))
        
        if dataset.size().getInfo() > 0:
            satellite = satelliteId
            break
            
    clip = dataset.median().clip(mask).select(getAvailableBands()[bands][satelliteId])
    
    return (clip, satelliteId)
    


