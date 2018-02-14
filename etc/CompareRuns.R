
#-------------------------------------------------------------
# 
#  
#-------------------------------------------------------------
temp = function() {
  Compare( basin = 'Rankin Lake',         gauge = 'BK' )
  Compare( basin = 'Terrapin Bay',        gauge = 'BK' )
  Compare( basin = 'North Whipray',       gauge = 'BK' )
  Compare( basin = 'Little Madeira Bay',  gauge = 'LM' )
  Compare( basin = 'Long Sound',          gauge = 'LS' )
  Compare( basin = 'Manatee Bay',         gauge = 'MB' )
}

#-------------------------------------------------------------
# 
#  
#-------------------------------------------------------------
CompareRunsRMS = function(
  data.field = 'Salinity..ppt.',
  bam.path   = '/home/jpark/NPS/PyBAM',
  data.path  = 'data/out/ET_Amplify.ea20',
  disk.path  = 'data/out/v1.2_Sep-1-1999_Dec-31-2016',
  basins     = c( 'Snake Bight',   'Rankin Lake',  'Rankin Bight',
                  'North Whipray', 'Terrapin Bay', 'Madeira Bay',
                  'Little Madeira Bay', 'Joe Bay', 'Eagle Key', 
                  'Long Sound',    'Manatee Bay',  'Barnes Sound',
                  'Duck Key',      'Twin Keys',    'Porpoise Lake',
                  'Little Blackwater Sound', 'Butternut Key', 'Johnson Key' ),
  gauges     = c( 'BK', 'BK', 'GB',
                  'BK', 'BK', 'LM',
                  'LM', 'TC', 'LM',
                  'LS', 'MB', 'MD',
                  'DK', 'LR', 'BA',
                  'LB', 'BN', 'JK' ),
  gauge.file = 'data/Salinity/DailySalinityFilled_1999-9-1_2016-12-31.csv',
  start      = '1999-9-1',
  end        = '2016-12-31'
) {

  
  data.to.gauge.RMS = numeric( length(basins) )
  disk.to.gauge.RMS = numeric( length(basins) )
  
  for ( i in 1:length(basins) ) {
    print( paste( basins[i], gauges[i], sep = ' : ' ) )
    
    RMS = CompareRuns(
      data.field = data.field,
      bam.path   = bam.path ,
      data.path  = data.path,
      disk.path  = disk.path,
      basin      = basins[i],
      gauge      = gauges[i],
      gauge.file = gauge.file,
      start      = start,
      end        = end,
      plot       = FALSE
    )

    data.to.gauge.RMS[i] = RMS ["data.to.gauge.RMS"]
    disk.to.gauge.RMS[i] = RMS ["disk.to.gauge.RMS"]
  }

  #-------------------------------------------------------------
  if ( is.null( dev.list() ) ) {
    newPlot( mar = c(7.5, 4, 1, 1) )
  }

  plot( data.to.gauge.RMS, pch = 15, cex = 1.5, col = 'red',
        ylim = range( c( data.to.gauge.RMS, disk.to.gauge.RMS ) ),
        xaxt = 'n', xlab = '', ylab = paste( 'RMS Error', data.field) )

  lines( data.to.gauge.RMS, lwd = 2, col = 'red' )

  points( disk.to.gauge.RMS, pch = 17, cex = 1.5, col = 'blue' )

  lines( disk.to.gauge.RMS, lwd = 2, col = 'blue' )

  axis( side = 1, labels = basins, cex.axis = 1,
        at = seq(1,length(basins)), las = 2 )

  mtext( gauges, side = 1, at = seq(1,length(basins)), line = -1.8, cex = 1.3 )

  legend( 'topleft', col = c('red', 'blue'),
          cex = 1.5, bty = 'n', pch = c( 15, 17 ), 
          legend = c(data.path, disk.path) )

  
  #-------------------------------------------------------------
  df = data.frame( Basin = basins, Gauge = gauges,
                   Data.RMS = data.to.gauge.RMS,
                   Disk.RMS = disk.to.gauge.RMS )

  invisible( df )
}

