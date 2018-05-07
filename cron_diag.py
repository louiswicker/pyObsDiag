#!/usr/bin/env python

import time
import os
import sys
import datetime
from optparse import OptionParser

_www_dir = "/www/www.nssl.noaa.gov/projects/wof/news-e/diagnostics"

_obs_exe = "/work/wicker/REALTIME/pyObsDiag/obs_seq_collate.py"
_sfc_exe = "/work/wicker/REALTIME/pyObsDiag/plot_sfc_innov.py"
_rad_inn = "/work/wicker/REALTIME/pyObsDiag/plot_radar_innov.py"
_rad_rms = "/work/wicker/REALTIME/pyObsDiag/plot_radar_rms.py"

def run_diag(year, month, day, run_collate=True):

    today = "%4.4d%2.2d%2.2d" % (year, month, day)
    print(" Today is:  %s" % today)

    image_dir = "%s/." % (_www_dir)

    if run_collate:
        cmd = 'python %s -d "/scratch/wof/realtime/%s/%s*" -f "obs_seq.final*" -p obs_seq.final' % (_obs_exe, today, year)

        print(" Cmd: %s" % (cmd))
        ret = os.system("%s" % cmd)
        if ret != 0:
            print("\n ============================================================================")
            print("\n RUN_DIAG:  obs_seq_collate failed....\n")
            print("\n ============================================================================")
            sys.exit(-1)

# Surface diagnostics
    cmd = 'python %s -f obs_seq.final.%s.nc --dir %s' % (_sfc_exe, today, image_dir)
    print(" Cmd: %s" % (cmd))
    ret = os.system("%s" % cmd)

# DBZ diagnostics
    cmd = 'python %s -f obs_seq.final.%s.nc --dir %s' % (_rad_inn, today, image_dir)
    print(" Cmd: %s" % (cmd))
    ret = os.system("%s" % cmd)
    cmd = 'python %s -f obs_seq.final.%s.nc --dir %s' % (_rad_rms, today, image_dir)
    print(" Cmd: %s" % (cmd))
    ret = os.system("%s" % cmd)

# VR diagnostics
    cmd = 'python %s -f obs_seq.final.%s.nc -v VR --dir %s' % (_rad_inn, today, image_dir)
    print(" Cmd: %s" % (cmd))
    ret = os.system("%s" % cmd)
    cmd = 'python %s -f obs_seq.final.%s.nc -v VR --dir %s' % (_rad_rms, today, image_dir)
    print(" Cmd: %s" % (cmd))
    ret = os.system("%s" % cmd)

#-------------------------------------------------------------------------------
# Main function defined to return correct sys.exit() calls

def main(argv=None):
   if argv is None:
       argv = sys.argv
#
# Command line interface
#
   parser = OptionParser()
   parser.add_option("-d", "--date",   dest="date",    default=None,  type="string", \
                    help = "YYYYMMDD to process if --realtime flag is not True")

   parser.add_option(      "--realtime",  dest="realtime",    default=False, action="store_true", \
               help = "Boolean flag to process this day")

   parser.add_option(      "--nofile",  dest="nofile",    default=True, action="store_false", \
               help = "Boolean flag to not create file, just plots")

   (options, args) = parser.parse_args()

   if options.realtime:
       local_today = time.localtime()
       run_diag(local_today.tm_year, local_today.tm_mon, local_today.tm_mday)
       sys.exit(0)

   if options.date != None:
       year, month, day = options.date[0:4], options.date[4:6], options.date[6:8]
       run_diag(int(year), int(month), int(day), run_collate=options.nofile)
       sys.exit(0)

   print(" \n Error, incorrect input arguments...exiting\n")
   parser.print_help()
   print
   sys.exit(-1)


#-------------------------------------------------------------------------------
# Main program for testing...
#
if __name__ == "__main__":
    sys.exit(main())
