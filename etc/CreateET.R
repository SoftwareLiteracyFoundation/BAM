
#-----------------------------------------------------------------
#
#-----------------------------------------------------------------
CreateETData = function( path = '../data/ET/',
                         file = 'PET_EDEN_1999-9-1_2015-12-31.Rdata',
                         out  = 'PET_1999-9-1_2015-12-31.Rdata' )
{

  # Read input data
  df = get( load( paste( path, file, sep = '' ) ) )
  df.in = df

  # Vector of indices of missing data
  i.na = which( is.na( df $ PET ) )

  if ( length( i.na ) ) {
    print( 'Missing data NA at i =' )
    print( i.na )
    
    # brute force... create yearday samples of available data
    date.lt   = as.POSIXlt( df $ Time )
    days      = seq( 1, 365 )
    data.yday = list()
    
    for ( day in days ) {
      i.yday = which( date.lt $ yday == day )
      
      yday.data = df[ i.yday, 'PET' ]
      i.na      = which( is.na( yday.data ) )
      yday.data = yday.data[ -i.na ]
      
      data.yday[[ day ]] = yday.data
    }

    print( paste( length( data.yday ), 'data sets created.' ) )

    # Fill missing data
    for ( i in i.na ) {
      yday = date.lt[ i ] $ yday
      
      if ( yday == 0 ) { yday = 1 }
      
      # Choose randomly from the available data for this yearday
      value = mean( sample( data.yday[[ yday ]], size = 2, replace = TRUE ) )
      #value = sample( data.yday[[ yday ]], size = 1 )
      # Assing to the missing data
      df[ i, 'PET' ] = value
    }
  }

  if ( is.null( dev.list() ) ) { newPlot() }
  plot( df $ Time, df $ PET, type = 'l', col = 'red', ylab = 'mm/day' )
  lines( df.in $ Time, df.in $ PET )
  
  save( df, file = paste( path, out, sep = '' ) )
  
  write.csv( df, file = paste( path, sub( '.Rdata', '.csv', out ), sep = '' ),
             quote = FALSE, row.names = FALSE )
  
  invisible( df )
}

#-----------------------------------------------------------------
# Data from EDEN/EVE : USGS GOES estimates via Priestley-Taylor
#-----------------------------------------------------------------
Read.EDEN.ET.Data = function( path = '../data/ET/',
                              file = 'PET_EDEN.csv',
                              out  = 'PET_EDEN_1999-9-1_2015-12-31.Rdata' )
{

  # Date, Joe_Bay_2E, Mud_Creek_at_mouth, Taylor_River_at_mouth, Trout_Creek_at_mouth
  # 1999-09-01, 6.18, 6.34, 6.38, 6.15
  # 1999-09-02, 4.64, 5.09, 4.8,  4.55
  # 1999-09-03, 6.26, 6.15, 6.14, 6.12
  df.in = read.csv( paste( path, file, sep = '' ), header = TRUE, as.is = TRUE )

  time.lt = strptime( df.in $ Date, '%Y-%m-%d' )

  # Daily max of the 4 stations 
  PET.mm.day = apply( df.in[ , c( 2, 3, 4, 5 )], 1, max )

  df = data.frame( Time = as.POSIXct(time.lt, origin='1970-01-01', tz = 'EST'),
                   PET = PET.mm.day )

  #-------------------------------------------------------
  if( is.null( dev.list() ) ) { newPlot() }
  plot( df $ Time, df $ PET, type = 'l', ylab = 'mm/day' )

  save( df, file = paste( path, out, sep = '' ) )
  
  invisible( df )
}

#-----------------------------------------------------------------
# SFWMD data via Abtew simple method
# DBHYDRO : EVAPOTRANS POTENTIAL, MM
# http://my.sfwmd.gov/dbhydroplsql/show_dbkey_info.show_dbkeys_matched?v_js_flag=Y&v_category=WEATHER&v_data_type=ETP&v_dbkey_list_flag=Y&v_order_by=STATION
#-----------------------------------------------------------------
Read.SFWMD.ET.Data = function( path = '../data/ET/',
                               file = 'PET_Dade_sfwmd.csv',
                               out  = 'PET_Dade_sfwmd.Rdata' )
{

  # Date,        JBTS_C111, S331W_L31NS, 3AS3WX_WCA3, Max_mm_day
  # 01-SEP-1999,      2.99,        3.36,          NA,     3.36
  # ....
  # 30-APR-2015,      2.32,        2.04,         2.11,     2.32
  df.in = read.csv( paste( path, file, sep = '' ), header = TRUE,
                    stringsAsFactors = FALSE,
                    colClasses = c( 'character', 'numeric', 'numeric', 
                                    'numeric',   'numeric' ) )

  time.lt = strptime( df.in $ Date, '%d-%b-%Y' )

  PET.mm.day = df.in[, 'Max_mm_day' ]

  df = data.frame( Time = as.POSIXct(time.lt, origin='1970-01-01', tz = 'EST'),
                   PET = PET.mm.day )

  #-------------------------------------------------------
  if( is.null( dev.list() ) ) { newPlot() }
  plot( df $ Time, df $ PET, type = 'l', ylab = 'mm/day' )

  save( df, file = paste( path, out, sep = '' ) )
  
  invisible( df )
}
