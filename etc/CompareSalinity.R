
#------------------------------------------------------------------------
#
#------------------------------------------------------------------------
CompareSalinities = function(
    delay     = 2,
    station.i = NULL,
    createPNG = FALSE
) {
  
  starts = c( rep( '2000-5-1',  21 ),
              rep( '2001-5-1',  21 ),
              rep( '2002-5-1',  21 ) )
  ends   = c( rep( '2000-11-1', 21 ),
              rep( '2001-11-1', 21 ),
              rep( '2002-11-1', 21 ) )
  
  bam.paths = c( rep( '../data/out/out.May-1_Nov-1-2000/', 21 ),
                 rep( '../data/out/out.May-1_Nov-1-2001/', 21 ),
                 rep( '../data/out/out.May-1_Nov-1-2002/', 21 ) )

  gauges = rep( list(
      c( 'MD', 'TP' ), c( 'MB' ), c( 'LS' ),
      c( 'LB' ), c( 'BS' ),
      c( 'TC', 'DK' ), c( 'LM' ), c( 'LM' ),
      c( 'BA' ), c( 'PK' ),
      c( 'LR', 'PK' ), c( 'WB' ), c( 'GB', 'BK' ), c( 'LR' ), c( 'JK' ),
      c( 'MK', 'JK' ), c( 'BK' ), c( 'BN' ), c( 'DK', 'BS', 'LB' ),
      c( 'BN' ), c( 'TC', 'DK' ) ), 3 )

  bam.files = rep( c(
      'Barnes Sound', 'Manatee Bay', 'Long Sound',
      'Little Blackwater Sound', 'Blackwater Sound',
      'Joe Bay', 'Little Madeira Bay', 'Black Betsy Keys',
      'Porpoise Lake', 'Lignumvitae',
      'Twin Keys', 'Whipray', 'Rankin Lake', 'Rabbit Key', 'Johnson Key',
      'Catfish Key', 'Snake Bight', 'Butternut Key', 'Duck Key',
      'Swash Keys', 'Deer Key'
      ), 3 )
  
  salinity.ylims = list(
      c( 0, 40 ),  c( 0, 40 ),  c( 0, 40 ),  c( 0, 40 ),  c( 0, 40 ), 
      c( 0, 40 ),  c( 0, 40 ),  c( 0, 40 ),  c( 20, 60 ), c( 20, 60 ), 
      c( 20, 60 ), c( 20, 60 ), c(  0, 70 ), c( 20, 60 ), c( 20, 60 ), 
      c( 20, 60 ), c( 20, 60 ), c( 10, 50 ), c( 10, 50 ), c( 0, 40 ), 
      c( 0, 40 ),
      c( 0, 40 ),  c( 0, 40 ),  c( 0, 40 ),  c( 0, 40 ),  c( 0, 40 ), 
      c( 0, 40 ),  c( 0, 40 ),  c( 0, 40 ),  c( 20, 60 ), c( 20, 60 ), 
      c( 20, 60 ), c( 20, 60 ), c(  0, 70 ), c( 20, 60 ), c( 20, 60 ), 
      c( 20, 60 ), c( 20, 60 ), c( 10, 50 ), c( 10, 50 ), c( 0, 40 ), 
      c( 0, 40 ),
      c( 0, 40 ),  c( 0, 40 ),  c( 0, 40 ),  c( 0, 40 ),  c( 0, 40 ), 
      c( 0, 40 ),  c( 0, 40 ),  c( 0, 40 ),  c( 20, 60 ), c( 20, 60 ), 
      c( 20, 60 ), c( 20, 60 ), c(  0, 70 ), c( 20, 60 ), c( 20, 60 ), 
      c( 20, 60 ), c( 20, 60 ), c( 10, 50 ), c( 10, 50 ), c( 0, 40 ), 
      c( 0, 40 )
      )
  bam.ylims = salinity.ylims
  
  if ( is.null( station.i ) ) {
    station.i = 1 : length( bam.files )
  }

  for ( i in station.i ) {

    print( paste( bam.files[i] ) )
    
    CompareSalinity( gauges     = gauges     [ i ],
                     bam.path   = bam.paths  [ i ],
                     bam.file   = paste( bam.files[i], '.csv', sep='' ),
                     start      = starts     [ i ],
                     end        = ends       [ i ],
                     bam.ylim   = bam.ylims  [[ i ]],
                     salinity.ylim = salinity.ylims[[ i ]],
                     createPNG  = createPNG
                 )

    dev.flush()

    if ( ! is.null( delay ) ) {
      Sys.sleep( delay )
    }
  }
}

