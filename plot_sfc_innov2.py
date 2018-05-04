
# coding: utf-8

from optparse import OptionParser


import pandas as pd
import numpy as np
from netcdftime import utime
import matplotlib.pyplot as plt
import sys, os, glob
import datetime as dtime
import xarray as xr
import matplotlib as mpl
import matplotlib.cm as cm
mpl.rcParams['figure.figsize'] = (12,10)
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
from pltbook import nice_mxmnintvl, nice_clevels

time_format = "%Y-%m-%d_%H:%M:%S"
day_utime   = utime("days since 1601-01-01 00:00:00")
sec_utime   = utime("seconds since 1970-01-01 00:00:00")

# definitions for the plot layout with multiple panels

plot_params = {0:['LAND_SFC_TEMPERATURE',     'METAR_TEMPERATURE_2_METER',-3,3],
               1:['LAND_SFC_DEWPOINT',        'METAR_DEWPOINT_2_METER',   -3,3], 
               2:['LAND_SFC_ALTIMETER',       'METAR_ALTIMETER',          -1,1],
               3:['LAND_SFC_U_WIND_COMPONENT','METAR_U_10_METER_WIND',  -5,5], 
               4:['LAND_SFC_V_WIND_COMPONENT','METAR_V_10_METER_WIND',  -5,5]}

# Create 30 min bins for a 9 hour period (9x4=36)
time_bins = [ (15*t,15*(t+3)) for t in range(36)]

#-------------------------------------------------------------------------------
#
def obs_seq_read_netcdf(filename, retFileAttr = False):
    if retFileAttr == False:
        return xr.open_dataset(filename).to_dataframe()
    else:
        xa = xr.open_dataset(filename)
        return xa.to_dataframe(), xa.attrs

#-------------------------------------------------------------------------------
#
def obs_seq_get_obtype(df, kind=None, name=None):
    
    if kind:
        if len(kind) > 1:
            idx1 = df['kind'] == kind[0]
            idx2 = df['kind'] == kind[1]
            return pd.concat([df[idx1], df[idx2]])
        else:
            idx = df['kind'] == kind
            return df[idx]
    
    if name:
        idx = df['name'] == name
        return df[idx]

    print("\n OBS_SEQ_GET_OBTYPE:  no kind or name specified, exiting \n")
    sys.exit(-1)
    
#-------------------------------------------------------------------------------
#
def obs_seq_1D_bin(df, variable, time=None, threshold=None, dart_qc=True):
    
    # Create the data structures needed for bin information
    
    bins     = np.zeros(len(time))
    rms      = np.zeros(len(time))
    spread   = np.zeros(len(time))
    num_obs  = np.zeros(len(time))
    min      = []

    for n, t in enumerate(time):
        
        # Create coordinate list for time in minutes
        min.append(t[0])
        
        # This string is used to bin data in time
        time_string = '%d <= anal_min <= %d' % (t[0], t[1])

        # Pandas dataframe query:  This query string returns a new dataframe with only those
        # rows that match the string.
        cut0_df = df.query(time_string)

        # Remove all DART_QC indices != 0.0 because those are the only ones assimilated...
        if dart_qc:
            cut1_df = cut0_df.query("dart_qc < 0.1")
        else:
            cut1_df = cut0_df

        if threshold != None:  # threshold is a string, like "heights > 2000." 
            num_obs[n] = np.sum(cut2_df[variable] != 0.0)
            cut2_df    = cut1_df.query(threshold)    
            bins[n]    = cut2_df[variable].mean()
            rms[n]     = np.sqrt((cut2_df[variable]**2).mean())
            spread[n]  = cut2_df['sdHxa'].mean()
        else:
            num_obs[n] = np.sum(cut1_df[variable] != 0.0)
            bins[n]    = cut1_df[variable].mean()
            rms[n]     = np.sqrt((cut2_df[variable]**2).mean())
            spread[n]  = cut1_df['sdHxa'].mean()

    print num_obs

    if threshold != None:
        del cut0_df, cut1_df, cut2_df
    else:
        del cut0_df, cut1_df

        
    return {'spread': np.ma.masked_invalid(spread), 
            'bin1d': np.ma.masked_invalid(bins), 
            'rms1d': np.ma.masked_invalid(rms), 
            'num_obs': num_obs,  
            'mins': np.array(min)}

#-------------------------------------------------------------------------------
#

