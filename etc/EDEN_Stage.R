

#--------------------------------------------------------------------
# 
#--------------------------------------------------------------------
CreateStageCSV = function(
    file    = 'EDEN_Stage.txt',  # EDEN water surface (m) NAVD88
    csvFile = 'EDEN_Stage_OffsetMSL.csv',
    ylim    = c( -0.7, 0.6 ),
    start   = '1999-9-1',
    end     = '2015-12-31',
    MSL     = -0.148,   # MSL = -14.8 cm NAVD
    offset  = TRUE,
    cols    = c('Date', 'S22', 'S21', 'S20', 'S19', 'S18', 'S17', 'S16', 'S15')

) {

  start.POSXIct = as.POSIXct( strptime( start, '%Y-%m-%d', tz = 'EDT' ),
                              origin = '1970-01-01' )
  end.POSXIct   = as.POSIXct( strptime( end, '%Y-%m-%d', tz = 'EDT' ),
                              origin = '1970-01-01' )

  xlim = c( start.POSXIct, end.POSXIct )

  # Read and MSL offset the EDEN data
  df.in = ReadStage( file = file, ylim = ylim, MSL = MSL, offset = offset )

  # Remove unused columns
  df = df.in[,cols]

  # Remove unused dates
  i.rm = which( df $ Date < start.POSXIct )
  df = df[-i.rm,]

  write.csv( df, file = csvFile, quote = FALSE, row.names = FALSE )

  #-----------------------------------------------------------------------
  if ( is.null( dev.list() ) ) { newPlot() }

  colors = rainbow( ncol( df ) )

  plot( df $ Date, df[,2], type = 'l', col = colors[2],
        xlab = 'Date', xlim = xlim,
        ylab = 'Stage (m) NAVD', ylim = ylim )

  for ( i in 3 : ncol( df ) ) {
    lines( df $ Date, df[,i], col = colors[i] )
  }

  abline( h = MSL, lwd = 2 )
  abline( h = 0, lwd = 1 )

  legend( 'top', ncol = 6, legend = names( df )[ 2 : ncol(df) ],
          col = colors[ 2 : ncol(df) ], lwd = 4, cex = 0.8 )

  invisible( df )
}

#--------------------------------------------------------------------
# 
#--------------------------------------------------------------------
ReadStage = function( file   = 'EDEN_Stage.txt',
                                # EDEN water surface (m) NAVD88
                      ylim   = c( -0.6, 0.5 ),
                      MSL    = -0.148,  # MSL = -14.8 cm NAVD
                      offset = TRUE,
                      plot   = FALSE
) {

  col.names = c( 'Date', paste( 'S', as.character( seq( 1, 22 ) ), sep = ''))
  
  df = read.table( file, skip = 5, stringsAsFactors = FALSE )

  if ( offset ) {
    # Shift the data from NAVD to MSL anomaly
    for ( i in 2 : ncol( df ) ) {
      df[,i] = round( df[,i] - MSL, 3 )
    }
  } 

  names( df ) = col.names

  Dates = as.POSIXct( strptime( df $ Date, '%Y/%m/%d', tz = 'EDT' ),
                      origin = '1970-01-01' )

  df $ Date = Dates

  if ( plot ) {
    if ( is.null( dev.list() ) ) { newPlot() }

    colors = rainbow( ncol( df ) )
    
    plot( df $ Date, df[,2], type = 'l', col = colors[2], xlab = 'Date',
          ylab = 'Stage (m) NAVD', ylim = ylim )

    for ( i in 3 : ncol( df ) ) {
      lines( df $ Date, df[,i], col = colors[i] )
    }

    colors = rainbow( ncol( df ) )
    legend( 'top', ncol = 6, legend = names( df )[ 2 : ncol(df) ],
            col = colors[ 2 : ncol(df) ], lwd = 4, cex = 0.8 )
  
    abline( h = MSL, lwd = 2 )
    abline( h = 0,   lwd = 1 )
  }
  
  invisible( df )
}

#--------------------------------------------------------------------
# 
#--------------------------------------------------------------------
PlotStage = function(
    file = 'EDEN_Stage_OffsetMSL.Rdata',
    ylim = c( -0.7, 0.6 ),
    start = '1999-7-1',
    end   = '2015-12-08',
    MSL   = -0.148   # MSL = -14.8 cm NAVD
) {

  df = get( load( file ) )

  start.POSXIct = as.POSIXct( strptime( start, '%Y-%m-%d', tz = 'EDT' ),
                              origin = '1970-01-01' )
  end.POSXIct   = as.POSIXct( strptime( end, '%Y-%m-%d', tz = 'EDT' ),
                              origin = '1970-01-01' )

  xlim = c( start.POSXIct, end.POSXIct )

  if ( is.null( dev.list() ) ) { newPlot() }

  colors = rainbow( ncol( df ) )

  plot( df $ Date, df[,2], type = 'l', col = colors[2],
        xlab = 'Date', xlim = xlim,
        ylab = 'Stage (m) NAVD', ylim = ylim )

  for ( i in 3 : ncol( df ) ) {
    lines( df $ Date, df[,i], col = colors[i] )
  }

  abline( h = MSL, lwd = 2 )
  abline( h = 0, lwd = 1 )

  legend( 'top', ncol = 6, legend = names( df )[ 2 : ncol(df) ],
          col = colors[ 2 : ncol(df) ], lwd = 4, cex = 0.8 )

  invisible( df )
}
