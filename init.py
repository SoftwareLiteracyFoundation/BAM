'''Initialization functions for the Bay Assessment Model (BAM)'''

# Python distribution modules
from os          import cpu_count
from datetime    import timedelta, datetime
from collections import OrderedDict as odict
strptime = datetime.strptime

# Community modules
from scipy import interpolate
from numpy import array as nparray
from numpy import zeros as npzeros

# Worker pool to parallelize generation of tide interpolators
from multiprocessing import Pool

# Library for reading ArcGIS shapefile see:
# https://github.com/GeospatialPython/pyshp
import shapefile

# Local modules 
import basins
import shoals

# Kludge since multiprocessing can't handle embedded Tk
import pool_functions

#-----------------------------------------------------------
#
#-----------------------------------------------------------
def InitTimeBasins( model ):
    '''Reset time variables, read in Basin parameters from the
    basinInit file, initialize basin volumes based on the 
    initial water levels, and call any required initializations
    for Rain, ET, Salinity, BCs.'''

    if model.args.DEBUG_ALL :
        print( '-> InitTimeBasins' )

    if model.start_time > model.end_time :
        msg = 'Init Error: start time is after end time.\n'
        model.gui.Message( msg )
        return

    model.simulation_days = (model.end_time - model.start_time).days

    model.state = model.status.Init
    model.times.clear()
    model.current_time = model.start_time

    if not model.args.noGUI :
        model.gui.current_time_label.set( str( model.current_time ) )

    model.unix_time = ( model.current_time - 
                        datetime(1970,1,1) ).total_seconds()

    if not InitialBasinValues( model ) : # -bi basinInit file
        msg = '\nBasin initialization failed.\n'
        model.gui.Message( msg )
        return

    # Initialize basin volume, area, salt_mass based on intial water levels
    for Basin in model.Basins.values() :
        Basin.InitVolume()
        Basin.plot_variables.clear()

    # Call additional initialization methods if required
    time_changed = ( model.previous_start_time != model.start_time or \
                     model.previous_end_time   != model.end_time  )

    if not model.args.noTide and time_changed : # -nt
        if not GetBasinTidalData( model ) :     # -bt
            errMsg = '\nGetBasinTidalData failed. See the console.\n'
            raise Exception( errMsg )
                
    if not model.args.noMeanSeaLevel and time_changed : # -nm
        GetSeasonalMSL( model )                         # -sm

    if not model.args.noRain and time_changed : # -nr
        GetBasinRainData( model )               # -br

    if not model.args.noET and time_changed :   # -ne
        GetETData( model )                      # -et

    if not model.args.noStageRunoff and time_changed : # -nR
        GetBasinRunoffStageData( model )               # -bR

    if time_changed :
        GetBasinStageData( model ) # -bs

    if not model.args.noDynamicBoundaryConditions and time_changed : # -db
        GetBasinDynamicBCData( model )                              # -bc

    if model.args.fixedBoundaryConditions :     # -fb
        GetBasinFixedBoundaryCondition( model ) # -bf

    if model.args.gaugeSalinity and time_changed : # -gs
        GetBasinSalinityData( model )              # -sf

    # If salinityInit is 'yes' (-si), then override salinity from the
    # basinInit file (-bi) with the closest gauge data as mapped in the 
    # basinParameter (-bp) file. 
    if model.args.salinityInit.lower() == 'yes' :
        GetBasinSalinityData   ( model ) 
        SetInitialBasinSalinity( model )

    # Report simulation parameters 
    output_hours = model.outputInterval.days * 24 +\
                   model.outputInterval.seconds//3600 

    msg = str( model.start_time ) + ' to ' +\
          str( model.end_time )            +\
          '  Δt ' + str( model.args.timestep ) + ' (s)' +\
          '  Output '+ str( output_hours ) +' (hr)' +\
          '  V\u209C\u2092\u2097 ' +\
          str( round( model.args.velocity_tol, 4 )) + ' (m/s)\n'
    model.gui.Message( msg )

    if not model.args.noGUI :
        model.gui.RenderBasins( init = True )
        model.gui.PlotLegend()
        model.gui.canvas.show()

