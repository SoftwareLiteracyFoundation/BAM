
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

    data.max = max( df[ , station ], na.rm = TRUE )
    
    print( paste( station, data.max ) )

    i.na = which( is.na( df[ , station ] ) )

    yday.list = station.list[[ station ]]
    
    for ( i in i.na ) {
      yday = date.lt[ i ] $ yday

      if ( yday == 0 ) { yday = 1 }
    
      # Choose randomly from the available data for this yearday
      value = mean( sample( yday.list[[ yday ]],
                            size = 20, replace = TRUE ) )
      
      # Assign to the missing data
      if ( value < 0 || value > data.max ) {
        value = df[ (i-1), station ]
      }
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
PlotSalinityData = function(
  path    = '../data/Salinity/',
  file    = 'DailySalinity_1999-9-1_2015-12-8.Rdata',
  overlay = FALSE,
  ylim    = c( 0, 60 ) )
{

  df = get( load( paste( path, file, sep = '' ) ) )
  df.col.names = names( df )
  N.plots      = ncol( df ) - 1

  N.plot.rows.1 = round( N.plots / 2, 0 )
  N.plot.rows.2 = N.plots - N.plot.rows.1

  if ( length( dev.list() ) < 1 ) {
    if ( overlay ) {
      dev1 = newPlot()
    }
    else {
      dev1 = newPlot( mfrow = c( N.plot.rows.1, 1 ) )
    }
  }
  if ( length( dev.list() ) < 2 ) {
    if ( overlay ) {
      dev2 = newPlot()
    }
    else {
      dev2 = newPlot( mfrow = c( N.plot.rows.2, 1 ) )
    }
  }
  else {
    dev1 = dev.list()[ 1 ]
    dev2 = dev.list()[ 2 ]
  }

  dev.set( dev1 )
  par( mar = c(1.5, 3, 1, 1) )
  row = 1
  plot.colors = rainbow( N.plots + 1 )
  
  for ( col in 2 : (N.plot.rows.1 + 1) ) {
    if ( overlay ) {
      if ( col == 2 ) {
        plot( df $ Date, df[,col], type = 'l', ylim = ylim,
              ylab = '(ppt)', col = plot.colors[ col ], lwd = 2 )
      }
      else {
        lines( df $ Date, df[,col], col = plot.colors[ col ], lwd = 2 )
      }
    }
    else {
      plot( df $ Date, df[,col], type = 'l', ylim = ylim,
            ylab = '(ppt)', col = 'red', lwd = 2 )
      par( mfg = c( row, 1 ) )
      row = row + 1
      mtext( df.col.names[ col ], line = -1.5, cex = 1.3 )
    }
  }
  if ( overlay ) {
    legend( 'top', bty = 'n', legend = df.col.names[ 2 : (N.plot.rows.1 + 1) ],
             lwd = 5, col = plot.colors[2 : (N.plot.rows.1 + 1)], cex = 1.2 )
  }
  
  dev.set( dev2 )
  par( mar = c(1.5, 3, 1, 1) )
  row = 1
  
  for ( col in ( N.plot.rows.1 + 2 ) : ncol( df ) ) {
    if ( overlay ) {
      if ( col == N.plot.rows.1 + 2 ) {
        plot( df $ Date, df[,col], type = 'l', ylim = ylim,
              ylab = '(ppt)', col = plot.colors[ col ], lwd = 2 )
      }
      else {
        lines( df $ Date, df[,col], col = plot.colors[ col ], lwd = 2 )
      }
    }
    else {
      plot( df $ Date, df[,col], type = 'l', ylim = ylim,
            ylab = '(ppt)', col = 'red', lwd = 2 )
      par( mfg = c( row, 1 ) )
      row = row + 1
      mtext( df.col.names[ col ], line = -1.5, cex = 1.3 )
    }
  }
  if ( overlay ) {
    legend( 'top', bty = 'n',
            legend = df.col.names[ (N.plot.rows.1 + 2) : ncol(df) ],
            lwd = 5, col = plot.colors[(N.plot.rows.1 + 2) : ncol(df)],
            cex = 1.2 )
  }
}


#-----------------------------------------------------------------------
#
#-----------------------------------------------------------------------
ReadCSV = function( path = '../data/Salinity/',
                    file = 'DailySalinity_1999-9-1_2015-12-8.csv',
                    skip = 0 ) {
  
  df = read.csv( paste( path, file, sep = '' ),
                 na.strings = 'null', header = TRUE, as.is = TRUE,
                 skip = skip )
                 #colClasses = c('character',
                 #               'numeric','numeric','numeric','numeric',
                 #               'numeric','numeric','numeric','numeric',
                 #               'numeric','numeric','numeric','numeric',
                 #               'numeric','numeric','numeric','numeric',
                 #               'numeric','numeric','numeric','numeric' ) )
  
  Dates = as.POSIXct( strptime( df $ Date, '%Y-%m-%d', tz = 'EST' ),
                      origin = '1970-01-01' )

  df $ Date = Dates

  save( df, file = paste( path, sub( '.csv', '.Rdata', file ), sep = '' ) )

  invisible( df )
}
