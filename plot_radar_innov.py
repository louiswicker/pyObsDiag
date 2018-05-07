
import pandas as pd
import numpy as np
from netcdftime import utime
import matplotlib.pyplot as plt
import sys, os, glob
from optparse import OptionParser
import datetime as dtime
import xarray as xr
import matplotlib as mpl
import matplotlib.cm as cm

import matplotlib.ticker as ticker
import matplotlib.dates as mdates
from pltbook import nice_mxmnintvl, nice_clevels

time_format = "%Y-%m-%d_%H:%M:%S"
day_utime   = utime("days since 1601-01-01 00:00:00")
sec_utime   = utime("seconds since 1970-01-01 00:00:00")

# definitions for the plot layout with multiple panels
_cmin, _cmax, _cinc = -5., 25., 2.0
auto_clevels = False

left, width = 0.1, 0.5
bottom, height = 0.1, 0.5
bottom_h = left_h = left+width+0.03

rectC = [left, bottom, width, height]
rectX = [left, bottom_h, width, 0.2]
rectY = [left_h, bottom, 0.2, height]

mpl.rcParams['figure.figsize'] = (12,10)

# Create 15 min bins for a 9 hour period (9x4=36).  Each bin will average for analysis times
time_bins = [ (15*t,15*(t+3)) for t in range(36)]

# Create uneven height bins because of MRMS and other radar scans.
height_bins = [(0.0, 1000.), (1000., 2000.), (2000., 3000.), (3000., 4000.),
               (4000., 5000.), (5000., 6000.), (7000.,8000.), (8000.,9000.), (9000.,10000.)]

        
#-------------------------------------------------------------------------------
#
#-------------------------------------------------------------------------------
#
def obs_seq_read_netcdf(filename, retFileAttr = False):
    if retFileAttr == False:
        try:
            return xr.open_dataset(filename).to_dataframe()
        except IOError:
            print(" \n ----> netCDF obs_seq_final file not found! \n")
            sys.exit(-1)
    else:
        try:
            xa = xr.open_dataset(filename)
            return xa.to_dataframe(), xa.attrs
        except IOError:
            print(" \n ----> netCDF obs_seq_final file not found! \n")
            sys.exit(-1)

#-------------------------------------------------------------------------------
#
def obs_seq_get_obtype(df, kind=None, name=None):
    
    if kind:
        idx = df['kind'] == kind
        return df[idx]
    
    if name:
        idx = df['name'] == name
        return df[idx]

    print("\n OBS_SEQ_GET_OBTYPE:  no kind or name specified, exiting \n")
    sys.exit(-1)
    
#-------------------------------------------------------------------------------
#
def obs_seq_2D_bin(df, variable, time=None, height=None, threshold=None, dart_qc=True):
    
    # Create the data structures needed for bin information
    
    bins     = np.zeros((len(height),len(time)))
    spread   = np.zeros((len(height),len(time)))

    num_obs = np.zeros((len(height),len(time)))
    min      = []
    hgt      = []

    for n, t in enumerate(time):
        
        # Create coordinate list for time in minutes
        min.append(t[0])
        
        # This string is used to bin data in time
        time_string = '%d <= anal_min <= %d' % (t[0], t[1])

        # Pandas dataframe query:  This query string returns a new dataframe with only those
        # rows that match the string.
        cut0_df = df.query(time_string)

        for m, z in enumerate(height):
            
            # This string is used to bin data in height
            height_string = '%f < height <= %f' % (z[0], z[1])

            # Pandas dataframe query:  This query string returns a new dataframe with only those
            # rows that match the string.
            cut1_df = cut0_df.query(height_string)

            # Create coordinate list for heights
            if n == 0:
                hgt.append(0.5*(z[0]+z[1]))

            # Remove all DART_QC indices != 0.0 because those are the only ones assimilated...
            if dart_qc:
                cut2_df = cut1_df.query("dart_qc < 0.1")
            else:
                cut2_df = cut1_df
                
            if threshold != None:  # threshold is a string, like "heights > 2000." 
                cut3_df      = cut2_df.query(threshold)    
                bins[m,n]    = cut3_df[variable].mean()
                spread[m,n]  = cut3_df['sdHxf'].mean()
                num_obs[m,n] = np.sum(cut3_df[variable] != 0.0)
            else:
                bins[m,n]    = cut2_df[variable].mean()
                spread[m,n]  = cut2_df['sdHxf'].mean()
                num_obs[m,n] = np.sum(cut2_df[variable] != 0.0)


    if threshold != None:
        del cut0_df, cut1_df, cut2_df, cut3_df
    else:
        del cut0_df, cut1_df, cut2_df

        
    return {'spread': spread, 'bin2d': bins, 'num_obs': num_obs,  
            'mins': np.array(min), 'hgts': np.array(hgt)}