#------------------------------------------------------------------------
#
#------------------------------------------------------------------------
CompareSalinity = function(
   salinity.df   = NULL,
   salinity.path = '../data/Salinity/',
   salinity.file = 'DailySalinityFilled_1999-9-1_2015-12-8.csv',
   gauges        = list( c( 'TC', 'DK' ) ),
   bam.path      = '../data/out/out.May-1_Nov-1-2000/',
   bam.file      = 'Deer Key.csv',
   start         = '2000-5-1',
   end           = '2000-11-1',
   bam.ylim      = c(0,40),
   salinity.ylim = c(0,40),
   bam.note      = '',
   createPNG     = FALSE
) {

  start.ct = as.POSIXct( strptime( start, '%Y-%m-%d', tz = 'EST' ),
                         origin = '1970-01-01' ) 
  end.ct   = as.POSIXct( strptime( end, '%Y-%m-%d', tz = 'EST' ),
                         origin = '1970-01-01' ) 

  xlim = c( start.ct, end.ct )
  
  bam.df = read.csv( paste( bam.path, bam.file, sep = '' ),
                     header = TRUE, stringsAsFactors = FALSE )

  bam.Date = as.POSIXct( strptime( bam.df $ Time,
                                   '%Y-%m-%d %H:%M:%S',
                                   tz = 'EST' ),
                                   origin = '1970-01-01' )
  
  salt.df = read.csv( paste( salinity.path, salinity.file, sep = '' ),
                      header = TRUE, stringsAsFactors = FALSE )

  salt.Date = as.POSIXct( strptime( salt.df $ Date,
                                    '%Y-%m-%d', tz = 'EST' ),
                                    origin = '1970-01-01' )

  #---------------------------------------------------------------------
  if ( is.null( dev.list() ) ) {
    newPlot( mfrow = c( 2, 1 ) )
  }
  else {
    par( mfrow = c( 2, 1 ) )
  }

  salt.colors = c( 'red', 'darkgreen', 'brown', 'black' )
  
  if ( createPNG ) {
    nameExtension = paste( ' ', start, ' Salinity.png', sep = '' )
    png( filename = sub( '.csv', nameExtension, bam.file ),
        width = 1200, height = 800, units = "px",
        pointsize = 12, bg = "white", res = 150 )
    par( mfrow = c( 2, 1 ) )
    par( mar   = c(3, 3, 0.5, 0.5)  )
    par( mgp   = c(1.7, 0.6, 0) )
  }
  
  plot( bam.Date, bam.df $ Salinity, ylim = bam.ylim, xlim = xlim,
        type = 'l', col = 'blue', lwd = 2,
        xlab = 'Date', ylab = 'Salinity (ppt)' )
  mtext( paste( 'BAM:', sub( '.csv', '', bam.file )), line = -1.5, cex = 1.5 )
  mtext( bam.note, line = -2.7, cex = 1.3 )
  mtext( paste( start, ' : ', end ), line = -1.5, cex = 1.3, side = 1 )
  
  plot( salt.Date, salt.df[ , gauges[[1]][1] ], col = salt.colors[1],
        type = 'l', lwd = 2, ylim = salinity.ylim, xlim = xlim,
        xlab = 'Date', ylab = 'Salinity (ppt)' )

  if ( length( gauges[[1]] ) > 1 ) {
    for ( j in 2 : length( gauges[[ 1 ]] ) ) {
      lines( salt.Date, salt.df[ , gauges[[1]][j] ],
             col = salt.colors[j], lwd = 2 )
    }
  }
 
  if ( length( gauges ) > 1 ) {
    for ( i in 2 : length( gauges ) ) {
      for ( j in 1 : length( gauges[[ i ]] ) ) {
      
        lines( salt.Date, salt.df[ , gauges[[i]][j] ],
               col = salt.colors[[i]], lwd = 2 )
      }
    }
  }

  legend( 'top', legend = unlist( gauges ), col = salt.colors,
          lwd = 6, cex = 1.3, bty = 'n' )
  mtext( paste( start, ' : ', end ), line = -1.5, cex = 1.3, side = 1 )

  if ( createPNG ) {
    dev.off()
  }
}
