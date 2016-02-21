

#-----------------------------------------------------------------------
#
#-----------------------------------------------------------------------
CreateSalinityData = function(
  path = '../data/Salinity/',
  file = 'DailySalinity_1999-9-1_2015-12-8.Rdata',
  out  = 'DailySalinityFilled_1999-9-1_2015-12-8.Rdata' )
{

  df = get( load( paste( path, file, sep = '' ) ) )
  # "Date" "BA"   "BK"   "BN"   "BS"   "DK"   "GB"   "HC"   "JK"   "LB"  
  # "LM"   "LR"   "LS"   "MK"   "PK"   "TC"   "TR"   "WB"   "MB"   "MD"  
  # "TP"    

  stations = names( df )[ 2 : ncol( df ) ]

  date.lt = as.POSIXlt( df $ Date )
  
  # brute force... create yearday samples of available data at each site
  days         = seq( 1, 365 )
  station.list = list()
  
  for ( station in stations ) {
    yday.list = list()
    
    for ( day in days ) {
      
      i.yday    = which( date.lt $ yday == day )
      yday.data = df[ i.yday, station ]
      i.na      = which( is.na( yday.data ) )
      yday.data = yday.data[ -i.na ]
      
      yday.list[[ day ]] = yday.data
    }
    
    station.list[[ station ]] = yday.list
  }

  print( paste( length( yday.list ), 'data sets created for',
                length( station.list ), 'stations.' ) )

  #return( data.yday )

  # For each station sample for missing data
  for ( station in stations ) {

    print( station )
    
    i.na = which( is.na( df[ , station ] ) )

    yday.list = station.list[[ station ]]
    
    for ( i in i.na ) {
      yday = date.lt[ i ] $ yday

      if ( yday == 0 ) { yday = 1 }
    
      # Choose randomly from the available data for this yearday
      value = mean( sample( yday.list[[ yday ]],
                            size = 20, replace = TRUE ) )
      
      # Assing to the missing data
      df[ i, station ] = value
    }
  }
  
  save( df, file = paste( path, out, sep = '' ) )
  
  invisible( df )
}

#-----------------------------------------------------------------------
# PlotSalinityData(file='DailySalinityFilled_1999-9-1_2015-12-8.Rdata')
# PlotSalinityData(file='DailySalinity_1999-9-1_2015-12-8.Rdata',overlay=TRUE)
#-----------------------------------------------------------------------
PlotSalinityData = function( path = '../data/Salinity/',
                         file = 'DailySalinity_1999-9-1_2015-12-8.Rdata',
                         overlay = FALSE,
                         ylim = c( 0, 60 ) )
{

  df = get( load( paste( path, file, sep = '' ) ) )
  df.cols = names( df )
  # "Date" "BA"   "BK"   "BN"   "BS"   "DK"   "GB"   "HC"   "JK"   "LB"  
  # "LM"   "LR"   "LS"   "MK"   "PK"   "TC"   "TR"   "WB"   "MB"   "MD"  
  # "TP"  

  cols.1 = c( 'MK', 'JK', 'BK', 'GB', 'LR', 'PK', 'WB', 'BA', 'TP', 'MB' )
  cols.2 = c( 'TR', 'LM', 'BN', 'TC', 'DK', 'BS', 'LB', 'HC', 'LS', 'MD' )

  if ( length( dev.list() ) < 2 ) {
    dev1 = newPlot( mfrow = c( length( cols.1 ), 1 ) )
    dev2 = newPlot( mfrow = c( length( cols.2 ), 1 ) )
  }
  else {
    dev1 = dev.list()[ 1 ]
    dev2 = dev.list()[ 2 ]
  }

  dev.set( dev1 )
  par( mar = c(1, 3, 1, 1) )
  row = 1
  
  for ( col in cols.1 ) {
    if ( ! overlay ) {
      plot( df $ Date, df[,col], type = 'l', ylim = ylim,
            ylab = '(ppt)', col = 'red' )
      mtext( substr( col, 1, 2 ), line = -1.5, cex = 1.3 )
    }
    else {
      par( mfg = c( row, 1 ) )
      lines( df $ Date, df[,col], col = 'black' )
      row = row + 1
    }
  }
  
  dev.set( dev2 )
  par( mar = c(1, 3, 1, 1) )
  row = 1
  
  for ( col in cols.2 ) {
    if ( ! overlay ) {
      plot( df $ Date, df[,col], type = 'l', ylim = ylim,
            ylab = '(ppt)', col = 'red' )
      mtext( substr( col, 1, 2 ), line = -1.5, cex = 1.3 )
    }
    else {
      par( mfg = c( row, 1 ) )
      lines( df $ Date, df[,col], col = 'black' )
      row = row + 1
    }
  }
}


#-----------------------------------------------------------------------
#
#-----------------------------------------------------------------------
ReadCSV = function( path = '../data/Salinity/',
                    file = 'DailySalinity_1999-9-1_2015-12-8.csv' ) {
  
  df = read.csv( paste( path, file, sep = '' ),
                 na.strings = 'null', header = TRUE,
                 colClasses = c('character',
                                'numeric','numeric','numeric','numeric',
                                'numeric','numeric','numeric','numeric',
                                'numeric','numeric','numeric','numeric',
                                'numeric','numeric','numeric','numeric',
                                'numeric','numeric','numeric','numeric' ) )
  
  Dates = as.POSIXct( strptime( df $ Date, '%Y-%m-%d', tz = 'EST' ),
                      origin = '1970-01-01' )

  df $ Date = Dates

  save( df, file = paste( path, sub( '.csv', '.Rdata', file ), sep = '' ) )

  invisible( df )
}
