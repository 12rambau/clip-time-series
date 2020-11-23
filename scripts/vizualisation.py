import traitlets

import ipyvuetify as v

def set_msg(pts, bands_combo, source_name, basename, start, end, square_size):
    
    nb_pts = len(pts)
    
    #compute the surface 
    pts_conform = pts.to_crs('ESRI:54009')
    minx, miny, maxx, maxy = pts_conform.total_bounds
    surface = (maxx-minx)*(maxy-miny)/10e6 #in km2
    
    msg = f"""
        <div>
            <p>
                You're about to launch the following downloading :
            <p>
            <ul>
                <li>
                    <b>{nb_pts}</b> points distributed on <b>{surface:.2f}</b> km\u00B2
                </li>
                <li>
                    Using the images coming from <b>{source_name}</b> satellites
                <li>
                    Using the <b>{bands_combo}</b> band combination
                </li>
                <li>
                    Using images from <b>{start}</b> to <b>{end}</b>
                </li>
                <li>
                    Using squares of <b>{square_size}x{square_size}</b> km\u00B2  
                </li>
                <li>
                    Saved in a file using <b>{basename}</b> as a basename
                </li>
            </ul>
            
            <p>
                If you agree with these input you can start the downloading, if not please change the inputs in the previous tiles
            </p>
        </div>
    """
    
    #create a Html widget
    class MyHTML(v.VuetifyTemplate):
        template = traitlets.Unicode(msg).tag(sync=True)
    
    
    return MyHTML()
    
    
    
    
    