#----------------------------------------------------------------
#
#----------------------------------------------------------------
def CreateBasinsFromShapefile( model ):
    '''Instantiate Basin objects into the Basins dictionary. 

     A record in a shapefile contains the attributes for each shape
     in the collection of geometry. Records are stored in the dbf file. 
     The link between geometry and attributes is the foundation of GIS. 
     This critical link is implied by the order of shapes and corresponding 
     records in the shp geometry file and the dbf attribute file.'''

    if model.args.DEBUG_ALL :
        print( '\n-> GetBasinShapefileParams', flush = True )

    # A temporary map to check for duplicate basin names
    basinNameNumMap = {}

    # Read the shapefile (-x)
    # shapes() method returns a list of the shapefile's geometry
    # iterRecords() returns an iterator to the shapefile records
    # Each shape record contains the following attributes:
    #    bbox  parts  points  shapeType
    # points are vectors of xy

    sf_basins = shapefile.Reader( model.args.basinShapeFile )

    # A record from sf_basins.iterRecords() is a list of 4 strings:
    #       Area                    Perimeter      Number      Name
    # ['8.310187961009e+007', '3.934640784246e+004', '5', 'Barnes Sound']
    # 
    # Dual iteration over the records and shapes
    for record, shape in zip( sf_basins.iterRecords(), sf_basins.shapes() ):
 
        basin_xy = nparray( shape.points )

        if len( record ) != 4 :
            errMsg = 'Shapefile record has a length of ' + \
                     + str( record.len() ) + '. It must be of length 4.' + \
                     ' Record is: \n' + record
            raise Exception( errMsg )
            
        total_area = float( record[ 0 ] )
        perimeter  = float( record[ 1 ] )
        number     = int  ( record[ 2 ] )
        name       =        record[ 3 ]

        # check for duplicate record
        if number in model.Basins.keys() :
            errMsg = 'Duplicate basin number [' + number + \
                     '] found in shapefile records.'
            raise Exception( errMsg )

        if name in basinNameNumMap.keys() :
            errMsg = 'Duplicate basin name: ', name, ' [' + str(number) + \
                     '] found in shapefile records.'
            raise Exception( errMsg )
                
        # Instantiate and save the Basin object
        model.Basins[ number ] = basins.Basin( model, name, number, 
                                               total_area, 
                                               perimeter, basin_xy )

        basinNameNumMap[ name ] = number

        if model.args.DEBUG_ALL :
            print( record, flush = True )

    # Add boundary Basin objects.
    # Ensure boundary basins do not exist
    for basin in [ 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 
                   71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82 ] :
        if basin in model.Basins.keys() :
            errMsg = 'Duplicate boundary basin number [' + basin + \
                     '] found in shapefile records.'
            raise Exception( errMsg )

    # JP : These boundary basins are Hardcoded... Bogus!
    # 10 Tidal Boundary basins
    model.Basins[ 59 ] = basins.Basin( model, 'Gulf Tide 1', 59,0,0,None,True )
    model.Basins[ 60 ] = basins.Basin( model, 'Gulf Tide 2', 60,0,0,None,True )
    model.Basins[ 61 ] = basins.Basin( model, 'Gulf Tide 3', 61,0,0,None,True )
    model.Basins[ 62 ] = basins.Basin( model, 'Gulf Tide 4', 62,0,0,None,True )
    model.Basins[ 63 ] = basins.Basin( model, 'Ocean Tide 5',63,0,0,None,True )
    model.Basins[ 64 ] = basins.Basin( model, 'Ocean Tide 6',64,0,0,None,True )
    model.Basins[ 65 ] = basins.Basin( model, 'Ocean Tide 7',65,0,0,None,True )
    model.Basins[ 66 ] = basins.Basin( model, 'Ocean Tide 8',66,0,0,None,True )
    model.Basins[ 67 ] = basins.Basin( model, 'Ocean Tide 9',67,0,0,None,True )
    model.Basins[ 68 ] = basins.Basin( model, 'Card Sound Tide 10',68,0,0,
                                       None,True)

    # 12 Everglades Boundary basins
    model.Basins[ 69 ] = basins.Basin( model, 'EVER to Snake Bight',
                                       69,0,0,None,True )
    model.Basins[ 70 ] = basins.Basin( model, 'EVER to Rankin Lake',
                                       70,0,0,None,True )
    model.Basins[ 71 ] = basins.Basin( model, 'EVER to Rankin Bight',
                                       71,0,0,None,True )
    model.Basins[ 72 ] = basins.Basin( model, 'EVER to North Whipray',
                                       72,0,0,None,True )
    model.Basins[ 73 ] = basins.Basin( model, 'EVER to Terrapin Bay',
                                       73,0,0,None,True )
    model.Basins[ 74 ] = basins.Basin( model, 'EVER to Madeira Bay',
                                       74,0,0,None,True )
    model.Basins[ 75 ] = basins.Basin( model, 'EVER to Little Madeira Bay',
                                       75,0,0,None,True )
    model.Basins[ 76 ] = basins.Basin( model, 'EVER to Eagle Key',
                                       76,0,0,None,True )
    model.Basins[ 77 ] = basins.Basin( model, 'EVER to Joe Bay',
                                       77,0,0,None,True )
    model.Basins[ 78 ] = basins.Basin( model, 'EVER to Deer Key',
                                       78,0,0,None,True )
    model.Basins[ 79 ] = basins.Basin( model, 'EVER to Long Sound',
                                       79,0,0,None,True )
    model.Basins[ 80 ] = basins.Basin( model, 'EVER to Manatee Bay',
                                       80,0,0,None,True )
    model.Basins[ 81 ] = basins.Basin( model, 'EVER to Conchie Channel',
                                       81,0,0,None,True )
    model.Basins[ 82 ] = basins.Basin( model, 'EVER to Barnes Sound',
                                       82,0,0,None,True )

    if model.args.DEBUG_ALL :
        for basin_num, Basin in model.Basins.items() :
            print( str( basin_num ), Basin.name )

#----------------------------------------------------------------
# 
#----------------------------------------------------------------
def GetBasinAreaDepths( model ):
    '''Read the GIS data with basin areas at each depth from 
    the basinDepth file (-bd)'''

    if model.args.DEBUG_ALL :
        print( '\n-> GetBasinAreaDepths', flush = True )

    # The csv file has 12 columns, 1 = basin number
    # 2 - 11 = area at each depth, 12 = land area, 
    # first row is header, get the depths from it
    fd   = open( model.args.path + model.args.basinDepth, 'r' )
    rows = fd.readlines()
    fd.close()

    # Get header values (depths) from first row
    row   = rows[ 0 ]  # first row of rows
    words = row.split( ',' )

    depths = npzeros( len( words ) - 2 ) 
    # Skip first and last columns : range( 1, len( row ) - 1 )
    j = 0
    for i in range( 1, len( words ) - 1 ) :
        depths[ j ] = int( words[ i ].strip( 'ft' ) )
        j = j + 1

    # Process each row of data, skip the header
    for i in range( 1, len( rows ) ) :
        row   = rows[ i ]
        words = row.split(',')
            
        basinNumber = int( words[ 0 ] ) # first element of first row

        if model.args.DEBUG_ALL :
            print( 'Basin', basinNumber, end = ': ', flush = True )

        if basinNumber not in model.Basins.keys() :
            continue

        # For each depth save the area in the Basin.wet_area dict 
        for j in range( len( depths ) ) : 
            depth = depths[ j ]
            area  = words[ j + 1 ].strip() # j + 1 for first column
                
            model.Basins[ basinNumber ].wet_area[ depth ] = float( area )

            if model.args.DEBUG_ALL :
                print( depth, '[', j, ']=', area, 
                       end = ' ; ', sep = '', flush = True )

        if model.args.DEBUG_ALL :
            print( '', flush = True )

        # Save the land area
        model.Basins[ basinNumber ].land_area = \
            float( words[ len( words ) - 1 ] )

#----------------------------------------------------------------
# 
#----------------------------------------------------------------
def GetBasinParameters( model ):
    '''Read basin parameters such as Rain/ET/Runoff mappings (-bp)'''

    if model.args.DEBUG_ALL :
        print( '\n-> GetBasinParameters', flush = True )
        for basin_num, Basin in model.Basins.items() :
            print( basin_num, ' : ', Basin.name )

    # The csv file has 5 columns, 1 = basin number, 2 = basin name
    # 3 = [ Rain stations ], 4 = [ Rain scales ], 5 = Salinity station,
    # 6 = Salt factor
    # first row is header
    fd   = open( model.args.path + model.args.basinParameters, 'r' )
    rows = fd.readlines()
    fd.close()

    # Create a mapping of column index and variable name
    header = rows[ 0 ].split( ',' ) 
    words  = [ word.strip() for word in header ]

    var_column_map = dict()
    for word in words :
        var_column_map[ word ] = words.index( word )
            
    # Validate the file has the correct columns
    valid_columns = [ 'Basin', 'Name', 'Rain Gauge',
                      'Rain Scale', 'Gauge', 'Salt Factor' ]

    for valid_column in valid_columns :
        if valid_column not in words :
            errMsg = 'GetBasinParameters: Basin parameters ' +\
                     model.args.basinParameters +\
                     ' does not have column ', valid_column
            raise Exception( errMsg )

    # Process each row of data, skip the header
    for i in range( 1, len( rows ) ) :
        row   = rows[ i ]
        words = row.split( ',' )

        # Get the Basin object
        basin_num  = int( words[ var_column_map[ 'Basin' ] ] )
        basin_name =      words[ var_column_map[ 'Name'  ] ].strip()

        if basin_num not in model.Basins.keys() :
            errMsg = 'GetBasinParameters: Failed to find basin ' +\
                     basin_name + ' number: ', basin_num
            raise Exception( errMsg )

        Basin = model.Basins[ basin_num ]

        # Add list of rain stations and scales to the Basin object
        rain_stations = \
            words[ var_column_map[ 'Rain Gauge' ] ].strip('[] ').split()

        _rain_scales = \
            words[ var_column_map[ 'Rain Scale' ] ].strip('[] ').split()

        rain_scales = list( map( float, _rain_scales ) )

        if not model.args.noRain and not Basin.boundary_basin :
            Basin.rain_stations = rain_stations
            Basin.rain_scales   = rain_scales

        # Add salinity station to the Basin
        salinity_station = words[ var_column_map['Gauge']].strip()

        if model.args.gaugeSalinity or \
           model.args.salinityInit.lower() == 'yes' or \
           Basin.boundary_basin :

            if salinity_station == 'None' :
                pass
            else :
                Basin.salinity_station = salinity_station
                if model.args.gaugeSalinity :
                    Basin.salinity_from_data = True

        # Add salt factor to the Basin
        Basin.salt_factor = float( words[ var_column_map['Salt Factor'] ] )

        if model.args.DEBUG_ALL :
            print( Basin.name, ' [', Basin.number, ']' )
            print( '\t', Basin.rain_stations, ' : ', Basin.rain_scales )
            print( '\t', Basin.salinity_station )

