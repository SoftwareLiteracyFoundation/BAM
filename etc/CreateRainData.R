

#-----------------------------------------------------------------------
#
#-----------------------------------------------------------------------
CreateRainData = function( path = '../data/Rain/',
                           file = 'DailyRain_cm_1999-9-1_2015-12-8.Rdata',
                           out  = 'DailyRainFilled_cm_1999-9-1_2015-12-8.Rdata' )
{

  df = get( load( paste( path, file, sep = '' ) ) )
  
  # date BK_cm_day BA_cm_day BN_cm_day BS_cm_day DK_cm_day GB_cm_day
  #      HC_cm_day JK_cm_day LB_cm_day LM_cm_day LR_cm_day LS_cm_day
  #      MK_cm_day PK_cm_day TC_cm_day TR_cm_day WB_cm_day

  stations = names( df )[ 2 : ncol( df ) ]

  date.lt = as.POSIXlt( df $ date )
  
  # brute force... create yearday samples of available data
  days      = seq( 1, 365 )
  data.yday = list()
  
  for ( day in days ) {
    i.yday = which( date.lt $ yday == day )

    all.yday.data = c()
    
    for ( station in stations ) {
      yday.data = df[ i.yday, station ]
      i.na      = which( is.na( yday.data ) )
      yday.data = yday.data[ -i.na ]

      all.yday.data = c( all.yday.data, yday.data )
    }
    
    data.yday[[ day ]] = all.yday.data
  }

  print( paste( length( data.yday ), 'data sets created.' ) )

  #return( data.yday )

  # For each station sample the distribution for missing data
  for ( station in stations ) {

    print( station )
    
    i.na = which( is.na( df[ , station ] ) )
    
    for ( i in i.na ) {
      yday = date.lt[ i ] $ yday

      if ( yday == 0 ) { yday = 1 }
    
      # Choose randomly from the available data for this yearday
      value = max( sample( data.yday[[ yday ]], size = 2, replace = TRUE ) )
      # Assing to the missing data
      df[ i, station ] = value
    }
  }
  
  save( df, file = paste( path, out, sep = '' ) )
  
  invisible( df )
}

#-----------------------------------------------------------------------
#
#-----------------------------------------------------------------------
PlotRainData = function( path = '../data/Rain/',
                         file = 'DailyRain_cm_1999-9-1_2015-12-8.Rdata',
                         overlay = FALSE )
{

  df = get( load( paste( path, file, sep = '' ) ) )
  df.cols = names( df )
  # date BK_cm_day BA_cm_day BN_cm_day BS_cm_day DK_cm_day GB_cm_day
  #      HC_cm_day JK_cm_day LB_cm_day LM_cm_day LR_cm_day LS_cm_day
  #      MK_cm_day PK_cm_day TC_cm_day TR_cm_day WB_cm_day


  west.cols = c( 'MK', 'JK', 'BK', 'GB', 'LR', 'PK', 'WB', 'BA' )
  east.cols = c( 'TR', 'LM', 'BN', 'TC', 'DK', 'BS', 'LB', 'HC', 'LS' )

  if ( length( dev.list() ) < 2 ) {
    dev1 = newPlot( mfrow = c( length( west.cols ), 1 ) )
    dev2 = newPlot( mfrow = c( length( east.cols ), 1 ) )
  }
  else {
    dev1 = dev.list()[ 1 ]
    dev2 = dev.list()[ 2 ]
  }

  dev.set( dev1 )
  par( mar = c(1, 3, 1, 1) )
  row = 1
  
  for ( col in paste( west.cols, '_cm_day', sep = '' ) ) {
    if ( ! overlay ) {
      plot( df $ date, df[,col], type = 'l', ylab = '(cm/day)', col = 'red' )
      mtext( substr( col, 1, 2 ), line = -1.5, cex = 1.3 )
    }
    else {
      par( mfg = c( row, 1 ) )
      lines( df $ date, df[,col], col = 'black' )
      row = row + 1
    }
  }
  
  dev.set( dev2 )
  par( mar = c(1, 3, 1, 1) )
  row = 1
  
  for ( col in paste( east.cols, '_cm_day', sep = '' ) ) {
    if ( ! overlay ) {
      plot( df $ date, df[,col], type = 'l', ylab = '(cm/day)', col = 'red' )
      mtext( substr( col, 1, 2 ), line = -1.5, cex = 1.3 )
    }
    else {
      par( mfg = c( row, 1 ) )
      lines( df $ date, df[,col], col = 'black' )
      row = row + 1
    }
  }
}


#-----------------------------------------------------------------------
#
#-----------------------------------------------------------------------
ReadCSV = function( path = '../data/Rain/',
                    file = 'DailyRain_cm_1999-9-1_2015-12-8.csv' ) {
  
  df = read.csv( paste( path, file, sep = '' ),
                 na.strings='null', header=TRUE,
                 colClasses=c('character','numeric','numeric','numeric',
                              'numeric','numeric','numeric','numeric',
                              'numeric','numeric','numeric','numeric',
                              'numeric','numeric','numeric','numeric',
                              'numeric','numeric') )
  
  Dates = as.POSIXct( strptime( df $ date, '%Y-%m-%d', tz = 'EST' ),
                      origin = '1970-01-01' )

  df $ date = Dates

  save( df, file = 'DailyRain_cm_1999-9-1_2015-12-8.Rdata' )

  invisible( df )
}
