#! /usr/bin/env python3

#----------------------------------------------------------------------------
# Name:     bam.py
# Purpose:  Florida Bay Assessment Model
# Author:   J Park
#----------------------------------------------------------------------------

# Python distribution modules
import sys
from   argparse import ArgumentParser
from   os       import getenv, getcwd
import tkinter as Tk

# Community modules
from numpy import linspace

# Local modules
import model as bam_model
import gui
from init import InitTimeBasins

#----------------------------------------------------------------------------
# Main module
#----------------------------------------------------------------------------
def main():
    '''See Notes.py and model.py
 
    To do:
      -------------------------------------------------------------
      Groundwater : include as Runoff?
      -------------------------------------------------------------
      Flush output files
      Add a non-gui option
      Change plot time units from model timestep (dt) to s, min, hr, day
      Plot archived data with run id
      Add iteration count to output
      Replace shoal hydro dictionaries with explicitly indexed numpy arrays?
      Replace numeric lists with pre-allocated numpy arrays?
      Break the Run() out into a multiprocess with queue or pipe comms : Pause
      Redo shapefile/init files to include new boundary basins
      Remove phantom shoals that don't connect basins
      Hardcoded boundary basins : read from config file
      Add Help (Notes.py __doc__ etc...)
    '''

    args = ParseCmdLine()

    # Initialize the root Tk object
    root = Tk.Tk()
    root.title( 'Bay Assessment Model' )

    # Instantiate and initialize the main Model class and its
    # Basins and Shoals maps
    model = bam_model.Model( root, args )
    
    # Create GUI
    model.gui = gui.GUI( root, model )
    model.gui.FloridaBayModel_Tk()

    InitTimeBasins( model )
    model.gui.InitPlotVars() # Set default outputs

    # Enter the Tk mainloop
    model.gui.Tk_root.mainloop()