#----------------------------------------------------------------
# 
#----------------------------------------------------------------
def GetBasinTidalData( model ):
    """Read data according to the basinTide file (-bt)

    A scipy interpolate.interp1d function for the tidal anomalies
    is stored in the appropriate basin object.
    
    Note that this takes a long time, and has been parallelized
    with multiprocessing Pool (see below and pool_functions.py)."""
    
    if model.args.DEBUG_ALL :
        print( '\n-> GetBasinTidalData', flush = True )

    msg = 'Reading Tidal Boundary timeseries, please wait...'
    model.gui.Message( msg )
    if not model.args.noGUI :
        model.gui.canvas.show()

    # The csv file has 3 columns: 1 = basin number, 2 = type,
    # 3 = data file name
    fd   = open( model.args.path + model.args.basinTide, 'r' )
    rows = fd.readlines()
    fd.close()

    basinList = []

    # Validate each row of data, skip the header
    for i in range( 1, len( rows ) ) :
        row   = rows[ i ]
        words = row.split(',')
        
        basin     = int ( words[ 0 ] )
        data_type = words[ 1 ].strip()
        data_file = words[ 2 ].strip()

        if basin not in model.Basins.keys() :
            errMsg = 'GetBasinTidalData() Error: Basin ' +\
                     str( basin ) + ' not found in the Basins map.\n'
            raise Exception( errMsg )

        if not model.Basins[ basin ].boundary_basin :
            errMsg = 'GetBasinTidalData() Error: Basin ' +\
                     model.Basins[ basin ].name +\
                     ' is not a boundary_basin.\n'
            raise Exception( errMsg )

        if data_type not in [ 'flow', 'stage', 'None' ] :
            errMsg = 'GetBasinTidalData() Error: Basin ' +\
                      model.Basins[ basin ].name + ' invalid data type: ' +\
                      data_type + '.\n'
            raise Exception( errMsg )

        if model.args.DEBUG_ALL :
            print( '\tValidated: ', str( basin ), data_type, data_file )

        basinList.append( basin )

    # Process each row of data, skip the header
    # ReadTideBoundaryData returns a tuple with basin number and 
    # scipy interpolate.interp1d function which can be called with 
    # a unix time (Epoch seconds) argument to get demeaned tidal elevations.
    N_processors  = cpu_count()
    num_processes = None
    if N_processors > 3 :
        num_processes = 4
    elif N_processors == 2 :
        num_processes = 2
    else :
        num_processes = 1
        
    pool = Pool( processes = num_processes )

    #------------------------------------------------------------
    # Kludge since multiprocessing can't serialize the Tk object
    # embedded in the Model class object. 
    # Explicitly extract and pass args. (path, start, end):
    path  = model.args.path
    start = model.start_time  
    # Add extra time to end_time for model.ReadTideBoundaryData
    end   = model.end_time + timedelta( hours = 3 )

    # Create an iterable object of args to pass to Pool.map_async()
    # rows are the list of lines from the basinTide file (-bt)
    n_row = len( rows ) - 1
    args  = zip( rows[ 1 : ], [start] * n_row, [end] * n_row, [path] * n_row )
    
    # map_async() : A variant of the map() method that returns a result object
    # of class multiprocessing.pool.AsyncResult
    results = pool.map_async( pool_functions.ReadTideBoundaryData, args )
    #------------------------------------------------------------

    # Must call AsyncResult.get() to spawn/wait for map_async() results
    result = results.get()

    msg = 'finished.\n'
    err = True

    # Save the boundary data function to each basin object
    for tide_boundary_tuple in result :
        if tide_boundary_tuple == None : # 'None' 
            continue

        elif tide_boundary_tuple == False :
            msg = '\n\n*** Error in ReadTideBoundaryData. ' +\
                  'Tides not initialized. ***\n\n'
            err = False
            break

        else :
            Basin      = model.Basins[ tide_boundary_tuple[ 0 ] ]
            Basin.boundary_function = tide_boundary_tuple[ 1 ]

            if model.args.DEBUG_ALL :
                print( Basin.name, 
                       ' [', tide_boundary_tuple[ 0 ], ']: Tide value ',
                       tide_boundary_tuple[ 1 ]( 1262305800 ) )

    model.gui.Message( msg )

    return( err )

#----------------------------------------------------------------
# 
#----------------------------------------------------------------
def GetSeasonalMSL( model ):
    """Read data according to the seasonalMSL file (-sm)
    
    A scipy interpolate.splrep() object for the MSL anomalies
    is stored in seasonal_MSL_splrep.  This spline represenation
    is used with the unix_timestamp to generate interpolated values
    via a call to interpolate.splev() in GetTides()"""
    
    if model.args.DEBUG_ALL :
        print( '\n-> GetSeasonalMSL', flush = True )

    # The csv file has 2 columns: 1 = Date, 2 = anomaly
    fd   = open( model.args.path + model.args.seasonalMSL, 'r' )
    rows = fd.readlines()
    fd.close()
    
    unix_times = []
    values     = []

    # Process each row of data, skip the header
    for i in range( 1, len( rows ) ) :
        row   = rows[ i ]
        words = row.split(',')
        
        unix_time = ( strptime( words[ 0 ], '%Y-%m-%d' ) - 
                      datetime(1970,1,1) ).total_seconds()

        unix_times.append( unix_time )

        values.append( float( words[ 1 ] ) )

    # Create the scipy interpolate spline representation
    model.seasonal_MSL_splrep = interpolate.splrep( unix_times, values, s=0 )