#-------------------------------------------------------------------------------
#

def obs_seq_TimeHeightInnov(data_dict, plotlabel=None, ptype = "Prior"):
    
    fig = plt.figure(figsize=(12,12))
    fig.text(0.68, 0.75, "\n\nInnovation Stats\nBlack Line = Innov\nBlue Line = %s Spread\nGreen = No. of Obs" % ptype, 
             size=16, va="baseline", ha="left", multialignment="left")
    
    if plotlabel != None:
        fig.text(0.68, 0.68, plotlabel, size=14, va="baseline", ha="left", multialignment="left")

    zmin = 0.0
    zmax = 10.
    
    # Decouple data_dict
    spread   = np.ma.masked_invalid(data_dict['spread'])
    anal_min = np.ma.masked_invalid(data_dict['mins'])
    z        = np.ma.masked_invalid(data_dict['hgts'])
    data     = np.ma.masked_invalid(data_dict['bin2d'])
    num_obs  = np.ma.masked_invalid(data_dict['num_obs'])
    
    datebins = []
    minutes_from = dtime.datetime.strptime("2017-05-16_18:00:00", time_format)
    for min in anal_min:
        datebins.append(minutes_from + dtime.timedelta(0,int(min)*60))
        
    # 2D plot
    
    axC = plt.axes(rectC)

    if auto_clevels:
        cmin, cmax, cint, clevels = nice_clevels(-30, 30, outside=False, cint = 5.0)
    else:
        clevels = np.arange(_cmin, _cmax+_cinc, _cinc)

    cs1=axC.contourf(datebins, z/1000., data, clevels, cmap=cm.get_cmap('YlOrRd'))
    cs2=axC.contour(datebins,  z/1000., data, cs1.levels, colors='k')
    start = datebins[0].strftime("%Y%m%d%H%M%S")
    end   = datebins[-1].strftime("%Y%m%d%H%M%S")
    s     = dtime.datetime.strptime(start, "%Y%m%d%H%M%S")
    e     = dtime.datetime.strptime(end, "%Y%m%d%H%M%S")

    axC.set_xlim(s, e)
    axC.set_ylim(zmin,zmax)

    maj_loc = mdates.MinuteLocator(interval=30)
    axC.xaxis.set_major_locator(maj_loc)
    dateFmt = mdates.DateFormatter('%H:%M')
    axC.xaxis.set_major_formatter(dateFmt)

    min_loc   = mdates.MinuteLocator(interval=15)
    axC.xaxis.set_minor_locator(min_loc)

    labels = axC.get_xticklabels()
    plt.setp(labels, rotation=40, fontsize=10)

    axC.clabel(cs2, inline=1, fontsize=10, fmt="%1.1f")
    axC.set_ylabel("Height (km)")
    axC.set_xlabel("Time")
    
    # 1D time series plot
    
    axX = plt.axes(rectX)
    time_data   = data.mean(axis=0)
    time_spread = spread.mean(axis=0)

    start = datebins[0].strftime("%Y%m%d%H%M%S")
    end   = datebins[-1].strftime("%Y%m%d%H%M%S")
    s     = dtime.datetime.strptime(start, "%Y%m%d%H%M%S")
    e     = dtime.datetime.strptime(end, "%Y%m%d%H%M%S")
    axX.plot(datebins, time_data, lw=2.0, color='k')
    axX.plot(datebins, time_spread, lw=1.0, color='b')

    # Twin the x-axis to create a double y axis for num_obs
    axX2 = axX.twinx()
    axX2.plot(datebins, num_obs.mean(axis=0), lw=1.0, color='g')
    axX2.set_ylabel('No. of Obs', color='g')
    axX2.tick_params('y', colors='g')

    axX.set_xlim(s, e)
    axX.set_ylim(_cmin, _cmax)
    axX.set_xticklabels([])
    axX.set_ylabel("Innovation/Spread")
    min_loc   = mdates.MinuteLocator(interval=15)
    axX.xaxis.set_minor_locator(min_loc)
    axX.grid(True)
     
    # 1D Height Plotting Plotting

    axY           = plt.axes(rectY)
    height_data   = data.mean(axis=1)
    height_spread = spread.mean(axis=1)
    
    axY.plot(height_data, z/1000., lw=2.0, color='k')
    axY.plot(height_spread, z/1000., lw=1.0, color='b')
    
    # Twin the y-axis to create a double x axis for num_obs
    axY2 = axY.twiny()
    axY2.plot(num_obs.mean(axis=1), z/1000., lw=1.0, color='g')
    axY2.set_xlabel('No. of Obs', color='g')
    axY2.tick_params('x', colors='g')

    axY.set_ylim(0.0,z.max()/1000.)
    axY.set_xlim(-5.,15)
    axY.set_yticklabels([])
    axY.set_xlabel("Innovation/Spread")
    
    # major ticks every 20, minor ticks every 5                                      
    major_ticks = np.arange(0,16,4)                                       
    minor_ticks = np.arange(0,16,2)                                         

    axY.set_xticks(major_ticks)                                                       
    axY.set_xticks(minor_ticks, minor=True)                                           

    axY.grid(True)

