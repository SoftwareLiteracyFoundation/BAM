
#-----------------------------------------------------------------
#
#-----------------------------------------------------------------
CreateETData = function( path = '../data/ET/',
                         file = 'PET.Rdata',
                         out  = 'PET_1999-9-1_2015-12-8.Rdata' )
{

  # Fill missing data after April 2015 to December 12 2015
  df = get( load( paste( path, file, sep = '' ) ) )
  df.in = df
  
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

  # sample the distribution for missing data
  i.na = which( is.na( df $ PET ) )
    
  for ( i in i.na ) {
    yday = date.lt[ i ] $ yday

    if ( yday == 0 ) { yday = 1 }
    
    # Choose randomly from the available data for this yearday
    value = mean( sample( data.yday[[ yday ]], size = 2, replace = TRUE ) )
    #value = sample( data.yday[[ yday ]], size = 1 )
    # Assing to the missing data
    df[ i, 'PET' ] = value
  }

  if ( length( dev.list() ) < 1 ) { newPlot() }
  plot( df $ Time, df $ PET, type = 'l', col = 'red', ylab = 'mm/day' )
  lines( df.in $ Time, df.in $ PET )
  
  save( df, file = paste( path, out, sep = '' ) )
  write.csv( df, file = paste( path, sub( '.Rdata', '.csv', out ), sep = '' ),
             row.names = FALSE )
  
  invisible( df )
}

#-----------------------------------------------------------------
#
#-----------------------------------------------------------------
ReadETData = function( path = '../data/ET/',
                       file = 'PET_Dade_sfwmd.csv',
                       out  = 'PET.Rdata' )
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

  newPlot()
  plot( df $ Time, df $ PET, type = 'l', ylab = 'mm/day' )

  save( df, file = paste( path, out, sep = '' ) )
  
  invisible( df )
}