#----------------------------------------------------------------
#
#----------------------------------------------------------------
def GetBasinRainData( model ):
    '''Read daily rain data (-br)
    Rain station to basin mappings are listed in the basinParameters
    init file and stored in rain_stations{} in GetBasinParameters().
    
    Populate rain_data dictionary'''

    if model.args.DEBUG_ALL :
        print( '\n-> GetBasinRainData', flush = True )

    # The csv file has 18 columns, 1 = YYYY-MM-DD
    # 2 - 18 = Daily cumulative rainfall in cm at:
    # BK_cm_day, BA_cm_day, BN_cm_day, BS_cm_day, DK_cm_day, GB_cm_day,
    # HC_cm_day, JK_cm_day, LB_cm_day, LM_cm_day, LR_cm_day, LS_cm_day,
    # MK_cm_day, PK_cm_day, TC_cm_day, TR_cm_day, WB_cm_day
    # first row is header
    fd   = open( model.args.path + model.args.basinRain, 'r' )
    rows = fd.readlines()
    fd.close()

    # Create list of station names in the order of the header/columns
    stations = []
    words = rows[ 0 ].split(',')

    for i in range( 1, len( words ) ) :  # Skip the time column
        stations.append( words[ i ].strip()[0:2] )

    # Create list of datetimes
    dates = []
    for i in range( 1, len( rows ) ) :  # Skip the header
        row   = rows[ i ]
        words = row.split(',')
        dates.append( strptime( words[ 0 ], '%Y-%m-%d' ) )

    # Find index in dates for start_time & end_time
    start_i, end_i = GetTimeIndex( 'Rain', dates, 
                                   model.start_time, model.end_time )
        
    if model.args.DEBUG_ALL :
        print( 'Rain data start: ', str( dates[ start_i ] ),str( start_i ), 
               ' end: ',            str( dates[ end_i   ] ),str( end_i ) )
        print( rows[ start_i ] )
        print( rows[ end_i ] )

    # The rain_data is a nested dictionary intended to minimize
    # dictionary key lookups to access basin rainfall for a 
    # specific year month day. The key is an integer 3-tuple of
    # ( Year, Month, Day ), values are a station_rain dictionary.

    # Populate only data needed for the simulation timeframe
    for i in range( start_i, end_i + 1 ) :
        row   = rows[ i+1 ]
        words = row.split(',')

        station_rain = dict()

        for j in range( 1, len( words ) ) :
            station_rain[ stations[ j-1 ] ] = float( words[ j ] )
                
        date = dates[ i ]
        key = ( date.year, date.month, date.day )

        model.rain_data[ key ] = station_rain
            
    if model.args.DEBUG_ALL :
        print( model.rain_data )

#----------------------------------------------------------------
# 
#----------------------------------------------------------------
def GetBasinSalinityData( model ):
    '''Read daily salinity data (-sf)
    Salinity station to basin mappings are listed in the basinParameters
    init file and stored in salinity_stations{} in GetBasinParameters().
    
    Populate salinity_data dictionary'''

    if model.args.DEBUG_ALL :
        print( '\n-> GetBasinSalinityData', flush = True )

    # The csv file has 22 columns, 1 = YYYY-MM-DD
    # 2 - 23 = Daily mean salinty at:
    # BA, BK, BN, BS, DK, GB, HC, JK, LB, LM, LR, LS, MK,
    # PK, TC, TR, WB, MB, MD, TP, Gulf_1, Ocean_1
    # First row is header
    try :
        fd = open( model.args.path + model.args.salinityFile, 'r' )
        rows = fd.readlines()
        fd.close()

    except OSError as err :
        msg = "\nGetBasinSalinityData: OS error: {0}\n".format( err )
        model.gui.Message( msg )
        return

    # Create list of station names in the order of the header/columns
    if len( model.salinity_stations ) == 0 :
        words = rows[ 0 ].split(',')

        for i in range( 1, len( words ) ) :  # Skip the time column
            word = words[ i ].strip()
            model.salinity_stations.append( word.strip('"') )

    # Create list of datetimes
    dates = []
    for i in range( 1, len( rows ) ) :
        row   = rows[ i ]
        words = row.split(',')
        dates.append( strptime( words[ 0 ], '%Y-%m-%d' ) )

    # Find index in dates for start_time & end_time
    start_i, end_i = GetTimeIndex( 'Salinity', dates, 
                                   model.start_time, model.end_time )        
        
    if model.args.DEBUG_ALL :
        print( 'Salinity data start: ', 
                str( dates[ start_i ] ),str( start_i ), 
                ' end: ', str( dates[ end_i   ] ),str( end_i ) )
        print( rows[ start_i ] )
        print( rows[ end_i ] )

    # The salinity_data is a nested dictionary intended to minimize
    # dictionary key lookups to access salinity for a 
    # specific year month day. The key is an integer 3-tuple of
    # ( Year, Month, Day ), values are a station_salinity dictionary.
    if model.salinity_data :
        model.salinity_data.clear()

    # Populate only data needed for the simulation timeframe
    for i in range( start_i, end_i + 1 ) :
        row   = rows[ i+1 ]
        words = row.split(',')

        station_salinity = dict()

        for j in range( 1, len( words ) ) :
            if words[ j ] == 'NA' :
                salinity_value = 'NA'
            else:
                salinity_value = float( words[ j ] )
                
            station_salinity[ model.salinity_stations[ j-1 ] ] = salinity_value
                
        date = dates[ i ]
        key  = ( date.year, date.month, date.day )

        model.salinity_data[ key ] = station_salinity
        
    if model.args.DEBUG_ALL :
        print( model.salinity_data )

#-----------------------------------------------------------
#
#-----------------------------------------------------------
def SetInitialBasinSalinity( model ) :
    '''Based on the basinParameter { station : basin } mapping,
    assign the initial salinity values at start_time'''

    if model.args.DEBUG_ALL :
        print( '\n-> SetInitialBasinSalinity', flush = True )

    key = ( model.start_time.year, 
            model.start_time.month, 
            model.start_time.day )

    station_salinity_map = model.salinity_data[ key ]

    for Basin in model.Basins.values() :
        if Basin.salinity_station :
            try:
                salinity_gauge = \
                    float( station_salinity_map[ Basin.salinity_station ] )
            except ValueError:
                # Salinity data can contain 'NA' if no data available...
                salinity_gauge = 0

                msg = '\nSetInitialBasinSalinity: WARNING:' +\
                      ' Basin ' + Basin.name + ' has no available salinity' +\
                      ' data to initialize Basin.salinity... setting to 0.\n'
                model.gui.Message( msg )  
            
            Basin.salinity = salinity_gauge
        
        if model.args.DEBUG_ALL :
            print( Basin.name, ' [', str( Basin.number ),
                   '] : ', Basin.salinity )

    # recompute salt_mass for all basins
    for Basin in model.Basins.values() :
        # salt_mass (g) = salinity (g/kg) * Vol (m^3) * rho (kg/m^3)
        Basin.salt_mass = Basin.salinity * Basin.water_volume * 997

