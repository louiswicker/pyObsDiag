
# coding: utf-8

import pandas as pd
import numpy as np
from netcdftime import utime
import matplotlib.pyplot as plt
import sys, os, glob
import time
import datetime as dtime
from optparse import OptionParser
import xarray as xr
import netCDF4 as ncdf

time_format = "%Y-%m-%d_%H:%M:%S"
day_utime   = utime("days since 1601-01-01 00:00:00")
sec_utime   = utime("seconds since 1970-01-01 00:00:00")

#-------------------------------------------------------------------------------
# We have a double precision scientific string which I can only read this way
#
def read_double_precision_string(the_string):  

    if the_string.count("D") > 0:
        number     = the_string.replace('D','e')
    else:
        number     = the_string

    return np.double(number)

#=========================================================================================
# A generic class variable used to create containers
#

class myobject(object):

  def __init__(self, name, data=None, **kwargs):
    self.name = name
    self.data = data

    if kwargs != None:
      for key in kwargs:  setattr(self, key, kwargs[key])

  def keys(self):
    return self.__dict__

#=========================================================================================
# Parse and return a datetime object from obs_seq filename (notice, no seconds in filename)
#
def obs_seq_file_dtime(filename):
    try:
        return dtime.datetime.strptime(os.path.split(filename)[1][14:26], "%Y%m%d%H%M")
    except:
        print("\n Cannot parse filename:  %s, exiting program \n" % os.path.split(filename)[1])
        sys.exit(0)

# =========================================================================================
# Defines the data frame for each observation type
# 
# def obs_seq_dict_recarray(len, num_copies, num_qc):
#         
#     return np.recarray(len, 
#                     dtype = [('name',                'S128'),
#                              ('kind',                'i4'),
#                              ('number',              'i8'),
#                              ('values',              ("(%d,)" % num_copies)+'f8'),
#                              ('qc_values',           ("(%d,)" % num_qc)+'f8'),
#                              ('lat',                 'f8'),
#                              ('lon',                 'f8'),
#                              ('height',              'f8'),
#                              ('vert_coord',          'i4'),
#                              ('error_variance',      'f4'),
#                              ('days',                'i8'),
#                              ('seconds',             'i8'),
#                              ('utime',               'f8'),          
#                              ('date',                'S128'),  
#                              ('yb',                  'f8'),
#                              ('platform_lat',        'f8'), 
#                              ('platform_lon',        'f8'), 
#                              ('platform_height',     'f8'),
#                              ('platform_vert_coord', 'i4'),
#                              ('platform_dir1',       'f8'), 
#                              ('platform_dir2',       'f8'), 
#                              ('platform_dir3',       'f8'), 
#                              ('elevation',           'f8'),
#                              ('azimuth',             'f8'),
#                              ('satellite',           '(3,)f8')] )

#=========================================================================================
# Defines the data frame for each observation type
#
def obs_seq_dict_default(len, num_copies, num_qc):
        
    return np.recarray(len, 
                    dtype = [('name',                'S128'),
                             ('kind',                'i4'),
                             ('number',              'i8'),
                             ('value',               'f8'),
                             ('meanHxf',             'f8'),
                             ('meanHxa',             'f8'),
                             ('sdHxf',               'f8'),
                             ('sdHxa',               'f8'),
                             ('ncep_qc',             'f8'),
                             ('dart_qc',             'f8'),
                             ('lat',                 'f8'),
                             ('lon',                 'f8'),
                             ('height',              'f8'),
                             ('vert_coord',          'i4'),
                             ('error_variance',      'f4'),
                             ('days',                'i8'),
                             ('seconds',             'i8'),
                             ('utime',               'f8'),          
                             ('date',                'S128'),
                             ('anal_time',           'S128'),
                             ('anal_min',            'f8'),
                             ('rmsi',                'f8'),
                             ('innov',               'f8') ] )

#=========================================================================================
# Reads the obs_seq file header and sets up the needed information.  Returns a simple object
#