#--------------------------------------------------------------
# 
#--------------------------------------------------------------
def ParseCmdLine():

    home_dir = getenv( 'HOME', default = getcwd() )

    parser = ArgumentParser( description = 'Bay Assessment Model' )

    parser.add_argument('-p', '--path',
                        dest    = 'path', type = str, 
                        action  = 'store', 
                        default = '/opt/hydro/models/PyBAM/',
                        help    = 'Top level path of BAM: -p ' +\
                                  '/opt/hydro/models/PyBAM/' )

    parser.add_argument('-t', '--timestep',
                        dest    = 'timestep', type = int, 
                        action  = 'store', 
                        default = 360,
                        help    = 'timestep (s): -t 360')

    parser.add_argument('-S', '--start',
                        dest    = 'start', type = str, 
                        action  = 'store', 
                        default = '2010-01-01 00:00',
                        help    = 'start date time: -S "2010-01-01 00:00"')

    parser.add_argument('-E', '--end',
                        dest    = 'end', type = str, 
                        action  = 'store', 
                        default = '2010-01-01 08:00',
                        help    = 'End date time: -E "2010-01-01 08:00"')

    parser.add_argument('-vt', '--velocity_tolerarance',
                        dest    = 'velocity_tol', type = float, 
                        action  = 'store', 
                        default = 0.0001,
                        help    = 'velocity iteration tolerance (m/s):' +\
                                  ' -vt 0.0001' )

    parser.add_argument('-it', '--max_iteration',
                        dest    = 'max_iteration', type = int, 
                        action  = 'store', 
                        default = 3000,
                        help    = 'velocity iteration limit: -it 3000')

    parser.add_argument('-b', '--basins',
                        dest    = 'basinShapeFile', type = str, 
                        action  = 'store', 
                        default = 'data/GIS/FLBayBasins',
                        help    = 'Basins shape file: -d data/GIS/FLBayBasins')

    parser.add_argument('-bd', '--basinDepth',
                        dest    = 'basinDepth', type = str, 
                        action  = 'store', 
                        default = 'data/init/Basin_Area_Depth.csv',
                        help    = 'Basin area depth input file: -bd ' +\
                                  'data/init/Basin_Area_Depth.csv' )

    parser.add_argument('-bp', '--basinParameter',
                        dest    = 'basinParameters', type = str, 
                        action  = 'store', 
                        default = 'data/init/Basin_Parameters.csv',
                        help    = 'Basin parameters input file: -bp ' +\
                                  'data/init/Basin_Parameters.csv' )

    parser.add_argument('-bi', '--basinInit',
                        dest    = 'basinInit', type = str, 
                        action  = 'store', 
                        default = 'data/init/Basin_Initial_Values.csv',
                        help    = 'Basin initial state variable input file:' +\
                                  '-bi data/init/Basin_Initial_Values.csv' )

    parser.add_argument('-bt', '--basinTide',
                        dest    = 'basinTide', type = str, 
                        action  = 'store', 
                        default = 'data/init/Basin_Tide_Boundary_2010_2015.csv',
                        help    = 'Basin tide boundary data files: -bt ' +\
                                  'data/init/Basin_Tide_Boundary_1995_2002.csv')

    parser.add_argument('-br', '--basinRain',
                        dest    = 'basinRain', type = str, 
                        action  = 'store', 
                        default = 'data/Rain/' +\
                                  'DailyRainFilled_cm_1999-9-1_2015-12-8.csv',
                        help    = 'Daily rain data file: -br data/Rain/' +\
                                  'DailyRainFilled_cm_1999-9-1_2015-12-8.csv' )

    parser.add_argument('-bf', '--basinBCFile',
                        dest    = 'basinBCFile', type = str, 
                        action  = 'store', 
                        default = 'data/init/Basin_Boundary_Condition.csv',
                        help    = 'Basin boundary condition data files: -bb ' +\
                                  'data/init/Basin_Boundary_Condition.csv')

    parser.add_argument('-bo', '--basinOutput',
                        dest    = 'basinOutputDir', type = str, 
                        action  = 'store', 
                        default = home_dir + '/BAM.out',
                        help    = 'Directory to write basin outputs: -bo ' +\
                                  home_dir + '/BAM.out' )

    parser.add_argument('-bF', '--basinFlowRunoff',
                        dest    = 'basinFlowRunoff', type = str, 
                        action  = 'store', 
                        default = 'data/Runoff/DailyRunoffVolume.csv',
                        help    = 'Daily runoff flow volume data file: ' +\
                                  '-bF data/Runoff/DailyRunoffVolume.csv' )

    parser.add_argument('-bR', '--basinStageRunoff',
                        dest    = 'basinStageRunoff', type = str, 
                        action  = 'store', 
                        default = 'data/Runoff/EDEN_Stage_OffsetMSL.csv',
                        help    = 'Daily runoff EDEN stage data file: ' +\
                                  '-bF data/Runoff/' +\
                                  'EDEN_Stage_OffsetMSL.csv' )

    parser.add_argument('-bS', '--basinStageRunoffMap',
                        dest    = 'basinStageRunoffMap', type = str, 
                        action  = 'store', 
                        default = 'data/init/Basin_Runoff_Boundary.csv',
                        help    = 'Mapping of EDEN stage to basin: ' +\
                                  '-bS data/init/Basin_Runoff_Boundary.csv' )

    parser.add_argument('-bs', '--basinStage',
                        dest    = 'basinStage', type = str, 
                        action  = 'store', 
                        default = 'data/Stage/' +\
                                  'DailyStage_1999-9-1_2016-3-1.csv',
                        help  = 'Daily stage data file: -sf data/Stage/'+\
                                'DailyStage_1999-9-1_2016-3-1.csv' )

    parser.add_argument('-et', '--ET',
                        dest    = 'ET', type = str, 
                        action  = 'store', 
                        default = 'data/ET/' +\
                                  'PET_1999-9-1_2015-12-8.csv',
                        help    = 'PET data file: -et ' +\
                                  'data/ET/PET_1999-9-1_2015-12-8.csv' )

    parser.add_argument('-es', '--ET scale',
                        dest    = 'ET_scale', type = float, 
                        action  = 'store', 
                        default = 2,
                        help    = 'Scale factor on global ET: -es 2' )

    parser.add_argument('-s', '--shoals',
                        dest    = 'shoalShapeFile', type = str, 
                        action  = 'store', 
                        default = 'data/GIS/FathomLines',
                        help    = 'Shoals shape file: -s data/GIS/FathomLines')

    parser.add_argument('-sp', '--shoalParameters',
                        dest    = 'shoalParameters', type = str, 
                        action  = 'store', 
                        default = 'data/init/Shoal_Parameters.csv',
                        help    = 'Shoal to basin mapping file:'+\
                                  '-sp data/init/Shoal_Parameters.csv' )

    parser.add_argument('-sl', '--shoalLength',
                        dest    = 'shoalLength', type = str, 
                        action  = 'store', 
                        default = 'data/init/Shoal_Length_Depth.csv',
                        help    = 'Shoal width and length depth input file:' +\
                                  '-sl data/init/Shoal_Length_Depth.csv' )

    parser.add_argument('-sm', '--shoalManning',
                        dest    = 'shoalManning', type = float, 
                        action  = 'store', 
                        default = None,
                        help    = 'Manning friction for all shoals: -sf 0.1' )

    parser.add_argument('-sf', '--salinityFile',
                        dest    = 'salinityFile', type = str, 
                        action  = 'store', 
                        default = 'data/Salinity/' +\
                                  'DailySalinityFilled_1999-9-1_2015-12-8.csv',
                        help  = 'Daily salinity data file: -sf data/Salinity/'+\
                                'DailySalinityFilled_1999-9-1_2015-12-8.csv' )

    parser.add_argument('-msl', '--seasonalMSL',
                        dest    = 'seasonalMSL', type = str, 
                        action  = 'store', 
                        default = 'data/Tide/' +\
                                  'MSL_Anomaly.csv',
                        help    = 'Seasonal MSL: -sm data/Tide/' +\
                                  'MSL_Anomaly.csv')

    parser.add_argument('-e', '--editor',
                        dest    = 'editor', type = str, 
                        action  = 'store', 
                        default = 'gedit',
                        help    = 'Editor: -e gedit' )

    parser.add_argument('-r', '--runID',
                        dest    = 'runID', type = str, 
                        action  = 'store', 
                        default = '',
                        help    = 'Run ID for output files.')

    parser.add_argument('-rf', '--runInfoFile',
                        dest    = 'runInfoFile', type = str, 
                        action  = 'store', 
                        default = 'RunInfo.txt',
                        help    = 'File for output run messages.')

    parser.add_argument('-oi', '--outputInterval',
                        dest    = 'outputInterval', type = int, 
                        action  = 'store', 
                        default = 1,
                        help    = 'Time interval (hr) of output data: ' +\
                                  '-oi 1' )

    parser.add_argument('-mi', '--mapInterval',
                        dest    = 'mapInterval', type = int, nargs = '*',
                        action  = 'store', 
                        default = ( 1, 0 ),
                        help    = 'Time interval of display refresh in ' +\
                                  '(days) and [(hr)]: -mi 1 [0]' )

    parser.add_argument('-L', '--stageLegend',
                        dest    = 'stageLegendBound', type = float, 
                        action  = 'store', 
                        default = 0.5,
                        help    = 'Stage legend bound on map: -L 0.5')

    parser.add_argument('-P', '--salinityLegend',
                        dest    = 'salinityLegendBound', type = float, 
                        action  = 'store', 
                        default = 50,
                        help    = 'Salinity legend bound on map: -P 50')

    parser.add_argument('-bc', '--boundaryConditions',
                        dest   = 'boundaryConditions', # type = bool, 
                        action = 'store_true', default = False,
                        help   = 'Enable fixed boundary conditions for basins.')

    parser.add_argument('-nr', '--noRain',
                        dest   = 'noRain', # type = bool, 
                        action = 'store_true', default = False,
                        help   = 'Disable rain inputs.')

    parser.add_argument('-ne', '--noET',
                        dest   = 'noET', # type = bool, 
                        action = 'store_true', default = False,
                        help   = 'Disable ET inputs.')

    parser.add_argument('-nR', '--noStageRunoff',
                        dest   = 'noStageRunoff', # type = bool, 
                        action = 'store_true', default = False,
                        help   = 'Disable EDEN stage runoff inputs.')

    parser.add_argument('-aF', '--addFlowRunoff',
                        dest   = 'addFlowRunoff', # type = bool, 
                        action = 'store_true', default = False,
                        help   = 'Activate Everglades flow runoff inputs.')

    parser.add_argument('-nt', '--noTide',
                        dest   = 'noTide', # type = bool, 
                        action = 'store_true', default = False,
                        help   = 'Disable tidal boundary inputs.')

    parser.add_argument('-nm', '--noMeanSeaLevel',
                        dest   = 'noMeanSeaLevel', # type = bool, 
                        action = 'store_true', default = False,
                        help   = 'Disable mean sea level inputs.')

    parser.add_argument('-gs', '--gaugeSalinity',
                        dest   = 'gaugeSalinity', # type = bool, 
                        action = 'store_true', default = False,
                        help   = 'Impose basin gauge salinity where available.')

    parser.add_argument('-si', '--salinityInit',
                        dest   = 'salinityInit', type = str, 
                        action = 'store', default = 'yes',
                        help   = 'Initialize basin salinity from gauge data.')

    parser.add_argument('-D', '--DEBUG',
                        dest   = 'DEBUG', # type = bool, 
                        action = 'store_true', default = False )

    parser.add_argument('-DA', '--DEBUG_ALL',
                        dest   = 'DEBUG_ALL', # type = bool, 
                        action = 'store_true', default = False )

    args = parser.parse_args()

    # Ensure path has terminator
    if not args.path.endswith( '/' ) :
        args.path = args.path + '/'

    # Add the home directory
    args.homeDir = home_dir

    # Add the original command line
    command_line = ''
    for c in sys.argv :
        command_line = command_line + c + ' '
    args.commandLine = command_line

    # Disqualify mutiple runoff BC's
    if ( not args.noStageRunoff ) and args.addFlowRunoff :
        errMsg = 'ParseCmdLine: Cannot specify runoff stage and flow ' +\
                 'together.  Either disable EDEN stage runoff (-nR) or ' +\
                 'do not specify Everglades flow runoff (-aF).'
        raise Exception( errMsg )

    # Tick marks for the legend : values corresponding to legend_color_map
    # Create stage_legend_bounds
    args.stage_legend_bounds = linspace( -args.stageLegendBound, 
                                          args.stageLegendBound, 11 )
    # Create salinity_legend_bounds
    args.salinity_legend_bounds = linspace( 0, args.salinityLegendBound, 11 )

    return args

#----------------------------------------------------------------------------
# Provide for cmd line invocation: not executed on import
if __name__ == "__main__":
    main()
