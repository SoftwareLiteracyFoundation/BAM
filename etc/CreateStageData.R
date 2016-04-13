

#-----------------------------------------------------------------------
#
#-----------------------------------------------------------------------
CreateStageData = function(
  path     = '../data/Stage/',
  file     = 'DailyStage_1999-9-1_2016-3-1.hydro.csv',
  out.file = 'DailyStage_1999-9-1_2016-3-1.csv' )
{

  # "Date" "BA"   "BK"   "BN"   "BS"   "DK"   "GB"   "HC"   "JK"   "LB"  
  # "LM"   "LR"   "LS"   "MK"   "PK"   "TC"   "TR"   "WB"   "MB"   "MD"   
  df = read.csv( paste( path, file, sep = '' ),
                 na.strings = 'null', header = TRUE, as.is = TRUE )
  
  Date.lt = strptime( df $ Date, '%Y-%m-%d' )
  Date    = as.POSIXct( Date.lt , origin = '1970-01-01' )

  df $ Date = Date

  # De-mean each station
  for ( col in 2 : ncol( df ) ) {
    df[,col] = df[,col] - mean( df[,col], na.rm = TRUE )
  }

  # Convert from feet to meters
  for ( col in 2 : ncol( df ) ) {
    df[,col] = round( df[,col] * 0.3048, 3 )
  }

  PlotStageData( df )
  
  write.csv( df, file = paste( path, out.file, sep = '' ),
             quote = FALSE, row.names = FALSE )
  
  save( df, file = paste( path, sub( '.csv', '.Rdata', out.file ), sep = '' ) )

  invisible( df )
}

#-----------------------------------------------------------------------
#
#-----------------------------------------------------------------------
PlotStageData = function( df   = NULL,
                          path = '../data/Stage/',
                          file = 'DailyStage_1999-9-1_2016-3-1.Rdata',
                          ylim = c( -0.5, 0.5 ) )
{

  if ( is.null( df ) ) {
    df = get( load( paste( path, file, sep = '' ) ) )
  }
  
  if ( length( dev.list() ) == 0 ) {
    newPlot()
  }
  
  plot.colors = rainbow( ncol( df ) )

  plot( df $ Date, df[,1], type = 'l', ylim = ylim,
        ylab = 'Stage (m)', col = plot.colors[1] )

  for ( i in 2 : ncol( df ) ) {
    lines( df $ Date, df[,i], col = plot.colors[i] )
  }

  legend( 'topleft', legend = names( df )[2:ncol(df)],
          lwd = 5, col = plot.colors, bty = 'n' )
}