#----------------------------------------------------------------
# 
#----------------------------------------------------------------
def GetETData( model ):
    '''Read daily ET data (-et)'''

    if model.args.DEBUG_ALL :
        print( '\n-> GetETData', flush = True )

    # The csv file has 2 columns, 1 = YYYY-MM-DD, 2 = PET mm/day
    # first row is header
    fd   = open( model.args.path + model.args.ET, 'r' )
    rows = fd.readlines()
    fd.close()

    # Create list of datetimes
    dates = []
    for i in range( 1, len( rows ) ) :
        row   = rows[ i ]
        words = row.split(',')
        dates.append( strptime( words[ 0 ], '%Y-%m-%d' ) )

    # Find index in dates for start_time & end_time
    start_i, end_i = GetTimeIndex( 'ET', dates, 
                                   model.start_time, model.end_time )        
        
    if model.args.DEBUG_ALL :
        print( 'ET data start: ', str( dates[ start_i ] ), str( start_i ), 
               ' end: ',          str( dates[ end_i   ] ), str( end_i ) )
        print( rows[ start_i ] )
        print( rows[ end_i ] )

    # Populate only data needed for the simulation timeframe
    for i in range( start_i, end_i + 1 ) :
        row   = rows[ i+1 ]
        words = row.split(',')

        # The key is an integer 3-tuple of ( Year, Month, Day )
        # values are PET in mm/day.
        date = dates[ i ]
        key = ( date.year, date.month, date.day )
        model.et_data[ key ] = float( words[1] )
            
    if model.args.DEBUG_ALL :
        print( model.et_data )

#----------------------------------------------------------------
# 
#----------------------------------------------------------------
def GetBasinRunoffStageData( model ):
    '''Read daily stage data for Everglades basins (-bR)
    Mapping of EDEN stage data in basinStageRunoff to model basins
    is specified in basinStageRunoffMap (-bS)

    Populate runoff_stage_data dictionary'''

    if model.args.DEBUG_ALL :
        print( '\n-> GetBasinRunoffStageData', flush = True )

    # Get mapping of EDEN stage station to model basins
    fd   = open( model.args.path + model.args.basinStageRunoffMap, 'r' )
    rows = fd.readlines()
    fd.close()

    # Create a mapping of column index and variable name
    header = rows[ 0 ].split( ',' ) 
    words  = [ word.strip() for word in header ]

    var_column_map = dict()
    for word in words :
        var_column_map[ word ] = words.index( word )
            
    # Validate the file has the correct columns
    valid_columns = [ 'Source_Basin', 'EDEN_Station',
                      'Dest_Basin',   'Shoals' ]

    for valid_column in valid_columns :
        if valid_column not in words :
            errMsg = 'EVER basin runoff ' + model.args.basinStageRunoffMap +\
                     ' does not have ', valid_column
            raise Exception( errMsg )

    # Get Basin : EDEN station data mapping
    # The basinStageRunoffMap also contains the shoals between the 
    # EVER boundary basins and model basins, and the destination 
    # basin in the model for the runoff. 
    for i in range( 1, len( rows ) ) :  # Skip the header
        row   = rows[ i ]
        words = row.split(',')

        EVER_basin_num = int( words[ var_column_map['Source_Basin'] ] )

        EVER_Basin = model.Basins[ EVER_basin_num ]

        model.runoff_stage_basins[ EVER_Basin ] =\
            words[ var_column_map['EDEN_Station'] ].strip()

        model_basin_num = int( words[ var_column_map['Dest_Basin'] ] )

        shoals = words[ var_column_map['Shoals'] ].strip('[] \n').split()
        shoal_nums = list( map( int, shoals ) )

        # Save list of Shoal objects in runoff_stage_shoals map
        # { Basin Object : [ Shoal Objects ] }
        model.runoff_stage_shoals[ model.Basins[ model_basin_num ] ] =\
            [ model.Shoals[ shoal_num ] for shoal_num in shoal_nums ]

    # Validate the Shoals : Basins
    for Basin, Shoals in model.runoff_stage_shoals.items() :

        for Shoal in Shoals :
            if Basin is Shoal.Basin_A :
                continue
            elif Basin is Shoal.Basin_B :
                continue
            else :
                errMsg = 'GetBasinRunoffStageData: Invalid Basin: ' +\
                         Basin.name + ' for shoal with A: ' +\
                         Shoal.Basin_A.name + ' B: ' + Shoal.Basin_B.name +\
                         ' in runoff_stage_shoals map basinStageRunoffMap (-bS)'
                raise ValueError( errMsg )


    if model.args.DEBUG_ALL :
        print( 'GetBasinRunoffStageData: runoff_stage_shoals:\n' )
        print( model.runoff_stage_shoals )

    # Load stage data into the runoff_stage_data dictionary
    # The csv file has 9 columns, 1 = YYYY-MM-DD
    # 2 - 9 = Daily EDEN stage in (m) offset to MSL anomaly:
    # S22, S21, S20, S19, S18, S17, S16, S15
    # first row is header
    fd   = open( model.args.path + model.args.basinStageRunoff, 'r' )
    rows = fd.readlines()
    fd.close()
    
    # Create list of station names in the order of the header/columns
    stations = []
    words = rows[ 0 ].split(',')

    for i in range( 1, len( words ) ) :  # Skip the time column
        stations.append( words[ i ].strip() )

    # Create list of datetimes
    dates = []
    for i in range( 1, len( rows ) ) :  # Skip the header
        row   = rows[ i ]
        words = row.split(',')
        dates.append( strptime( words[ 0 ], '%Y-%m-%d' ) )

    # Find index in dates for start_time & end_time
    start_i, end_i = GetTimeIndex( 'Runoff', dates, 
                                   model.start_time, model.end_time )
        
    if model.args.DEBUG_ALL :
        print( 'Runoff data start: ',str(dates[ start_i ]),str( start_i ), 
               ' end: ',             str(dates[ end_i   ]),str( end_i ) )
        print( rows[ start_i ] )
        print( rows[ end_i ] )

    # The runoff_stage_data is a nested dictionary intended to minimize
    # dictionary key lookups to access basin stage for a 
    # specific year month day. The key is an integer 3-tuple of
    # ( Year, Month, Day ), values are { station : stage }.

    # Populate only data needed for the simulation timeframe
    for i in range( start_i, end_i + 1 ) :
        row   = rows[ i+1 ]
        words = row.split(',')

        station_stage = dict()

        for j in range( 1, len( words ) ) :
            station_stage[ stations[ j-1 ] ] = float( words[ j ] )
                
        date = dates[ i ]
        key = ( date.year, date.month, date.day )

        model.runoff_stage_data[ key ] = station_stage
            
    if model.args.DEBUG_ALL :
        print( model.runoff_stage_basins )
        print( model.runoff_stage_data )