#-------------------------------------------------------------
# Compare a BAM output (data.path, basin) with another BAM
# output (disk.path) and with a BAM gauge data (gauge.file)
#  
#-------------------------------------------------------------
CompareRuns = function(
  data.field = 'Salinity..ppt.',
  bam.path   = '/home/jpark/NPS/PyBAM',
  data.path  = 'data/out/ET_Amplify.ea20', # './ET_Amp',
  disk.path  = 'data/out/v1.2_Sep-1-1999_Dec-31-2016',
  basin      = 'Little Madeira Bay',
  gauge      = 'LM',
  gauge.file = 'data/Salinity/DailySalinityFilled_1999-9-1_2016-12-31.csv',
  start      = '1999-9-1',
  end        = '2016-12-31',
  plot       = TRUE
  ){

  start.time = as.POSIXct( paste( start, ' 00:00:00', sep = '' ) )
  end.time   = as.POSIXct( paste( end,   ' 00:00:00', sep = '' ) )

  # Read data from run
  df.data = read.csv( paste( bam.path, '/', data.path, '/',
                             basin, '.csv', sep = '' ),
                      header = TRUE, as.is = TRUE, strip.white = TRUE )

  data.time = as.POSIXct( df.data $ Time )

  data.start.i = which( data.time == start.time )
  data.end.i   = which( data.time == end.time   )

  # Read data from other run (disk data)
  df.disk = read.csv( paste( bam.path, '/', disk.path, '/',
                             basin, '.csv', sep = '' ),
                      header = TRUE, as.is = TRUE, strip.white = TRUE )

  disk.time = as.POSIXct( df.disk $ Time )

  disk.start.i = which( disk.time == start.time )
  disk.end.i   = which( disk.time == end.time   )

  # Read gauge data
  if ( ! is.null( gauge ) ) {
    df.gauge = read.csv( paste( bam.path, gauge.file, sep = '/' ),
                         header = TRUE, as.is = TRUE, strip.white = TRUE )

    gauge.date = as.Date( df.gauge $ Date )
    
    gauge.start.i = which( gauge.date == as.Date( start.time ) )
    gauge.end.i   = which( gauge.date == as.Date( end.time   ) )
    
    gauge.time = as.POSIXct( gauge.date[ gauge.start.i : gauge.end.i ] )
  }

  #-------------------------------------------------------------
  # Difference statistics
  #-------------------------------------------------------------
  #data.to.disk.diff = df.data[ data.start.i : data.end.i, data.field ] - 
  #                    df.disk[ disk.start.i : disk.end.i, data.field ]

  # BAM data are arbitrary timestep, but gauge data are Daily
  gauge.time.in.data.i = match( gauge.time,
                                data.time[ data.start.i : data.end.i ] )
  
  gauge.time.in.disk.i = match( gauge.time,
                                disk.time[ disk.start.i : disk.end.i ] )
                              
  data.to.gauge.diff = df.data[ gauge.time.in.data.i, data.field ] -
                       df.gauge[ gauge.start.i : gauge.end.i, gauge ]

  disk.to.gauge.diff = df.disk[ gauge.time.in.disk.i, data.field] -
                       df.gauge[ gauge.start.i : gauge.end.i, gauge ]

  #data.to.disk.RMS  = sqrt( mean( data.to.disk.diff^2  ) )
  data.to.gauge.RMS = sqrt( mean( data.to.gauge.diff^2, na.rm = TRUE ) )
  disk.to.gauge.RMS = sqrt( mean( disk.to.gauge.diff^2, na.rm = TRUE ) )
 
  #-------------------------------------------------------------
  if ( plot ) {
    if ( is.null( dev.list() ) ) { newPlot() }

    plot( data.time[ data.start.i : data.end.i ],
          df.data[ data.start.i : data.end.i, data.field ],
          type = 'l', lwd = 2, col = 'red', xlab = '', ylab = 'Salinity (ppt)')
    
    lines( disk.time[ disk.start.i : disk.end.i ],
           df.disk[ disk.start.i : disk.end.i, data.field ],
           lwd = 2, col = 'darkgreen' )
    
    if ( ! is.null( gauge ) ) {
      lines( gauge.time,
             df.gauge[ gauge.start.i : gauge.end.i, gauge ],
             lwd = 2, col = 'blue' )
    }
    
    mtext( side = 3, line = -1.8, paste( '  ', basin, ":", gauge ),
           adj = 0, cex = 1.8 )
    mtext( side = 3, line = -3.5, paste( '  ', start, ":", end ),
           adj = 0, cex = 1.8 )
    
    legend( 'bottomleft',
            legend = c( paste( data.path, round( data.to.gauge.RMS, 2 ) ),
                       paste( disk.path, round( disk.to.gauge.RMS, 2 ) ),
                       paste( "Gauge :", gauge ) ),
            lwd = 5, col = c('red', 'darkgreen', 'blue'),
            bty = 'n', cex = 1.8 )
  }

  invisible( c( data.to.gauge.RMS = data.to.gauge.RMS, 
                disk.to.gauge.RMS = disk.to.gauge.RMS ) )
}

  
