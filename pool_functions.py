'''Multiprocess function to read tidal boundary data for the Bay Assessment
   Model (BAM)'''

# Python distribution modules
from datetime import datetime
strptime = datetime.strptime

# Community modules
from scipy import interpolate
from numpy import zeros as npzeros

#-----------------------------------------------------------
# 
#-----------------------------------------------------------
def ReadTideBoundaryData( args ) :
    '''Read and interpolate tidal boundary condition data.

    Returns a tuple with the basin number and scipy interpolate.interp1d 
    function, which can be called with a unix time (Epoch seconds) argument 
    to get the demeaned tidal elevations. 

    Kludge: 
    Since multiprocess (and multiprocessing) can't handle objects with Tk 
    instances, this function has been separated so that it can be called 
    without a model object. It should be a Model class method...'''

    line       = args[0] 
    start_time = args[1]
    end_time   = args[2]
    path       = args[3]

    words = line.split( ',' )
    
    basin     = int ( words[ 0 ] )
    data_type = words[ 1 ].strip()
    data_file = words[ 2 ].strip()

    #print( '->  ReadTideBoundaryData: ', basin, data_type, data_file )

    if data_type == 'None' :
        return( None )

    if data_type not in [ 'stage' ] :
        msg = 'ReadTideBoundaryData() Invalid data type: ' +\
              data_type + '\n'
        print( msg, flush = True )
        return( False )

    # The csv file has 2 columns: 1 = Date-time, 2 = data value
    # Time, WL.(m).demeaned
    # 1990-01-01 12:00 AM EST, -0.086
    # 1990-01-01 1:00 AM EST, 0.166
    try:
        fd = open( path + data_file, 'r' )
    except OSError as err :
        msg = "ReadTideBoundaryData() OS error: {0}\n".format( err )
        print( msg, flush = True )
        return( False )

    rows = fd.readlines()
    fd.close()

    # Find rows closest to the start_time & end_time
    datetimes = []
    times     = []
    data      = npzeros( ( len( rows ) - 1 ) )
    
    # Format the date and copy each row of data, skip the header
    for i in range( 1, len( rows ) ) :
        row   = rows[ i ]
        words = row.split(',')

        date_time = strptime( words[ 0 ], '%Y-%m-%d %I:%M %p %Z' ) 
        datetimes.append( date_time )
        times.append( (date_time - datetime(1970, 1, 1) ).total_seconds() )

        data[ i - 1 ] = float( words[ 1 ] )

    # Now search for times in the data that match the simulation start/end
    start_i = 0
    end_i   = 0

    try: 
        start_i = datetimes.index( start_time )
    except ValueError :
        msg = 'ReadTideBoundaryData() Model start time: ' + str( start_time ) +\
              ' is not in the tide boundary data: ' + data_file + '\n'
        print( msg, flush = True )
        return( False )

    try: 
        end_i = datetimes.index( end_time )
    except ValueError :
        msg = 'ReadTideBoundaryData() Model end time: ' + str( end_time ) +\
              ' is not in the tide boundary data: ' + data_file + '\n'
        print( msg, flush = True )
        return( False )

    #print( '   Found start ', times[ start_i ], ' and end ', 
    #       times[ end_i ] )

    tide_observations = data [ start_i : end_i ]
    tide_seconds      = times[ start_i : end_i ]

    #print( tide_seconds )
    #print( tide_observations )

    interpolation_function = interpolate.interp1d( tide_seconds, 
                                                   tide_observations )

    return( tuple( ( basin, interpolation_function ) ) )