#----------------------------------------------------------------
# 
#----------------------------------------------------------------
def GetBasinDynamicBCData( model ):
    '''Read daily runoff flow or stage data (-db) from -bc file,
    Populate dynamic_flow_boundary and/or dynamic_head_boundary dictionary'''
    
    if model.args.DEBUG :
        print( '\n-> GetBasinDynamicBCData', flush = True )

    # Get mapping of model basins to BC timeseries
    fd   = open( model.args.path + model.args.basinBCFile, 'r' )
    rows = fd.readlines()
    fd.close()

    # Create a mapping of column index and variable name
    header = rows[ 0 ].split( ',' ) 
    words  = [ word.strip() for word in header ]

    var_column_map = dict()
    for word in words :
        var_column_map[ word ] = words.index( word )
            
    # Validate the file has the correct columns
    valid_columns = [ 'Basin', 'Name', 'Type', 'File' ]

    for valid_column in valid_columns :
        if valid_column not in words :
            errMsg = 'Dynamic BC file ' + model.args.basinBCFile +\
                     ' does not have ', valid_column
            raise Exception( errMsg )

    # Process each row 
    # Get Basin : BC Type and data file mapping and fill in the
    # dynamic_flow_boundary or dynamic_head_boundary as appropriate
    for i in range( 1, len( rows ) ) :  # Skip the header
        row   = rows[ i ]
        words = row.split(',')

        basin_num  = int( words[ var_column_map['Basin'] ] )
        basin_name = words[ var_column_map['Name'] ].strip()
        data_type  = words[ var_column_map['Type'] ].strip()
        bc_file    = words[ var_column_map['File'] ].strip()

        Basin = model.Basins[ basin_num ]

        if Basin.name != basin_name :
            errMsg = 'GetBasinDynamicBCData: Basin ' + basin_num +\
                     ' ' + Basin.name + ' does not match ' + basin_name +\
                     ' in file ' + model.args.basinBCFile + '\n'
            raise Exception( errMsg )

        if data_type not in [ 'flow', 'stage' ] :
            errMsg = 'GetBasinDynamicBCData: Basin ' + basin_num +\
                     ' ' + Basin.name + ' Type ' + data_type +\
                     ' must be flow or stage in file '+\
                     model.args.basinBCFile + '\n'
            raise Exception( errMsg )
            
        # Load flow or stage data into the appropriate dictionary
        # The csv file has 2 columns, 1 = YYYY-MM-DD, 2 = value
        # first row is header
        fd   = open( model.args.path + bc_file, 'r' )
        rows = fd.readlines()
        fd.close()

        # Create list of datetimes
        dates = []
        for i in range( 1, len( rows ) ) :  # Skip the header
            row   = rows[ i ]
            words = row.split(',')
            dates.append( strptime( words[ 0 ], '%Y-%m-%d' ) )

        # Find index in dates for start_time & end_time
        start_i, end_i = GetTimeIndex( 'BC ' + data_type, dates, 
                                       model.start_time, model.end_time )
        
        if model.args.DEBUG_ALL :
            print( data_type, 
                   ' BC data start: ', str(dates[start_i]),str(start_i), 
                   ' end: ',           str(dates[ end_i ]),str( end_i ) )
            print( rows[ start_i ] )
            print( rows[ end_i   ] )

        # The dynamic_*_boundary is a nested dictionary intended to minimize
        # dictionary key lookups to access basin stage for a 
        # specific year month day. The key is a Basin object,
        # values are { ( Year, Month, Day ), : volume or head }.
        basin_BC_map = dict() # { ( Year, Month, Day ) : bc_value }

        # Populate only data needed for the simulation timeframe
        for i in range( start_i, end_i + 1 ) :
            row   = rows[ i+1 ]
            words = row.split(',')

            basin_value = dict()

            bc_value = float( words[ 1 ] )
                
            date = dates[ i ]
            key  = ( date.year, date.month, date.day )

            # flow assumed to be cfs, convert to timestep volume
            if data_type == 'flow' :
                bc_value = bc_value * model.timestep

            basin_BC_map[ key ] = bc_value

            if data_type == 'flow' :
                model.dynamic_flow_boundary[ Basin ] = basin_BC_map

            elif data_type == 'stage' :
                model.dynamic_head_boundary[ Basin ] = basin_BC_map

    if model.args.DEBUG_ALL :
        print( model.dynamic_flow_boundary )
        print( model.dynamic_head_boundary )

#----------------------------------------------------------------
# 
#----------------------------------------------------------------
def GetBasinFixedBoundaryCondition( model ):
    """Read data according to the basinFixedBCFile file (-bf)"""
    
    if model.args.DEBUG_ALL :
        print( '\n-> GetBasinFixedBoundaryCondition', flush = True )

    # The csv file has 4 columns: 1 = basin number, 2 = basin name,
    # 3 = type, 4 = value.  Value must be a numeric. 
    fd   = open( model.args.path + model.args.basinFixedBCFile, 'r' )
    rows = fd.readlines()
    fd.close()

    # Validate each row of data, skip the header
    for i in range( 1, len( rows ) ) :
        row   = rows[ i ]
        words = row.split(',')
            
        basin      = int ( words[ 0 ] )
        basin_name = words[ 1 ].strip()
        data_type  = words[ 2 ].strip()
        data_value = words[ 3 ].strip()

        if basin not in model.Basins.keys() :
            errMsg = 'GetBasinFixedBoundaryCondition() Error: Basin ' +\
                      basin + ' not found in the Basins map.\n'
            raise Exception( errMsg )

        if model.Basins[ basin ].name != basin_name :
            errMsg = 'GetBasinFixedBoundaryCondition() Error: Basin ' +\
                      str( basin ) + '[' + model.Basins[ basin ].name +\
                      '] does not match ' + basin_name + ' in '       +\
                      model.args.basinFixedBCFile + '\n'
            raise Exception( errMsg )

        if model.Basins[ basin ].boundary_basin :
            errMsg = 'GetBasinFixedBoundaryCondition() Error: Basin ' +\
                      model.Basins[ basin ].name + ' is a boundary_basin.\n'
            raise Exception( errMsg )

        if data_type not in [ 'flow', 'stage', 'None' ] :
            errMsg = 'GetBasinFixedBoundaryCondition() Error: Basin ' +\
                      model.Basins[ basin ].name + ' invalid data type: ' +\
                      data_type + '.\n'
            raise Exception( errMsg )

        if model.args.DEBUG_ALL :
            print( '\tValidated: ', basin, data_type, data_value )

        # Insert BC values into model.fixed_boundary 
        if data_type in [ 'flow', 'stage'] :
            model.fixed_boundary[ basin ] = ( data_type, data_value )

