
# Python distribution modules
from collections import OrderedDict as odict

# Local modules
import constants

#---------------------------------------------------------------
# 
#---------------------------------------------------------------
class Basin:
    """Variables for each of the 54 basins in Florida Bay. Water level and
    solute concentrations in each basin are calculated from the volumes 
    and fluxes. Note that Bay basins are numbered 5 - 58. Basins 1 - 4
    do not exist.  Basins 59 - 68 are tidal boundary basins, 69 - 82 are
    Everglades runoff boundary basins."""

    def __init__( self, model, name, number, total_area, perimeter, xy, 
                  boundary = False ):

        self.model = model

        # Figure Canvas variables
        self.basin_xy   = xy    # Read from shapefile
        self.Axes_fill  = None  # Created by matplotlib fill() :
                                # a matplotlib.lines.Line2D class
        self.color      = ( 1, 1, 1 )

        # Basin variables
        self.name            = name
        self.number          = number
        self.total_area      = total_area # (m^2)
        self.perimeter       = perimeter  # (m)
        self.wet_area        = dict()     # (m^2) { depth(ft) : Area(m^2) }
        self.land_area       = None       # (m^2)
        self.area            = 0          # (m^2) 
        self.water_level     = None       # (m)
        self.water_volume    = 0          # (m^3)
        self.previous_volume = 0          # (m^3)
        self.salt_mass       = None       # (kg)
        self.salinity        = None       # (g/kg)
        self.temperature     = None       # (C)

        # Volume transports
        self.shoal_transport = None   # (m^3/time)  Sum : Shoal Q_total
        self.rainfall        = None   # (m^3/time)
        self.runoff_flow     = None   # (m^3/time) imposed flow
        self.runoff_EVER     = None   # (m^3/time) from EDEN stage over shoals
        self.groundwater     = None   # (m^3/time)
        self.evaporation     = None   # (m^3/time)

        self.shoal_nums = set() # Shoal numbers : keys in Shoals map, for gui
        self.Shoals     = []    # Shoals

        # Boundary conditions
        self.boundary_basin      = boundary # True / False
        self.boundary_type       = None     # flow or stage
        self.boundary_function   = None     # scipy interpolate function

        # Rainfall station
        self.rain_station = None

        # Salinity station and salinity set from data flag
        self.salinity_station   = None
        self.salinity_from_data = False

        # Map of data accumulated over the simulation
        self.plot_variables = odict() # { variable : [ values ] }

        # Solute
        # self.dissolved_oxygen         = None
        # self.total_organic_carbon     = None
        # self.total_organic_phosphorus = None
        # self.total_organic_nitrogen   = None
        # self.phosphate                = None
        # self.nitrate                  = None
        # self.ammonium                 = None

        # Solute concentration transports
        # self.solute_shoal_transport = None  # (mol/time)
        # self.solute_rainfall        = None  # (mol/time)
        # self.solute_runoff          = None  # (mol/time)
        # self.solute_groundwater     = None  # (mol/time)

    #-----------------------------------------------------------
    # 
    #-----------------------------------------------------------
    def InitVolume( self ) :
        '''Compute initial basin volume, surface area and salt_mass'''

        self.Area()

        for depth_ft, wet_area in self.wet_area.items() :

            h = self.water_level + depth_ft * 0.3048

            self.water_volume += wet_area * h

        if not self.water_volume :
            self.water_volume = 1 # prevent division by 0 for salinity
            # why not just check for basin_boundary?

        # Set initial previous_volume to initial volume
        self.previous_volume = self.water_volume

        # salt_mass (g) = salinity (g/kg) * Vol (m^3) * rho (kg/m^3)
        self.salt_mass = self.salinity * self.water_volume * 997

    #-----------------------------------------------------------
    # 
    #-----------------------------------------------------------
    def Area( self ) :
        '''Compute surface area at current water_level'''

        self.area = 0

        for depth_ft, wet_area in self.wet_area.items() :

            h = self.water_level + depth_ft * 0.3048

            if h >= 0 :
                self.area += wet_area

    #-----------------------------------------------------------
    # 
    #-----------------------------------------------------------
    def CopyDataRecord( self ) :
        '''Transfer data values from a basin object to the 
        basin.plot_variables dictionary. Values are selected from 
        the GetRecordVariables() pop-up checkboxes. '''

        if self.model.args.DEBUG_ALL :
            print( '->CopyDataRecord : ', self.name )

        for plotVariable, intVar in self.model.gui.plotVar_IntVars.items() :

            if intVar.get() :
                if plotVariable not in self.plot_variables.keys() :
                    self.plot_variables[ plotVariable ] = []

                if plotVariable == 'Stage' :
                    data_value = self.water_level
                elif plotVariable == 'Salinity' :
                    data_value = self.salinity
                elif plotVariable == 'Volume' :
                    data_value = self.water_volume
                elif plotVariable == 'Flow' :
                    data_value = self.shoal_transport
                elif plotVariable == 'Rain' :
                    data_value = self.rainfall
                elif plotVariable == 'Evaporation' :
                    data_value = self.evaporation
                elif plotVariable == 'Runoff' :
                    data_value = self.runoff_EVER
                elif plotVariable == 'Groundwater' :
                    data_value = self.groundwater
                else :
                    msg = 'CopyDataRecord: ' + self.name + ' ' + plotVariable +\
                        ' is not supported for plotting.\n'
                    self.model.gui.Message( msg )
                    if plotVariable in self.plot_variables.keys() :
                        del self.plot_variables[ plotVariable ]
                    return

                # JP Change to preallocated numpy array?
                self.plot_variables[ plotVariable ].append( data_value )

    #-----------------------------------------------------------
    # 
    #-----------------------------------------------------------
    def WriteData( self ) :
        '''Write data values from the basin.plot_variables dictionary
        to a file. Values are selected from the GetRecordVariables()
        pop-up checkboxes. '''

        if self.model.args.DEBUG_ALL :
            print( '-> WriteData : ', self.name )

        # Open a file for this basin
        file_name = self.name + self.model.args.runID + '.csv'

        try :
            fd = open( self.model.args.basinOutputDir + '/' + file_name, 'w' )
        except OSError :
            msg = 'WriteData: failed to open file ' + file_name + ' in ' +\
                  self.model.args.basinOutputDir + '\n'
            self.model.gui.Message( msg )
            return

        # Write the header
        header = 'Time,\t\t\t'
        for plotVariable in self.plot_variables.keys() :
            header = header + plotVariable + ',\t'
        header = header.rstrip( ',\t' )
        fd.write( header + '\n' )

        # Write the data
        dataList = []
        for data in self.plot_variables.values() :
            dataList.append( data )

        for i in range( len( self.model.times ) ) :
            dataStr = str( self.model.times[ i ] ) + ',\t'

            for j in range( len( dataList ) ) :
                value = dataList[ j ][ i ]

                if value is None :
                    dataStr = dataStr + 'NA,\t'
                    continue

                try :
                    value = round( value, 3 )
                except TypeError as err :
                    if self.args.DEBUG : 
                        print( 'Basin ', self.name, ' WriteData(): ', err )

                    # This only happens if the basin is a tidal boundary and
                    # the data has been returned in a numpy array and not cast
                    # to a python float, since round() doesn't work on numpy
                    # arrays in the try: above, but there is np.round() 
                    # Here we cast it to a float:
                    value = round( float( value ), 3 )

                dataStr = dataStr + str( value ) +',\t'
                    
            dataStr = dataStr.rstrip( ',\t' )
            fd.write( dataStr + '\n' )

        # Close file
        fd.close()


    #-----------------------------------------------------------
    # 
    #-----------------------------------------------------------
    def SetBasinMapColor( self, plotVariable, legend_bounds ) :
        '''Set the basin color value according to the stage/salinity'''

        if self.model.args.DEBUG_ALL :
            print( '-> SetBasinMapColor : ', self.name )

        data_value = None

        if plotVariable not in constants.BasinMapPlotVariable :
            msg = 'SetBasinMapColor: Invalid map plot variable, using Stage'
            self.model.gui.Message( msg )
            plotVariable = 'Stage'
            data_value   = self.water_level
        
        # Select the appropriate data value
        if plotVariable == 'Salinity' :
            legend_bounds = self.model.args.salinity_legend_bounds
            data_value    = self.salinity

        elif plotVariable == 'Stage' : 
            legend_bounds = self.model.args.stage_legend_bounds
            data_value    = self.water_level

        else :
            msg = '\nSetBasinMapColor: ', plotVariable, \
                  'not yet supported for map, showing Stage.\n'
            self.model.gui.Message( msg )
            plotVariable = 'Stage'
            data_value   = self.water_level

        index = 0
        # Find the index into legend_bounds that is closest to the data
        for i, legend_value in enumerate( legend_bounds ):
            index = i
            if round( legend_value, 2 ) >= round( data_value, 3 ):
                break

        if index >= len( self.model.gui.colors ) :
            index = len( self.model.gui.colors ) - 1

        # Assign the current color
        self.color = self.model.gui.colors[ index ]

        if self.model.args.DEBUG_ALL :
            print( legend_bounds )
            print( self.name, ' plotVariable: ', plotVariable, ' ', index, 
                   ' ', data_value, ' ', legend_value, ' ', self.color )

    #-----------------------------------------------------------
    # 
    #-----------------------------------------------------------
    def Print( self, print_all = False ) :
        '''Display basin info on the gui msgText box.'''

        if self.model.args.DEBUG_ALL :
            print( '-> Print basin:' )

        basinInfo = '\n' + self.name + '\n'

        if print_all and self.total_area != None :
            basinInfo = basinInfo + ' Area: ' +\
                        str( round( self.total_area/1E6, 3 )) + ' (km^2) '

        if print_all and self.land_area != None :
            basinInfo = basinInfo + ' Land Area: ' +\
                        str( round( self.land_area/1E6, 3 ) ) + ' (km^2)\n'

        if print_all :
            basinInfo = basinInfo + ' Wet Area: '
            for depth, area in self.wet_area.items() :
                basinInfo = basinInfo +\
                    str( int( depth ) ) + 'ft: ' +\
                    str( round( area/1E6, 2 ) ) + ' '
                basinInfo = basinInfo + ' (km^2)\n'

        if self.water_level != None :
            basinInfo = basinInfo +\
                ' Stage: ' + str( round( self.water_level, 2 ) ) + ' (m)\n'

        if self.salinity != None :
            basinInfo = basinInfo +\
                ' Salinity: ' + str( round( self.salinity, 2 ) ) + ' (g/kg)\n'

        if self.water_volume != None :
            basinInfo = basinInfo +\
                ' Volume: ' + str( round( self.water_volume/1E9, 4 ) ) +\
                ' (km^3)\n'

        if self.shoal_transport != None :
            basinInfo = basinInfo +\
                ' Shoal Flux: ' + str( round( self.shoal_transport, 2 ) ) +\
                ' (m^3/t)\n'
        
        if self.rainfall != None :
            basinInfo = basinInfo +\
                ' Rain: ' + str( round( self.rainfall, 2 ) ) + ' (m^3/t)\n'
        
        if self.groundwater != None :
            basinInfo = basinInfo +\
                ' Groundwater: ' + str( round( self.groundwater, 2 ) ) +\
                ' (m^3/t)\n'
        
        if self.evaporation != None :
            basinInfo = basinInfo +\
                ' Evaporation: ' + str( round( self.evaporation, 2 ) ) +\
                ' (m^3/t)\n'

        self.model.gui.Message( basinInfo )