#=========================================================================================
# Plot the innovations from an obs_seq_file.nc file created by dart_cc.py
#-------------------------------------------------------------------------------
def main(argv=None):
    if argv is None:
           argv = sys.argv

# Command line interface for DART_cc
    
    parser = OptionParser()

    parser.add_option("-f", "--file",  dest="file",  default=None, type="string",
                       help = "netCDF4 obs_seq_final to process") 

    parser.add_option("-v", "--variable",  dest="var",  default="REF", type="string",
                       help = "radar variable to process [REF, VR], default is REF") 

    parser.add_option("-p", "--plotfile",  dest="plotfilename",  default=None, type="string",
                       help = "name of output pdf file") 
                                              
    parser.add_option(       "--show",  dest="show", default=False, action="store_true", help="Turn off screen plotting")
                                         
    parser.add_option(       "--thres", dest="thres", default=None, help="use this to threshold calculations using an obs floor")
    parser.add_option("--dir",  dest="dir",  default="./", type="string", help = "full pathname where to put image")
                                         
    (options, args) = parser.parse_args()
    
    if options.file == None:
        print "\n                NO FILE IS SUPPLIED, EXITING.... \n "
        parser.print_help()
        print
        sys.exit(1)

    # Read in the data
    dataset, fileAttrs = obs_seq_read_netcdf(options.file, retFileAttr = True)
    
    # Get the radar variable out of file  fileAttrs has a dictionary for the DART ob type kinds
    
    if options.var == "VR":
        kind = fileAttrs['DOPPLER_RADIAL_VELOCITY']
        _cmin, _cmax, _cinc = -15., 15., 1.0
    else:
        kind = fileAttrs['RADAR_REFLECTIVITY']
   
    field = obs_seq_get_obtype(dataset, kind=kind)

    # Construct a output pdf filename
   
    if options.plotfilename == None:
        file = os.path.split(options.file)[-1]
        file_time = dtime.datetime.strptime(file[-11:-3], "%Y%m%d")
        if file.find("obs") > 0:
            plotfilename = "%s/%s_%sINNOV_%s" % (options.dir, options.var, file[0:file.find("obs")], file[-11:-3])
        else:
            plotfilename = "%s/%s_INNOV_%s" % (options.dir, options.var, file[-11:-3])
        
        plotlabel = "REALTIME: %s\nOBTYPE: %s" % (file[0:file.find("obs")], options.var)

    else:
        plotfilename = options.plotfilename
        plotlabel    = "%s\nDART QC ON" % (options.var)
        
    if options.thres != None:
        plotlabel = "%s\nDART QC ON\n%s" % (plotlabel, options.thres)
        
#   Bin data
    data_dict = obs_seq_2D_bin(field, 'innov', time=time_bins, height=height_bins, threshold=options.thres)
    
#   Plot data
    if options.file.find("final") != 0: 
        obs_seq_TimeHeightInnov(data_dict, plotlabel=plotlabel, ptype="Prior")
    else:
        obs_seq_TimeHeightInnov(data_dict, plotlabel=plotlabel)
    
#   Saving and plotting
    plt.savefig(plotfilename+".png")
    
    if options.show:
        plt.show()

#-------------------------------------------------------------------------------
# Main program for testing...
#
if __name__ == "__main__":
    sys.exit(main())

# End of file


