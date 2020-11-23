from pathlib import Path
from gdrive import gdrive
import os 
import ee 
import time
import shutil

from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import rasterio as rio
import numpy as np
import gdal
import gee 
from sepal_ui.scripts import gee as gs

from utils import *
from parameters import *

ee.Initialize()

def createPDF(file, df, raw_polygons, bands, sources, output):
    
    #get the filename
    filename = Path(file).stem
    
    #extract the bands to use them in names 
    name_bands = '_'.join(bands.split(', '))
    
    #pdf name 
    pdf_file = getResultDir() + '{}_{}.pdf'.format(filename, name_bands)
    
    if os.path.isfile(pdf_file):
        output.add_live_msg('Pdf already exist', 'success')
        return pdf_file
    
    #start the drive handler 
    drive_handler = gdrive() 
    
    #create a filename list 
    descriptions = {}
    for year in range(start_year, end_year + 1):
        descriptions[year] = {}
        for index, row in df.iterrows():
            descriptions[year][row['id']] = '{}_{}_{}_pt_{}'.format(filename, name_bands, year, row['id'])
    
    #load all the data in gdrive 
    satellites = {} #contain the names of the used satellites
    task_list = []
    for year in range(start_year, end_year + 1):
        for index, row in df.iterrows():
        
            #launch it only if the file is not in tmp, or in gdrive
            task_name = descriptions[year][row['id']]
            file = getTmpDir() + task_name + '.tif'
            
            image, satellites[year] = getImage(sources, bands, row['ee_geometry'], year)
            
            
            output.add_live_msg('exporting year {} for point {}'.format(year, row['id']))
            if not os.path.isfile(file):
                if drive_handler.get_files(task_name) == []:
                    
                    task_config = {
                        'image':image,
                        'description': task_name,
                        'scale': getScale(satellites[year]),
                        'region': row['ee_geometry'],
                        'maxPixels': 10e12
                    }
            
                    task = ee.batch.Export.image.toDrive(**task_config)
                    task.start()
                    
                    task_list.append(task_name)
                    
    
    #check the exportation evolution
    state = gee.custom_wait_for_completion(task_list, output)
    output.add_live_msg('Export to drive finished', 'success')
    time.sleep(2)
    
    output.add_live_msg('Retrieve to sepal')
    
    #retreive all the file ids 
    filesId = []
    for year in range(start_year, end_year + 1):
        for index, row in df.iterrows():
            
            task_name = descriptions[year][row['id']]
            file = getTmpDir() + task_name + '.tif'
            
            if not os.path.isfile(file):
                filesId += drive_handler.get_files(task_name)
    
    #download the files   
    output.add_live_msg('Download files')
    drive_handler.download_files(filesId, getTmpDir())     
    
    #remove the files from gdrive 
    output.add_live_msg('Remove from gdrive')
    drive_handler.delete_files(filesId)            
    
    #create the resulting pdf
    with PdfPages(pdf_file) as pdf:
        #each point is display on one single page
        for index, row in df.iterrows():
            
            page_title = "Polygon_{} ({})".format(
                int(row['id']), 
                row['Name'], 
            )
            
            output.add_live_msg('Creating pages for pt {}'.format(int(row['id'])))
                  
            fig, axes = plt.subplots(nb_line, nb_col, figsize=(11.69,8.27), dpi=500)
            fig.suptitle(page_title, fontsize=16, fontweight ="bold")
            
            #display the images in a fig and export it as a pdf page
            cpt = 0
            for year in range(start_year, end_year + 1):
                
                #laod the file 
                file = getTmpDir() + descriptions[year][row['id']] + '.tif'                
    
                #with rio.open(tmp_file) as f:
                with rio.open(file) as f:
                    data = f.read([1, 2, 3], masked=True)
                    x_min, y_min, x_max, y_max = list(f.bounds)
                
                bands = [] 
                for i in range(3):
                    band = data[i]
                    h_, bin_ = np.histogram(band[np.isfinite(band)].flatten(), 3000, density=True) #remove the NaN from the analysis
    
                    cdf = h_.cumsum() # cumulative distribution function
                    cdf = 3000 * cdf / cdf[-1] # normalize
    
                    # use linear interpolation of cdf to find new pixel values
                    band_equalized = np.interp(band.flatten(), bin_[:-1], cdf)
                    band_equalized = band_equalized.reshape(band.shape)
        
                    bands.append(band_equalized)
    
                data = np.stack( bands, axis=0 )

                data = data/3000
                data = data.clip(0, 1)
                data = np.transpose(data,[1,2,0])
            
                x_polygon, y_polygon = raw_polygons.loc[index]['geometry'].exterior.coords.xy
            
                ax = axes[getPositionPdf(cpt)[0], getPositionPdf(cpt)[1]]
                ax.imshow(data, interpolation='nearest', extent=[x_min, x_max, y_min, y_max])
                ax.plot(x_polygon, y_polygon, color=polygon_color, linewidth=polygon_width)
                ax.set_title(str(year) + ' ' + getShortname(satellites[year]), x=.0, y=.9, fontsize='small', backgroundcolor='white', ha='left')
                ax.axis('off')
                ax.set_aspect('equal', 'box') 
                
                cpt += 1
            
            #finish the line with empty plots 
            while cpt < nb_line*nb_col:
                ax = axes[getPositionPdf(cpt)[0], getPositionPdf(cpt)[1]]
                ax.axis('off')
                ax.set_aspect('equal', 'box')
                
                cpt += 1
            
            #save the page 
            plt.tight_layout()
            pdf.savefig(fig)
            plt.close()
            
    #flush the tmp repository 
    #shutil.rmtree(getTmpDir())
    
    output.add_live_msg('PDF output finished', 'success')
    
    return pdf_file