def obs_seq_SfcInnov(data_dict, axX=None, cint=None, title=None):
        
    # Decouple data_dict
    spread   = data_dict['spread']
    anal_min = data_dict['mins']
    data     = data_dict['bin1d']
    data_rms = data_dict['rms1d']
    num_obs  = data_dict['num_obs']
    
    datebins = []
    minutes_from = dtime.datetime.strptime("2017-05-16_18:00:00", time_format)
    for min in anal_min:
        datebins.append(minutes_from + dtime.timedelta(0,int(min)*60))
    
    # 1D time series plot
    
    start = datebins[0].strftime("%Y%m%d%H%M%S")
    end   = datebins[-1].strftime("%Y%m%d%H%M%S")
    s     = dtime.datetime.strptime(start, "%Y%m%d%H%M%S")
    e     = dtime.datetime.strptime(end, "%Y%m%d%H%M%S")
    axX.plot(datebins, data,   lw=2.0, color='k', label="Prior Innov [y - Hx]")
    axX.plot(datebins, spread, lw=1.0, color='b', label="Prior Spread")
    axX.plot(datebins, data_rms, lw=1.0, color='r', label="RMSI")

    axX.set_xlim(s, e)

    maj_loc = mdates.MinuteLocator(interval=30)
    axX.xaxis.set_major_locator(maj_loc)
    dateFmt = mdates.DateFormatter('%H:%M')
    axX.xaxis.set_major_formatter(dateFmt)

    min_loc   = mdates.MinuteLocator(interval=15)
    axX.xaxis.set_minor_locator(min_loc)

    labels = axX.get_xticklabels()
    plt.setp(labels, rotation=40, fontsize=10)

    # Twin the x-axis to create a double y axis for num_obs
    axX2 = axX.twinx()
    axX2.plot(datebins, num_obs, lw=1.0, color='g')
    axX2.set_ylabel('No. of Obs', color='g')
    axX2.tick_params('y', colors='g')

    axX.set_xlim(s, e)
    axX.set_ylim(cint[0], cint[1])
    axX.set_ylabel("Innovation and Spread")
#    axX.set_xlabel("Time")
    min_loc   = mdates.MinuteLocator(interval=15)
    axX.xaxis.set_minor_locator(min_loc)
    
    axX.grid(True)
    axX.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3, ncol=2, mode="expand", borderaxespad=0.)
    if title != None:
        axX.set_title(title, zorder=10)
                

def main(file, image_dir):

    plotlabel = "SFC %s" % file[-11:-3]
    dataset, fileAttrs = obs_seq_read_netcdf(file, retFileAttr = True)

    fig, ax = plt.subplots(5, figsize=(12,12))

    test     = obs_seq_get_obtype(dataset, kind=[fileAttrs[plot_params[0][0]],fileAttrs[plot_params[0][1]]])

    for key in np.arange(5):
    
        field1 = pd.DataFrame({'A' : []})
        field2 = pd.DataFrame({'A' : []})
    
        try:
            print plot_params[key][0]
            field1     = obs_seq_get_obtype(dataset, kind=fileAttrs[plot_params[key][0]])
            data_dict1 = obs_seq_1D_bin(field1, 'innov', time=time_bins)
        except:
            pass
    
        try:
            field2     = obs_seq_get_obtype(dataset, kind=fileAttrs[plot_params[key][1]])
            data_dict2 = obs_seq_1D_bin(field2, 'innov', time=time_bins)
        except:
            pass
    
        if field1.empty == False and field2.empty == True:
            ptitle = "%s" % (plot_params[key][2])
            print(" Plotting:  %s" % ptitle)
            obs_seq_SfcInnov(data_dict1, axX = ax[key], cint=plot_params[key][2:], title=ptitle)


        if field2.empty == False and field1.empty == True:
            ptitle = "%s" % (plot_params[key][1])
            print(" Plotting:  %s" % ptitle)
            obs_seq_SfcInnov(data_dict2, axX = ax[key], cint=plot_params[key][2:], title=ptitle)

        if field1.empty == False and field2.empty == False:
            num_obs1 = data_dict1['num_obs']
            num_obs2 = data_dict2['num_obs']
            w0       = num_obs1 / (num_obs1 + num_obs2)
            w1       = 1.0 - w0
                                        
            data_dict = {'spread':  w0*data_dict1['spread'] + w1*data_dict2['spread'],
                         'bin1d' :  w0*data_dict1['bin1d']  + w1*data_dict2['bin1d'],
                         'num_obs': num_obs1 + num_obs2,
                         'mins':    data_dict1['mins']}
                                        
            ptitle = "%s + %s" % (plot_params[key][0], plot_params[key][1])
            print(" Plotting:  %s" % ptitle)

            obs_seq_SfcInnov(data_dict, axX = ax[key], cint=plot_params[key][2:], title=ptitle)

        del field1, field2
    
    fig.subplots_adjust(hspace=0.3)
    plt.setp([a.get_xticklabels() for a in ax[:-1]], visible=False)
    ax[-1].set_xlabel("Time")
    fig.suptitle(("\n\nDiagnostics for %s\nBlack Line = Innov  Blue Line = Prior Spread  Green = No. of Obs" % plotlabel), 
             size=12, va="baseline", ha="center", multialignment="center", y= 0.96)
    fig.tight_layout(rect=[0.05, 0.05, 0.95, 0.95])
    
    plt.savefig("%s/SFC_ObsDiag_%s.png" % (image_dir, file[-11:-3]))
    plt.show()
    
#-------------------------------------------------------------------------------
# Main program for testing...
#
if __name__ == "__main__":

#-------------------------------------------------------------------------------
# Main function defined to return correct sys.exit() calls

# Command line interface for DART_cc

    parser = OptionParser()

    parser.add_option("-f", "--file",  dest="file",  default=None, type="string", help = "obs_seq.final.nc file to process")
    parser.add_option("--dir",  dest="dir",  default="./", type="string", help = "full pathname where to put image")

    (options, args) = parser.parse_args()

    if options.file == None:
        print "\n                NO INPUT obs_seq_final.nc IS SUPPLIED, EXITING.... \n "
        parser.print_help()
        print
        sys.exit(1)
    else:
        main(options.file, options.dir)
