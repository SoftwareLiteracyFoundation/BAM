
# Python distribution modules
from os          import mkdir
from os.path     import exists as path_exists
from time        import time, asctime, localtime
from datetime    import timedelta, datetime
from collections import OrderedDict as odict
import tkinter as Tk

strptime = datetime.strptime

# Community modules
from scipy import interpolate

# Local modules 
import init
import basins
import shoals
import hydro
import gui
import constants

#---------------------------------------------------------------
# 
#---------------------------------------------------------------
class Model:
    '''The main model object. It contains a Basins dictionary of Basin
    objects, and a Shoals dictionary of Shoal objects. The Run() method
    executes a model simulation.'''

    def __init__( self, root, args ):

        self.Version = 'Bay Assessment Model\n' + constants.Version + '\n'
        self.args                = args
        self.status              = constants.Status()
        self.state               = None
        self.start_time          = None # -S
        self.end_time            = None # -E
        self.simulation_days     = None
        self.previous_start_time = None
        self.previous_end_time   = None
        self.current_time        = None
        self.unix_time           = None
        self.timestep            = args.timestep      # -t  (s)
        self.timestep_per_day    = 24 * 3600 / self.timestep 
        self.max_iteration       = args.max_iteration # -it 
        self.velocity_tol        = args.velocity_tol  # -vt (m/s)

        # Data containers and maps
        self.times               = []     # array of datetimes
        self.record_variables    = []     # variables to plot/record
        self.rain_data           = dict() # { (year,month,day) : {station:rain}}
        self.et_data             = dict() # { (year,month,day) : pet }
        self.runoff_stage_basins = dict() # { Basin : EDEN station } -bS
        self.runoff_stage_data   = dict() # {(year,month,day):{basin_num:stage}}
        self.runoff_stage_shoals = dict() # { Basin : [ Shoal ] }
        self.runoff_flow_basins  = []     # [ Basin ] -bF
        self.runoff_flow_data    = dict() # {(year,month,day):{basin_num:flow}}
        self.salinity_data       = odict()# { (year,month,day) : {station:ppt} }
        self.stage_data          = odict()# { (year,month,day) : {station:ppt} }
        self.fixed_boundary_cond = dict() # { basin_num : (type, value) }
        self.timeseries_boundary = dict() # { basin : ??? } Not implemented
        self.seasonal_MSL_splrep = None   # scipy spline representation 
        self.seasonal_MSL        = 0      # value at current time
        self.salinity_stations   = []     # [ gauge IDs ]
        self.stage_stations      = []     # [ gauge IDs ]

        # Convert -S -E args into start_time, end_time datetime objects
        self.GetStartStopTime()

        # Create dictionary of Basin objects from shapefile (-b)
        self.Basins = dict() # { basin_number : Basin }
        init.CreateBasinsFromShapefile( self ) # and add boundary basins
        init.GetBasinAreaDepths( self )  # -bd
        init.GetBasinParameters( self )  # -bp

        # Create dictionary of Shoal objects from shoalLength.csv file (-sl)
        self.Shoals = dict() # { shoal_number : Shoal }
        init.CreateShoals( self )
        init.GetShoalParameters( self ) # -sp

        # Simulation update intervals for gui and data output
        self.timeLabelUpdate = timedelta( days = 0, hours = 1, 
                                          minutes = 0, seconds = 0 )
        self.timeMapUpdate   = timedelta( days  = args.mapInterval[ 0 ], 
                                          hours = args.mapInterval[ 1 ], 
                                          minutes = 0, seconds = 0 )
        self.outputInterval  = timedelta( hours = args.outputInterval )

        # Text buffer to hold messages written to runInfo.txt
        self.run_info = []

        self.gui = None

    #-----------------------------------------------------------
    #
    #-----------------------------------------------------------
    def Run( self ):
        '''Execute a model simulation.
        Called from the runButton in gui.py'''

        if self.args.DEBUG_ALL :
            print( '-> Run' )

        # Prepare to write output
        # Probe the basinOutputDir and create if needed
        output_dir = self.args.basinOutputDir 
        if not path_exists( output_dir ) :
            msg = 'Run: ' + output_dir +\
                  ' is not accessible.  Creating directory.\n'
            self.gui.Message( msg )

            try :
                mkdir( output_dir )

            except FileNotFoundError :
                msg = 'Run: Invalid output path ' + output_dir +\
                      '  simulation aborted.\n'
                self.gui.Message( msg )
                return                

            if not path_exists( output_dir ) :
                msg = 'Run: Failed to mkdir ' + output_dir +\
                      '  simulation aborted.\n'
                self.gui.Message( msg )
                return

        #----------------------------------------------------------------
        # Set appropriate legend and data type for basin.SetBasinMapColor 
        # called for map plot updates below
        mapPlotVariable = self.gui.mapPlotVariable.get()

        legend_bounds = None

        if mapPlotVariable not in constants.BasinMapPlotVariable :
            msg = 'Run Error: Invalid map plot variable, using Stage.\n'
            self.gui.Message( msg )
            mapPlotVariable = 'Stage'
            legend_bounds   = self.args.stage_legend_bounds

        if mapPlotVariable == 'Salinity' :
            legend_bounds = self.args.salinity_legend_bounds

        elif mapPlotVariable == 'Stage' : 
            legend_bounds = self.args.stage_legend_bounds

        else :
            msg = 'Run Error: ', mapPlotVariable, \
                  'not yet supported for map, showing Stage.\n'
            self.gui.Message( msg )
            mapPlotVariable = 'Stage'
            legend_bounds   = self.args.stage_legend_bounds

        #-----------------------------------------------------
        # Setup start time and status
        if self.state == self.status.Init :
            self.current_time = self.start_time

        if self.current_time > self.end_time :
            msg = 'Run Error: start time is after end time.\n'
            self.gui.Message( msg )
            return

        run_start_time = time()
        msg = 'Start simulation from ' + str( self.start_time ) +\
              ' to ' + str( self.end_time ) + ' at ' +\
              asctime( ( localtime( run_start_time ) ) ) + '.\n'
        self.gui.Message( msg )

        # Copy initial values to the data logs
        self.times.append( self.current_time )
        for Basin in self.Basins.values() :
            Basin.CopyDataRecord()
 
        zero_timedelta = timedelta() # timedelta() = zero delta time
        self.state = self.status.Running

        #------------------------------------------------------------
        # Simulation loop
        #------------------------------------------------------------
        while self.state == self.status.Running :

            if self.args.DEBUG_ALL :
                print( self.current_time )

            # Advance time
            self.current_time = self.current_time + \
                                timedelta( seconds = self.timestep )

            self.unix_time += self.timestep

            # Update time on gui currentTimeLabel every self.timeLabelUpdate 
            timeDelta = ( self.current_time - self.start_time )
            quotient, remainder = divmod( timeDelta, self.timeLabelUpdate )
            if remainder == zero_timedelta :
                self.gui.current_time_label.set( str( self.current_time ) )
                self.gui.canvas.show()

            # Tuple used as lookup key for rain, ET, salinity, runoff
            key = ( self.current_time.year,
                    self.current_time.month,
                    self.current_time.day )

            self.BoundaryConditions()

            self.GetSalinity( key )

            self.GetTides()

            self.GetRain( key )

            self.GetET( key )

            self.GetRunoff( key )

            hydro.ShoalVelocities( self )

            hydro.MassTransport( self )

            hydro.Depths( self )


            # Display map update every timeMapUpdate interval or at sim end
            quotient, remainder = divmod( timeDelta, self.timeMapUpdate )
            if remainder == zero_timedelta or \
               self.current_time == self.end_time :

                for Basin in self.Basins.values() :
                    if not Basin.boundary_basin :
                        Basin.SetBasinMapColor( mapPlotVariable, legend_bounds )

                self.gui.current_time_label.set( str( self.current_time ) )
                self.gui.RenderBasins()
                self.gui.canvas.show()

            # Transfer data values to records for plots & file output
            quotient, remainder = divmod( timeDelta, self.outputInterval )
            if remainder == zero_timedelta or \
               self.current_time == self.end_time :
                # Store datetime reference
                self.times.append( self.current_time )

                for Basin in self.Basins.values() :
                    Basin.CopyDataRecord()

            if self.current_time >= self.end_time :
                self.state = self.status.Finished
        #------------------------------------------------------------
        # End Simulation loop
        #------------------------------------------------------------

        # Track simulation elapsed time
        self.state = self.status.Finished

        elapsed_time = time() - run_start_time
        if elapsed_time <= 60 :
            elapsed_time_str = str( round( elapsed_time ) ) + ' (s).'
        elif elapsed_time > 60 and elapsed_time <= 3600 :
            elapsed_time_str = str( round( elapsed_time / 60, 1 ) ) + ' (min).'
        else :
            elapsed_time_str = str( round( elapsed_time / 3600, 2 ) ) + ' (hr).'
            
        msg = 'Simulation complete. Elapsed time: ' + elapsed_time_str +\
              '\nWriting output to ' + self.args.basinOutputDir + '... '
        self.gui.Message( msg )

        # Write output
        for Basin in self.Basins.values() :
            Basin.WriteData()

        try :
            fd = open(self.args.basinOutputDir +'/'+ self.args.runInfoFile, 'w')
            for line in self.run_info :
                fd.write( line )
            fd.close()

        except OSError as err :
            msg = "\nRun: OS error: {0}\n".format( err )
            self.gui.Message( msg )
            print( msg )

        self.gui.Message( ' Finished.\n' )
        
    #----------------------------------------------------------------
    # 
    #----------------------------------------------------------------
    def GetRain( self, key ):
        '''Add rain volume to the basin'''

        if self.args.DEBUG_ALL :
            print( '\n-> GetRain', flush = True )

        if self.args.noRain :
            return

        station_rain_map = self.rain_data[ key ]

        for Basin in self.Basins.values() :
            if Basin.boundary_basin is True :
                continue

            rain_cm_day = 0

            # JP instead of aggregating here, do in init?
            # Accumulate scaled rain from stations
            for rain_station, scale in zip( Basin.rain_stations, 
                                            Basin.rain_scales ) :
                rain_cm_day += station_rain_map[ rain_station ] * scale

            rain_volume_day = ( rain_cm_day / 100 ) * Basin.area

            rain_volume_t   = rain_volume_day / self.timestep_per_day

            Basin.rainfall  = rain_volume_t

            Basin.water_volume += rain_volume_t

    #----------------------------------------------------------------
    # 
    #----------------------------------------------------------------
    def GetET( self, key ):
        '''Subtract ET volume from basin'''

        if self.args.DEBUG_ALL :
            print( '\n-> GetET', flush = True )

        if self.args.noET :
            return

        et_mm_day = self.et_data[ key ]

        for Basin in self.Basins.values() :
            if Basin.boundary_basin is True :
                continue

            et_volume_day = ( et_mm_day / 1000 ) * Basin.area * \
                            self.args.ET_scale

            et_volume_t   = et_volume_day / self.timestep_per_day

            Basin.evaporation = et_volume_t

            Basin.water_volume -= et_volume_t
            
    #----------------------------------------------------------------
    # 
    #----------------------------------------------------------------
    def GetRunoff( self, key ):
        '''Add runoff flow volume or set Everglades basin stage'''

        if self.args.DEBUG_ALL :
            print( '\n-> GetRunoff', flush = True )

        if not self.args.noStageRunoff :
            self.GetRunoffStage( key )

        elif self.args.addFlowRunoff :
            self.GetRunoffFlow( key )
 
    #----------------------------------------------------------------
    # 
    #----------------------------------------------------------------
    def GetRunoffStage( self, key ):
        '''Set stage in Everglades boundary basins'''

        if self.args.DEBUG_ALL :
            print( '\n-> GetRunoffStage', flush = True )

        basin_stage_map = self.runoff_stage_data[ key ]

        for Basin, EDEN_station in self.runoff_stage_basins.items() :

            Basin.water_level = basin_stage_map[ EDEN_station ]

    #----------------------------------------------------------------
    # 
    #----------------------------------------------------------------
    def GetRunoffFlow( self, key ):
        '''Add runoff flow volume to the basin'''

        if self.args.DEBUG_ALL :
            print( '\n-> GetRunoffFlow', flush = True )

        basin_flow_map = self.runoff_flow_data[ key ]

        for Basin in self.runoff_flow_basins :

            volume_day = basin_flow_map[ Basin.number ]

            volume_t = volume_day / self.timestep_per_day

            Basin.runoff_flow = volume_t

            Basin.water_volume += volume_t

    #-----------------------------------------------------------
    #
    #-----------------------------------------------------------
    def GetTides( self ):
        '''Set boundary basin water level to the tidal value with
        the seasonal mean sea level anomaly.'''

        if self.args.DEBUG_ALL :
            print( '-> GetTides' )

        # Get the seasonal mean sea level anomaly
        try :
            if self.args.noMeanSeaLevel :
                self.seasonal_MSL = 0
            else :
                self.seasonal_MSL = interpolate.splev( self.unix_time, 
                                                       self.seasonal_MSL_splrep,
                                                       der = 0 ).round( 3 )
        except ValueError as err :
            print( 'GetTides(): interpolate seasonal_MSL at ',
                   str( self.current_time ), '[', 
                   str( self.unix_time ), ']  ', err )
            self.seasonal_MSL = 0

        # Get the tidal value for each boundary basin
        for Basin in self.Basins.values() :
            if Basin.boundary_basin :
                try :
                    if self.args.noTide :
                        wl = 0
                    else :
                        # Note this returns a numpy array, but we have 
                        # appended floats to a list for other plot_variable
                        # data values, and use round() on those.
                        # JP might change all data to numpy arrays
                        if Basin.boundary_function :
                            wl = float(Basin.boundary_function(self.unix_time))

                except ValueError as err :
                    print( 'GetTides() boundary_function basin: ', Basin.name, 
                           ' at ',
                           str( self.current_time ), '[', 
                           str( self.unix_time ), ']  ', err )
                    wl = 0

                wl += self.seasonal_MSL
                
                Basin.water_level = wl

    #----------------------------------------------------------------
    # 
    #----------------------------------------------------------------
    def GetSalinity( self, key ):
        '''Set basin salinity from data'''

        if self.args.DEBUG_ALL :
            print( '\n-> GetSalinity', flush = True )

        station_salinity_map = self.salinity_data[ key ]

        for Basin in self.Basins.values() :
            if Basin.boundary_basin :
                if Basin.salinity_station :
                    Basin.salinity = \
                        station_salinity_map[ Basin.salinity_station ]

            elif Basin.salinity_from_data :
                Basin.salinity = station_salinity_map[ Basin.salinity_station ]

    #-----------------------------------------------------------
    #
    #-----------------------------------------------------------
    def BoundaryConditions( self ):
        '''Set additional basin flow, or stage value'''

        if self.args.DEBUG_ALL :
            print( '-> BoundaryConditions' )

        if not self.args.boundaryConditions :
            return

        # Fixed head or flow
        for basin_num, type_value_tuple in self.fixed_boundary_cond.items() :
            Basin = self.Basins[ basin_num ]

            if type_value_tuple[ 0 ] == 'flow' :
                bc_vol = float( type_value_tuple[ 1 ] ) * self.timestep
                Basin.water_volume += bc_vol

            elif type_value_tuple[ 0 ] == 'stage' :
                Basin.water_level = float( type_value_tuple[ 1 ] )

    #-----------------------------------------------------------
    #
    #-----------------------------------------------------------
    def GetStartStopTime( self ):
        ''' '''
        if self.args.DEBUG_ALL :
            print( '-> GetStartStopTime' )

        if ':' in self.args.start :
            format_string = '%Y-%m-%d %H:%M'
        else :
            format_string = '%Y-%m-%d'

        self.start_time = strptime( self.args.start, format_string ) # -S

        if ':' in self.args.end :
            format_string = '%Y-%m-%d %H:%M'
        else :
            format_string = '%Y-%m-%d'

        self.end_time = strptime( self.args.end, format_string ) # -E

    #-----------------------------------------------------------
    #
    #-----------------------------------------------------------
    # def Pause( self ):
    #     ''' '''
    #     if self.args.DEBUG:
    #         print( '-> Pause' )
    #
    #     self.state = self.status.Paused
