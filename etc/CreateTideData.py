#! /usr/bin/env python3

#----------------------------------------------------------------------------
# Name:     CreateTideData.py
# Purpose:  Wrapper for XTide to generate fbm boundary data
# Author:   J Park
#----------------------------------------------------------------------------
#

import os
import argparse

#----------------------------------------------------------------------------
# Main module
#----------------------------------------------------------------------------
def main():
    '''See XTide  http://www.flaterco.com/xtide/
    http://manpages.ubuntu.com/manpages/trusty/man1/xtide.1.html
    sudo apt-get install xtide

    From the command line: tide ...
       -l  harmonic constants name
       -b  begin: "1990-01-01 00:00"
       -e  end:   "1990-01-03 00:00" 
       -mm output times as: 2002-02-06  4:56 PM EST
       -mr output time in Unix seconds instead of AM/PM.
       -fc .cvs output
       -um units meters
       -s  output interval for -mm or -mr modes as HH:MM
       -o  output filename (append mode)
    '''
    args = ParseCmdLine()

    for station in args.stationNames :
    #if True:
    #    station = args.stationNames
        outFile = args.outputDirectory +\
                  station[ : station.find( ',' ) ].replace( ' ', '_' ) +\
                  '_' + args.begin[ : args.begin.find( ' ' ) ] +\
                  '_' + args.end  [ : args.end.find  ( ' ' ) ] + '.csv'

        if args.DEBUG_ALL :
            print( outFile )

        command_line = 'tide -l "' + station + '" -b "' + args.begin +\
                       '" -e "' + args.end + '" -mm -fc -um -s ' +\
                       args.interval + ' -o ' + outFile.replace( '.csv', '.tmp' )

        if args.DEBUG :
            print( command_line )

        # subprocess.call can't take a string command... wtf?
        os.system( command_line )

        # Remove the first column and round the water levels
        fd = open( outFile.replace( '.csv', '.tmp' ), 'r' )
        lines = fd.readlines()
        fd.close()

        # Delete the temporary file
        os.system( 'rm ' +  outFile.replace( '.csv', '.tmp' ) )

        # Find the mean
        mean = 0
        if args.removeMean :
            for line in lines :
                words  = line.split( ',' )
                mean  += float( words[3] )
            mean = mean / len( lines )

            print( 'Mean: ', mean )

        buff = []
        for line in lines :
            words    = line.split( ',' )
            DateTime = words[1] + ' ' + words[2]
            data     = str( round( float( words[3] ) - mean, 3 ) )
            buff.append( DateTime + ', ' + data + '\n' )

        fd = open( outFile, 'w' )
        if args.removeMean :
            fd.write( 'Time, WL.(m).demeaned\n' )
        else :
            fd.write( 'Time, WL.(m)\n' )
        for line in buff:
            fd.write( line )
        fd.close()

#--------------------------------------------------------------
# 
#--------------------------------------------------------------
def ParseCmdLine():

    StationNames = [
        #'Flamingo, Florida Bay, Florida',
        'Cape Sable, East Cape, Florida',
        'Long Key, western end, Florida',
        'Lignumvitae Key, NE side, Florida Bay, Florida',
        'Snake Creek, Hwy. 1 bridge, Windley Key, Florida',
        'Tavernier Creek, Hwy. 1 bridge, Hawk Channel, Florida',
        #'Point Charles, Key Largo, Florida',
        'Garden Cove, Key Largo, Florida',
        'Little Card Sound bridge, Florida' ] #,
        #'Main Key, Barnes Sound, Florida',
        #'Manatee Creek, Manatee Bay, Barnes Sound, Florida',
        #'Shell Key, northwest side, Lignumvitae Basin, Florida',
        #'Yacht Harbor, Cowpens Anchorage, Plantation Key, Florida',
        #'East Key, southern end, Florida Bay, Florida',
        #'Crane Keys, north side, Florida Bay, Florida' ]

    parser = argparse.ArgumentParser( description = 'CreateTideData' )
    
    parser.add_argument('-b', '--begin',
                        dest    = 'begin', type = str, 
                        action  = 'store', 
                        default = '1990-01-01 00:00',
                        help    = 'start date time')

    parser.add_argument('-e', '--end',
                        dest    = 'end', type = str, 
                        action  = 'store', 
                        default = '2021-01-02 00:00',
                        help    = 'End date time')

    parser.add_argument('-i', '--interval',
                        dest    = 'interval', type = str, 
                        action  = 'store', 
                        default = '01:00',
                        help    = 'Projection interval HH:MM')

    parser.add_argument('-od', '--outputDirectory',
                        dest    = 'outputDirectory', type = str, 
                        action  = 'store', 
                        default = './',
                        help = 'Directory to write outputs.')

    parser.add_argument('-s', '--stationNames',
                        dest    = 'stationNames', type = str,
                        action  = 'store', 
                        default = StationNames,
                        help = 'List of Xtide station names.')

    parser.add_argument('-rm', '--removeMean',
                        dest   = 'removeMean', # type = bool, 
                        action = 'store_true', default = True )

    parser.add_argument('-D', '--DEBUG',
                        dest   = 'DEBUG', # type = bool, 
                        action = 'store_true', default = True )

    parser.add_argument('-DA', '--DEBUG_ALL',
                        dest   = 'DEBUG_ALL', # type = bool, 
                        action = 'store_true', default = False )

    args = parser.parse_args()

    if args.outputDirectory[ -1 ] != '/' :
        args.outputDirectory = outputDirectory + '/'

    if not os.path.exists( args.outputDirectory ) :
        raise Exception( 'Output directory not accessible: ', 
                         args.outputDirectory )

    return args

#----------------------------------------------------------------------------
# Provide for cmd line invocation: not executed on import
if __name__ == "__main__":
    main()