def obs_seq_header(file, debug_header=False):
    fi = open(file, 'r')
    fi.readline()                       # Read(str) "obs_sequence"
    fi.readline()                       # Read(str) "obs_kind_definitions"
    num_ob_kinds = long(fi.readline())  # Read(int) "number of observation types" 
        
    if debug_header:  print 'Number of observation types:  ', num_ob_kinds
        
    n = 0
        
    obtype_dict = {}

    begin_time = time.time()
    while n < num_ob_kinds:
        stuff = fi.readline()
        stuff = stuff.split()
        if debug_header:  print 'Observation kind definitions:  ', stuff[0], stuff[1]
        obtype_dict[int(stuff[0])] = stuff[1]
        n += 1
    
    end_time = time.time()
#    print("\n Search for obs took {0} seconds ".format(end_time - begin_time))

    stuff      = fi.readline()          # Read(str) "num_copies" line
    stuff      = stuff.split()
        
    num_copies = long(stuff[1])         # Important, if you have a truth file, you need to know this number (either 1 or 2)
    num_qc     = long(stuff[3])         
        
    stuff       = fi.readline()         # Read(str) "num_obs" line
    stuff       = stuff.split()
    num_obs     = long(stuff[1])
    max_num_obs = long(stuff[3])

    copy_names = []
    qc_names   = []

    for numcp in np.arange(num_copies):
        copy_names.append(fi.readline())  # Read(str) how the data is written....e.g., "observations" or "truth"

    for numqc in np.arange(num_qc):         # If the num_qc flag is > 0, read the description of the qc flags
        qc_names.append(fi.readline())

    stuff       = fi.readline()             # Read(str) "first   1   last   No of obs" line
    stuff       = stuff.split()
    first       = long(stuff[1])
    last        = long(stuff[3])

    if debug_header:
        print "Number of observation copies:  ", num_copies
        print "Number of QC'd observations:   ", num_qc
        print "Number of observations:        ", num_obs
        print "Max number of observations:    ", max_num_obs
    
    fi.close()
    
    return myobject("obs_head", filename      = file, 
                                num_obs_kinds = num_ob_kinds, 
                                obs_type      = obtype_dict,
                                copy_names    = copy_names,
                                qc_names      = qc_names,
                                num_copies    = num_copies,
                                num_qc        = num_qc,
                                num_obs       = num_obs,
                                max_num_obs   = max_num_obs,
                                first         = first,
                                last          = last,
                                ob_offset     = num_ob_kinds + num_qc + num_copies + 6)