#----------------------------------------------------------------
# 
#----------------------------------------------------------------
def GetBasinStageData( model ):
    '''Read daily stage data (-bs)
    Stage station to basin mappings are listed in the basinParameters
    init file and stored in stage_stations{} in GetBasinParameters()
    and are the same as the Salinity Gauge. 
    This data is not used in the model, only for output comparison.
    
    Populate stage_data dictionary'''

    if model.args.DEBUG_ALL :
        print( '\n-> GetBasinStageData', flush = True )

    # The csv file has 21 columns, 1 = YYYY-MM-DD
    # 2 - 21 = Daily mean stage at:
    # BK, BA, BN, BS, DK, GB, HC, JK, LB, LM, LR, LS,
    # MK, PK, TC, TR, WB, TP, MD, MB
    # first row is header
    try :
        fd = open( model.args.path + model.args.basinStage, 'r' )
        rows = fd.readlines()
        fd.close()

    except OSError as err :
        msg = "\nGetBasinStageData: OS error: {0}\n".format( err )
        model.gui.Message( msg )
        return

    # Create list of station names in the order of the header/columns
    if len( model.stage_stations ) == 0 :
        words = rows[ 0 ].split(',')

        for i in range( 1, len( words ) ) :  # Skip the time column
            word = words[ i ].strip()
            model.stage_stations.append( word.strip('"') )

    # Create list of datetimes
    dates = []
    for i in range( 1, len( rows ) ) :
        row   = rows[ i ]
        words = row.split(',')
        dates.append( strptime( words[ 0 ], '%Y-%m-%d' ) )

    # Find index in dates for start_time & end_time
    start_i, end_i = GetTimeIndex( 'Stage', dates, 
                                   model.start_time, model.end_time )        

    if model.args.DEBUG_ALL :
        print( 'Stage data start: ', 
                str( dates[ start_i ] ),str( start_i ), 
                ' end: ', str( dates[ end_i   ] ),str( end_i ) )
        print( rows[ start_i ] )
        print( rows[ end_i ] )

    # The stage_data is a nested dictionary intended to minimize
    # dictionary key lookups to access stage for a 
    # specific year month day. The key is an integer 3-tuple of
    # ( Year, Month, Day ), values are a stage_salinity dictionary.
    if model.stage_data :
        model.stage_data.clear()

    # Populate only data needed for the simulation timeframe
    for i in range( start_i, end_i + 1 ) :
        row   = rows[ i+1 ]
        words = row.split(',')

        station_stage = dict()

        for j in range( 1, len( words ) ) :
            if 'NA' in words[ j ].strip() :
                stage = None
            else :
                stage = float( words[ j ] )

            station_stage[ model.stage_stations[ j-1 ] ] = stage
                
        date = dates[ i ]
        key  = ( date.year, date.month, date.day )

        model.stage_data[ key ] = station_stage
        
    if model.args.DEBUG_ALL :
        print( model.stage_data )

#----------------------------------------------------------------
# 
#----------------------------------------------------------------
def InitialBasinValues( model ):
    '''Read initial state values for basins 
    from the basinInit file (-bi)'''

    if model.args.DEBUG_ALL :
        print( '\n-> InitialBasinValues', flush = True )

    init_file = model.args.path + model.args.basinInit

    # The csv file has 11 columns, 1 = basin number, 2 = Stage, 3 = Temp,
    # 4 = DO, 5 = Salinity, 6 = TOC, 7 = TOP, 8 = TON, 9 = Phosphate
    # 10 = Nitrate, 11 = Ammonium
    # first row is header
    try :
        fd = open( init_file, 'r' )
    except OSError as err :
        msg = "\nInitialBasinValues: OS error: {0}\n".format( err )
        model.gui.Message( msg )
        return

    rows = fd.readlines()
    fd.close()

    # Get header labels from first row
    variable_names = rows[ 0 ].split( ',' )

    # Validate that it's a Basin init file
    columns = [ 'Basin', 'Name', 'Stage_cm', 'Temperature_C',
                'DissolvedOxygen_mg/L', 'Salinity_ppt',
                'TotalOrganicCarbon_mmol/m^3',
                'TotalOrganicPhosphorus_mmol/m^3',
                'TotalOrganicNitrogen_mmol/m^3',
                'Phosphate_mmol/m^3',
                'Nitrate_mmol/m^3', 'Ammonium_mmol/m^3\n' ]

    if len( set(variable_names).intersection(columns) ) != len(columns) :
        msg = '\nError: The basin initialization file: ' + init_file +\
              ' does not have the correct column variables.\n'
        model.gui.Message( msg )
        return( False )

    if len( variable_names ) != 12 :
        msg = '\nError: The basin initialization file: ' + init_file +\
              ' does not have the correct number of column variables.\n'
        model.gui.Message( msg )
        return( False )

    # Process each row of data, skip the header
    for i in range( 1, len( rows ) ) :
        row   = rows[ i ]
        words = row.split(',')
            
        basin = int ( words[ 0 ] )
        if basin not in model.Basins.keys() :
            msg = '*** InitialBasinValues: Basin ' + words[ 1 ] + ' [' +\
                   str( basin ) + '] is not in the model Basins.' +\
                  ' File: ' + init_file + '\n'
            model.gui.Message( msg )
            continue

        model.Basins[ basin ].water_level              = float( words[ 2 ] )
        model.Basins[ basin ].temperature              = float( words[ 3 ] )
        model.Basins[ basin ].dissolved_oxygen         = float( words[ 4 ] )
        model.Basins[ basin ].salinity                 = float( words[ 5 ] )
        model.Basins[ basin ].total_organic_carbon     = float( words[ 6 ] )
        model.Basins[ basin ].total_organic_phosphorus = float( words[ 7 ] )
        model.Basins[ basin ].total_organic_nitrogen   = float( words[ 8 ] )
        model.Basins[ basin ].phosphate                = float( words[ 9 ] )
        model.Basins[ basin ].nitrate                  = float( words[ 10] )
        model.Basins[ basin ].ammonium                 = float( words[ 11] )

    return( True )

