#----------------------------------------------------------------------------
#
#----------------------------------------------------------------------------
MSL = function(
    msl.file     = 'MonthlyMean_1999-9_2015-12.csv',
    ylim = NULL,
    xlim = NULL
    ) {

  df  = read.csv( msl.file, header = TRUE, as.is = TRUE )

  Date  = strptime( df  $ Date, '%Y-%m-%d' )

  if ( is.null( dev.list() ) ) {
    newPlot()
  }

  plot( Date, df $ Anomaly_m_2008_2015_MSL, type = 'l', lwd = 3,
        xlab = 'Year', ylab = 'Mean Sea Level Anomaly (m)',
        ylim = ylim, xlim = xlim, cex.axis = 1.3, cex.lab = 1.3 )

  abline( h = 0, col = 'brown' )
}

#----------------------------------------------------------------------------
#
#----------------------------------------------------------------------------
Anomaly.MSL = function(
    msl.file     = 'MonthlyMean_1999-9_2015-12.csv',
    anomaly.file = 'VacaKey_AverageSeasonalCycle.csv',
    MSL.NAVD     = -0.148,
    ylim = NULL,
    xlim = NULL
    ) {

  df  = read.csv( msl.file,     header = TRUE, as.is = TRUE )
  df2 = read.csv( anomaly.file, header = TRUE, as.is = TRUE )

  Date  = strptime( df  $ Date, '%Y-%m-%d' )
  Date2 = strptime( df2 $ Date, '%Y-%m-%d' )

  stations = names( df )[2:6]

  if ( is.null( dev.list() ) ) {
    newPlot()
  }

  plot( Date, df $ MeanMSL.SC_NAVD - MSL.NAVD, type = 'l', lwd = 2,
        xlab = 'Year', ylab = 'Mean Sea Level Anomaly (m)',
        ylim = ylim, xlim = xlim, cex.axis = 1.3, cex.lab = 1.3 )

  lines( Date2, df2 $ Anomaly_m, lwd = 2, col = 'red'  )

  legend( 'topleft',
          legend = c( '3 Station Mean + 14.8 cm', 'Vaca Key NOAA Anomaly' ),
          lwd = 5, col = c( 'black', 'red' ),
          cex = 1.4, bty = 'n' )
}

#----------------------------------------------------------------------------
#
#----------------------------------------------------------------------------
Station.MSL = function(
    msl.file = 'MonthlyMean_1999-9_2015-12.csv',
    ylim = NULL,
    xlim = NULL
    ) {

  df  = read.csv( msl.file, header = TRUE, as.is = TRUE )

  Date  = strptime( df $ Date, '%Y-%m-%d' )

  stations = names( df )[2:6]

  print( stations )

  # RMS deviation among 3 stations
  delta.1.2 = df $ VirginiaKeyMSL.SC_NAVD - df $ VacaKeyMSL.SC_NAVD
  delta.2.3 = df $ VirginiaKeyMSL.SC_NAVD - df $ KeyWestMSL.SC_NAVD
  delta.1.3 = df $ VacaKeyMSL.SC_NAVD     - df $ KeyWestMSL.SC_NAVD
  delta.mean = colMeans( rbind( delta.1.2, delta.2.3, delta.1.3 ) )
  RMS = sqrt( var( delta.mean ) )
  print( paste( 'RMS deviation', round( RMS, 3 ), '(m)' ) )

  if ( is.null( dev.list() ) ) {
    newPlot()
  }

  plot( Date, df $ MeanMSL.SC_NAVD, type = 'l', lwd = 4, col = 'cyan',
        xlab = 'Year', ylab = 'Mean Sea Level NAVD (m)',
        ylim = ylim, xlim = xlim, cex.axis = 1.3, cex.lab = 1.3 )

  lines( Date, df $ VirginiaKeyMSL.SC_NAVD, lwd = 2, col = 'red'  )
  lines( Date, df $ VacaKeyMSL.SC_NAVD,     lwd = 2, col = 'blue' )
  lines( Date, df $ KeyWestMSL.SC_NAVD,     lwd = 2, col = 'darkgreen' )

  legend( 'topleft',
          legend = c( '3 Station Mean', 'Virginia Key',
                      'Vaca Key', 'Key West' ),
          lwd = 5, col = c( 'cyan', 'red', 'blue', 'darkgreen' ),
          cex = 1.4, bty = 'n' )
}