#=========================================================================================
# Reads the obs_seq file and returns a Pandas dataframe
#
def read_obs_seq(fhead, return_DF = False, return_XR = False, time_from_1800=None):
 
    begin_time = time.time()
    
    print(" \n Reading in obs_sequence file:  %s" % fhead.filename)
    
    f = open(fhead.filename)
    fi = f.readlines()
    f.close()
    
    idx_obs = []
    for n, line in enumerate(fi):
        s = line.split()
        if s[0] == "OBS":
            idx_obs.append(n)

    # Create rec_array to store data in
    
    obs_seq = obs_seq_dict_default(fhead.num_obs, fhead.num_copies, fhead.num_qc)

    # If time_after_1800 is a datetime object, compute some useful time measures after 18Z
    if time_from_1800:
        anal_dtime           = obs_seq_file_dtime(fhead.filename)
        diff                 = anal_dtime - time_from_1800
        obs_seq.anal_time[:] = anal_dtime.strftime(time_format)
        obs_seq.anal_min[:]  = diff.seconds / 60.
      
    i = 0
    
    for m, n in enumerate(idx_obs):

        j = n
        
        stuff             = fi[j]        # Read(str) "OBS...." line
        stuff             = stuff.split()
        obs_seq.number[i] = long(stuff[1]) - 1
        
        j +=1 

        # crude but this works....

        for numcp in np.arange(fhead.num_copies):      
            if fhead.copy_names[numcp].find('obser') != -1:
                obs_seq.value[i] = read_double_precision_string(fi[j+numcp])
                continue 
                
            if fhead.copy_names[numcp].find('prior ensemble mean') != -1:
                obs_seq.meanHxf[i] = read_double_precision_string(fi[j+numcp])
                continue
                
            if fhead.copy_names[numcp].find('posterior ensemble mean') != -1:
                obs_seq.meanHxa[i] = read_double_precision_string(fi[j+numcp])
                continue 
                
            if fhead.copy_names[numcp].find('prior ensemble spread') != -1:
                obs_seq.sdHxf[i] = read_double_precision_string(fi[j+numcp]) 
                continue
                
            if fhead.copy_names[numcp].find('posterior ensemble spread') != -1:
                obs_seq.sdHxa[i] = read_double_precision_string(fi[j+numcp])    
                continue
                
        j += fhead.num_copies

        for numqc in np.arange(fhead.num_qc):      # Now read the observation, and if provided, the truth value
            if fhead.qc_names[numqc].find('NCEP') != -1:
                obs_seq.ncep_qc[i] = read_double_precision_string(fi[j+numqc])
                continue
            
            if fhead.qc_names[numqc].find('DART') != -1:
                obs_seq.dart_qc[i] = read_double_precision_string(fi[j+numqc]) 
                continue
                
        j += fhead.num_qc
        
        stuff            = fi[j]
        stuff            = stuff.replace(","," ").split()
        previous         = long(stuff[0])
        next             = long(stuff[1])
        cov_group        = long(stuff[2])
        
        j += 3

        stuff             = fi[j]
        stuff             = stuff.split()
        obs_seq.lon[i]    = np.rad2deg(read_double_precision_string(stuff[0]))
        obs_seq.lat[i]    = np.rad2deg(read_double_precision_string(stuff[1]))
        obs_seq.height[i] = read_double_precision_string(stuff[2])

        if obs_seq.lon[i] > 180.0: obs_seq.lon[i] = obs_seq.lon[i] - 360.

        if len(stuff) == 4:
            obs_seq.vert_coord[i] = long(stuff[3])
            j += 2
        else:
            obs_seq.vert_coord[i] = long(fi[j+1])
            j += 3

        obs_seq.kind[i] = int(fi[j])
        
        obs_seq.name[i] = fhead.obs_type[obs_seq.kind[i]]
        
        if m < len(idx_obs)-1:                      # read the day and time by knowing where next OB starts
            stuff              = fi[idx_obs[m+1]-2]
            stuff              = stuff.split()
            obs_seq.seconds[i] = int(stuff[0])
            obs_seq.days[i]    = int(stuff[1])
            obs_seq.error_variance[i] = read_double_precision_string(fi[idx_obs[m+1]-1])
        else:  # end of file issue
            stuff              = fi[idx_obs[-1]-2]
            stuff              = stuff.split()
            obs_seq.seconds[i] = int(stuff[0])
            obs_seq.days[i]    = int(stuff[1])
            obs_seq.error_variance[i] = read_double_precision_string(fi[idx_obs[-1]-1])
            
        day              = (float(obs_seq.days[i]) + float(obs_seq.seconds[i])/86400.)
        date             = day_utime.num2date(day)
        obs_seq.date[i]  = date.strftime(time_format)
        obs_seq.utime[i] = round(sec_utime.date2num(date))
        
        i += 1

    print(" %d observations are now read in from:  %s" % (fhead.num_obs,fhead.filename))

    end_time = time.time()
    print("\n Reading took {0} seconds since the loop started \n".format(end_time - begin_time))


# Calculate some handy stuff - like mean innovation (Yb)
    obs_seq.innov = obs_seq.value - obs_seq.meanHxf
    
    if return_DF == True:
        return pd.DataFrame.from_records(obs_seq)
    
    if return_XR == True:
        tmp = pd.DataFrame.from_records(obs_seq)
        return xr.Dataset(tmp, coords = {'index':tmp.number})

    else:
        return obs_seq