#----------------------------------------------------------------
# 
#----------------------------------------------------------------
def CreateShoals( model ):
    '''Read the GIS data with shoal width and lengths at each depth
    from the shoalLength file (-sl)'''
    
    if model.args.DEBUG_ALL :
        print( '\n-> GetShoalLengthDepth', flush = True )

    # Make a map of shoal numbers/xy points from shapefile records 
    # 'Line_Numbe' field which is the first element of the field field[0]
    # ['Line_Numbe', 'N', 16, 6]
    # This is used below to assign the line_xy to each Shoal object
    sf_shoals = shapefile.Reader( model.args.shoalShapeFile )
    shoal_xy_map = dict()
    for record, shape in zip( sf_shoals.records(), sf_shoals.shapes() ) :
        shoal_xy_map[ int( record[0] ) ] = nparray( shape.points )

    # The csv file has 14 columns, 1 = shoal number, 2 = shoal width,
    # 3 - 12 = length at each depth, 13 = land length, 14 = Mannings
    # first row is header, get the depths from it
    fd = open( model.args.path + model.args.shoalLength, 'r' )
    rows = fd.readlines()
    fd.close()

    # Get header values (depths) from first row
    row   = rows[ 0 ]  # first row of rows from csv.reader
    words = row.split( ',' )

    depths = list( range( 2, len( words ) - 2 ) )
    # Skip first two, and last two columns : range( 2, len( row ) - 2 )
    j = 0
    for i in range( 2, len( words ) - 2 ) :
        depths[ j ] = int( words[ i ].strip( 'ft' ) )
        j = j + 1

    # Process each row of data, skip the header
    for i in range( 1, len( rows ) ) :

        # Instantiate the Shoal
        shoal = shoals.Shoal( model )

        row   = rows[ i ]
        words = row.split(',')
            
        shoalNumber = int( words[ 0 ] ) # first element of first row

        width = float( words[ 1 ].strip() ) # second element of row
        shoal.width = width
            
        if model.args.DEBUG_ALL :
            print( 'Shoal', shoalNumber, 'width', width,
                   end = ': ', flush = True )

        # For each depth save the length in the Shoal wet_length dict 
        for j in range( len( depths ) ) : 
            depth  = depths[ j ]
            length = float( words[ j + 2 ].strip() ) # j + 2 for two column
                
            shoal.wet_length[ depth ] = length

            # If there is a length, initialize a friction_factor for depth
            if length > 0 :
                shoal.friction_factor[ depth ] = 0

            if model.args.DEBUG_ALL :
                print( depth, '[', j, ']=', length, 
                       end = ' ; ', sep = '', flush = True )

        # If shoal width is zero set no_flow
        if shoal.width == 0 :
            shoal.no_flow = True

        if model.args.DEBUG_ALL :
            print( '', flush = True )

        # Save the land length
        shoal.land_length = float( words[ len( words ) - 2 ].strip() )

        # Save Mannings unless overridden with -sf
        if model.args.shoalManning :
            shoal.manning_coefficient = model.args.shoalManning
        else :
            shoal.manning_coefficient = float(words[len( words ) - 1].strip())

        if model.args.DEBUG_ALL :
            print( 'Shoal', shoalNumber, 'manning', 
                   shoal.manning_coefficient, end = ': ', flush = True )

        # Save the line_xy from the shapefile map above
        # Note that shoals 1 - 6 are not in the shapefile records above
        if shoalNumber in shoal_xy_map.keys() :
            shoal.line_xy = shoal_xy_map[ shoalNumber ]

        model.Shoals[ shoalNumber ] = shoal

#----------------------------------------------------------------
# 
#----------------------------------------------------------------
def GetShoalParameters( model ):
    '''Read shoalParameters: adjacent basins (-sp)'''

    if model.args.DEBUG_ALL :
        print( '\n-> GetShoalParameters', flush = True )

    # The csv file has 3 columns
    # 1 = shoal number, 2 = Basin_A, 3 = Basin_B
    # first row is header
    fd = open( model.args.path + model.args.shoalParameters, 'r' )
    rows = fd.readlines()
    fd.close()

    # Get header names from first row: Shoal, Basin_A, Basin_B
    row   = rows[ 0 ]  # first row of rows from csv.reader
    words = row.split( ',' )

    # Create mapping of column name and an index into words
    keys = []
    for word in words :
        keys.append( word.strip() )

    VarIndex = dict( zip( keys, range( len( words ) ) ) )

    # Process each row of data, skip the header
    for i in range( 1, len( rows ) ) :

        row   = rows[ i ]
        words = row.split(',')
            
        shoalNumber = int  ( words[ VarIndex['Shoal'  ] ].strip() )
        basin1      = int  ( words[ VarIndex['Basin_A'] ].strip() )
        basin2      = int  ( words[ VarIndex['Basin_B'] ].strip() )

        if basin1 == 0 or basin2 == 0 :
            if shoalNumber in model.Shoals.keys() :
                del model.Shoals[ shoalNumber ]

            continue  # a shoal that doesn't connect??... Nice!

        if model.args.DEBUG_ALL :
            print( 'Shoal', shoalNumber, basin1, basin2, flush = True )

        if shoalNumber not in model.Shoals :
            errMsg = 'Shoal ' + shoalNumber + ' is not in the Shoals map'
            raise Exception( errMsg )

        model.Shoals[ shoalNumber ].name = shoalNumber
            
        # Set the appropriate basin shoal objects
        Shoal = model.Shoals[ shoalNumber ]

        if basin1 in model.Basins.keys() :
            Basin = model.Basins[ basin1 ]

            Basin.shoal_nums.add( shoalNumber )
            Basin.Shoals.append ( Shoal )
            Shoal.Basin_A_key = basin1
            Shoal.Basin_A     = Basin

        if basin2 in model.Basins.keys() :
            Basin = model.Basins[ basin2 ]

            Basin.shoal_nums.add( shoalNumber )
            Basin.Shoals.append( Shoal )
            Shoal.Basin_B_key = basin2
            Shoal.Basin_B     = Basin

#----------------------------------------------------------------
# 
#----------------------------------------------------------------
def GetTimeIndex( type, dates, start_time, end_time ) :
    '''Find array indices for start and end times in dates.'''

    # Check start & end time is within the data window
    if start_time < dates[ 0 ] :
        errMsg = 'GetTimeIndex: start time ' +\
                 str( end_time ) +\
                 ' is prior to the earliest ' + type + ' data at time: ' +\
                 str( dates[ 0 ] )
        raise Exception( errMsg )

    if end_time > dates[ len( dates ) - 1 ] :
        errMsg = 'GetTimeIndex: end time ' + str( end_time ) +\
                 ' is after the latest ' + type + ' data at time:' +\
                 str( dates[ len( dates ) - 1 ] )
        raise Exception( errMsg )


    try :
        start_i = dates.index( start_time )
    except ValueError :
        # No exact match: find the first dates[] before start_time
        i = 0
        for date in dates :
            if date > start_time :
                break
            i += 1

        if i >= len( dates ) :
            errMsg = 'GetTimeIndex: Failed to find start_time for ' + type
            raise Exception( errMsg )

        start_i = i

    # Find index in dates for end_time
    try :
        end_i = dates.index( end_time   )
    except ValueError :
        # No exact match: find the first dates[] before end_time
        i = 0
        for date in dates :
            if date > end_time :
                break
            i += 1

        if i >= len( dates ) :
            errMsg = 'GetTimeIndex: Failed to find end_time for ' + type
            raise Exception( errMsg )

        end_i = i

    return( ( start_i, end_i ) )
