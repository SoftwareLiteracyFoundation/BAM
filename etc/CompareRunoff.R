
#------------------------------------------------------------------------
#
#------------------------------------------------------------------------
CompareRunoffs = function(
    delay     = 2,
    station.i = NULL,
    plot      = TRUE,
    createPNG = FALSE
) {
  
  regions =
    rep( c( 'region1',
            'region1','region2','region3','region4','region5',  'region6',
            'region7','region8','region9','region10','region11','region12'), 3)

  bam.files =
    rep( c( 'Barnes Sound.csv',
            'Manatee Bay.csv',  'Long Sound.csv',   'Deer Key.csv',
            'Joe Bay.csv',      'Eagle Key.csv',    'Little Madeira Bay.csv',
            'Madeira Bay.csv',  'Terrapin Bay.csv', 'North Whipray.csv', 
            'Rankin Bight.csv', 'Rankin Lake.csv',  'Snake Bight.csv' ), 3)

  bam.paths = c(rep( '../data/out/out.May-1_Nov-1-2000/', 13 ),
                rep( '../data/out/out.May-1_Nov-1-2001/', 13 ),
                rep( '../data/out/out.May-1_Nov-1-2002/', 13 ))
  
  scales = rep( 7200, 39 ) # Scale FAT m^3/month to m^3/6 min

  starts = c( rep( '2000-05-01', 13 ),
              rep( '2001-05-01', 13 ),
              rep( '2002-05-01', 13 ) )
  
  ends   = c( rep( '2000-11-01', 13 ),
              rep( '2001-11-01', 13 ),
              rep( '2002-11-01', 13 ) )
  
  if ( is.null( station.i ) ) {
    station.i = 1 : length( bam.files )
  }

  for ( i in station.i ) {

    print( paste( bam.files[i] ) )
    
    CompareRunoff(
      fat.region = regions  [ i ],
      fat.scale  = scales   [ i ],
      bam.path   = bam.paths[ i ],
      bam.file   = bam.files[ i ],
      start      = starts   [ i ],
      end        = ends     [ i ],
      bam.ylim   = NULL,
      fat.ylim   = NULL,
      plot       = plot,
      createPNG  = createPNG
    )
    dev.flush()

    if ( ! is.null( delay ) ) {
      Sys.sleep( delay )
    }
  }

  # Estimate scale factors to match flows
  # BAM runoff is m^3/dt ... convert from m^3/month
  # for dt = 6 min : 10/hr * 24/day * 30 day = 7200 6 min/month
  s1 = ( scales / 7200 )[ 1  : 13 ]
  s2 = ( scales / 7200 )[ 14 : 26 ]
  s3 = ( scales / 7200 )[ 27 : 39 ]

  s.avg = apply( cbind( s1, s2, s3 ), 1, mean )

  df = data.frame( bam.files[ 1 : 13 ], s.avg )

  print( df )
  invisible( df )
}

#------------------------------------------------------------------------
#
#------------------------------------------------------------------------
CompareRunoff = function(
   fat.path   = './',
   fat.file   = 'FATHOM_Runoff_m3.csv',
   fat.region = 'region2',
   fat.scale  = 1E5,
   bam.path   = '../data/out/out.May-1_Nov-1-2002.ns/',
   bam.file   = 'Long Sound.csv',
   start      = '2002-05-01',
   end        = '2002-11-01',
   bam.ylim   = NULL,
   fat.ylim   = NULL,
   plot       = TRUE,
   createPNG  = FALSE
) {

  start.ct = as.POSIXct( strptime( start, '%Y-%m-%d', tz = 'EST' ),
                         origin = '1970-01-01' ) 
  end.ct   = as.POSIXct( strptime( end, '%Y-%m-%d', tz = 'EST' ),
                         origin = '1970-01-01' ) 

  xlim = c( start.ct, end.ct )

  # Read FATHOM runoff
  fat.df = read.csv( paste( fat.path, fat.file, sep = '' ),
                     header = TRUE, stringsAsFactors = FALSE )

  fat.Date = as.POSIXct( strptime( paste(fat.df$Year,fat.df$month,'1'), 
                                   '%Y %m %d', tz = 'EST' ),
                                   origin='1970-01-01')

  # Read BAM runoff
  bam.df = read.csv( paste( bam.path, bam.file, sep = '' ),
                     header = TRUE, stringsAsFactors = FALSE )

  bam.Date = as.POSIXct( strptime( bam.df $ Time,
                                   '%Y-%m-%d %H:%M:%S',
                                   tz = 'EST' ),
                                   origin = '1970-01-01' )

  # BAM runoff is m^3/dt ... convert to m^3/month
  # for dt = 6 min : 10/hr * 24/day * 30 day = 7200 6 min/month
  
  if ( plot ) {
    #-------------------------------------------------------------------------
    if ( is.null( dev.list() ) ) {
      newPlot() # mfrow = c( 2, 1 ) )
    }
    else {
      par( mfrow = c( 1, 1 ) )
    }

    if ( createPNG ) {
      nameExtension = paste( ' ', start, ' Runoff.png', sep = '' )
      png( filename = sub( '.csv', nameExtension, bam.file ),
          width = 1200, height = 800, units = "px",
          pointsize = 12, bg = "white", res = 150 )
      par( mar   = c(3, 3, 0.5, 0.5)  )
      par( mgp   = c(1.7, 0.6, 0) )
    }
  
    # Positive runoff is out of the basin
    plot( bam.Date, bam.df $ Runoff, ylim = bam.ylim, xlim = xlim,
          type = 'l', lwd = 2, col = 'blue',
          xlab = paste( start, ':', end ), ylab = 'Runoff (m^3)' )

    # FAT data is m^3/month : apply fat.scale
    # Invert sign since BAM runoff is negative (into basin)
    lines( fat.Date, -fat.df[ , fat.region ] / fat.scale, col = 'red', lwd = 4 )

    abline( h = 0 )
    legend( 'topleft', legend = c( 'BAM', 'FATHOM' ), lwd = 6,
            col = c( 'blue', 'red' ), bty = 'n', cex = 1.4 )
    
    mtext( paste( sub( '.csv', '', bam.file )), line = -1.5, cex = 1.5 )

    if ( createPNG ) {
      dev.off()
    }
  }
}