#=========================================================================================
# Write out obs_seq files to netCDF for faster inspection
#-------------------------------------------------------------------------------
# Main function defined to return correct sys.exit() calls

def main(argv=None):
    if argv is None:
           argv = sys.argv

# Command line interface for DART_cc
    
    parser = OptionParser()

    parser.add_option("-d", "--dir",  dest="dir",  default=None, type="string",
                       help = "Directory of files to process ")

    parser.add_option("-f", "--file",  dest="file",  default=None, type="string",
                       help = "wildcard of files to process ")

    parser.add_option("-p", "--prefix", dest="fprefix",  default=None, type="string",
                       help = "Preappend this string to the netcdf object filename")

                       
    (options, args) = parser.parse_args()
    
    if options.dir == None:

        print "\n                NO INPUT DIRECTORY IS SUPPLIED, EXITING.... \n "
        parser.print_help()
        print
        sys.exit(1)

    else:

        suffix = options.file
        print "%s/%s" % (os.path.abspath(options.dir), suffix)
        rawlist = glob.glob("%s/%s" % (os.path.abspath(options.dir), suffix))
        print rawlist
        
        files = sorted( rawlist, key = lambda file: os.path.getmtime(file))
        
        print("\n Obs_seq.final files sorted by modification time\n")
        for file in files:
            print(" {} - {}".format(file, time.ctime(os.path.getmtime(file))) )
        
        # Fix in case we picked up some none obs_seq files
        for n, file in enumerate(files):
             if file.find(".nc") != -1:  
                 print("\n Removing file:  %s from list" % file)
                 del files[n]
    
        print("\n Dart_cc:  Processing %d files in the directory:  %s" % (len(files), options.dir))
        print(" Dart_cc:  First file is %s" % (files[0]))
        print(" Dart_cc:  Last  file is %s" % (files[-1]))
        
        netcdf_file = files[0][:-4]+".nc"
        if options.fprefix == None:
            netcdf_file = os.path.split(files[0])[1][:-4]+".nc"
        else:
            netcdf_file = ("%s.%s" % (options.fprefix, os.path.split(files[0])[1][-12:-4]+".nc"))

        print("\n Dart_cc:  netCDF4 file to be written is %s\n" % (netcdf_file))
                
    dataset = []

    begin_time = time.time()
    
    time_stamp = obs_seq_file_dtime(files[0])
    
    num_obs_kinds = -1
    
    for file in files:
        file_header = obs_seq_header(file)
        dataset.append(read_obs_seq(file_header, return_DF=True, time_from_1800=time_stamp))
        if file_header.num_obs_kinds > num_obs_kinds:
            num_obs_kinds = file_header.num_obs_kinds
            file_header0 = file_header
            
    print("\n Found %d kinds of observations" % num_obs_kinds)
            
    end_time = time.time()
    
    print("\n Reading took {0} seconds since the loop started \n".format(end_time - begin_time))

    # Concat the obs_seq files together
    
    a = pd.concat(dataset, ignore_index=True)
    
    # Create an xarray dataset for file I/O
    xa = xr.Dataset(a)
    
    # reset index to be a master index across all obs
    xa.rename({'dim_0': 'index'}, inplace=True)
    
    # Write the xarray file out (this is all there is, very nice guys!)
    xa.to_netcdf(netcdf_file, mode='w')
    xa.close()
    
#   Add attributes to the files
    
    fnc = ncdf.Dataset(netcdf_file, mode = 'a')
    fnc.history = "Created " + dtime.datetime.today().strftime(time_format)
    
    for key in file_header0.obs_type.keys():
        print(" Writing attribute %s with key %d" % (file_header0.obs_type[key], key))
        fnc.setncattr(file_header0.obs_type[key],int(key))  
        
    fnc.sync()  
    fnc.close()
    
    

#-------------------------------------------------------------------------------
# Main program for testing...
#
if __name__ == "__main__":
    sys.exit(main())

# End of file
