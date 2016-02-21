
source( '~/R/ReadData4EverCSV.R' )
#------------------------------------------------------------------------
#
#------------------------------------------------------------------------
CompareStages = function(
    delay     = 2,
    bam.path  = '../data/out/out.Jan-1-2010_Dec-7-2015/',
    station.i = NULL,
    starts    = c( rep( '2010-01-01', 20 ), '2015-05-01','2015-05-01' ),
    ends      = rep( '2015-12-01', 22 ),
    createPNG = FALSE
) {
  
  hydro.files = c(
      'MBTS_stage_1991-06-13_2015-10-09.csv',
      'LS_stage_1993-07-29_2015-12-08.csv',
      'LB_stage_1993-07-28_2015-12-08.csv',
      'BS_stage_1993-08-02_2015-12-08.csv',
      'DK_stage_1993-08-06_2015-12-08.csv',
      'TC_stage_1993-07-29_2015-12-08.csv',
      'JBTS_stage_1992-11-23_2015-12-08.csv',
      'LM_stage_1993-09-07_2015-12-08.csv',
      'LM_stage_1993-09-07_2015-12-08.csv',
      'GB_stage_1996-03-06_2015-12-08.csv',
      'BK_stage_1993-08-09_2015-12-08.csv',
      'MK_stage_1993-08-09_2015-12-08.csv',
      'JK_stage_1993-09-09_2015-12-08.csv',
      'LR_stage_1993-08-09_2015-12-08.csv',
      'LR_stage_1993-08-09_2015-12-08.csv',
      'PK_stage_1993-08-09_2015-12-08.csv',
      'PK_stage_1993-08-09_2015-12-08.csv',
      'WB_stage_1993-08-09_2015-12-08.csv',
      'BA_stage_1993-08-09_2015-12-08.csv',
      'BN_stage_1993-07-30_2015-12-08.csv',
      'PK_stage_1993-08-09_2015-12-08.csv',
      'WB_stage_1993-08-09_2015-12-08.csv'
      )
  bam.files = c(
      'Manatee Bay.csv',             'Long Sound.csv',
      'Little Blackwater Sound.csv', 'Blackwater Sound.csv',
      'Duck Key.csv',                'Deer Key.csv',
      'Joe Bay.csv',                 'Little Madeira Bay.csv',
      'Black Betsy Keys.csv',        'Rankin Lake.csv',
      'Snake Bight.csv',             'Conchie Channel.csv',
      'Johnson Key.csv',             'Twin Keys.csv',
      'Rabbit Key.csv',              'Lignumvitae.csv',
      'Long Key.csv',                'Whipray.csv',
      'Porpoise Lake.csv',           'Butternut Key.csv',
      'Lignumvitae.csv',             'Whipray.csv'
      )
  hydro.ylims = list(
      c(0.6,1.6),  c(0,0.8),    c(0,0.8),    c(0,0.8),    c(0,0.8),  
      c(0,0.8),    c(0,0.8),    c(0,0.8),    c(0,0.8),    c(-0.2,0.8),  
      c(-0.2,0.8), c(-0.7,1.3), c(-0.5,1),   c(-0.2,0.9), c(-0.2,0.9),
      c(-0.2,0.8), c(-0.2,0.8), c(-0.2,0.8), c(-0.2,0.8), c(-0.2,0.8),
      c(-0.1,0.8), c(-0.1,0.7)
      )
  bam.ylims = list(
      c(-0.4,0.6), c(-0.4,0.4), c(-0.4,0.4), c(-0.4,0.4), c(-0.2,0.6),
      c(-0.4,0.4), c(-0.4,0.4), c(-0.4,0.4), c(-0.4,0.4), c(-0.4,0.6),
      c(-0.4,0.6), c(-1,1),     c(-0.5,1),   c(-0.4,0.7), c(-0.4,0.7), 
      c(-0.4,0.6), c(-0.4,0.6), c(-0.4,0.6), c(-0.4,0.6), c(-0.6,0.4),
      c(-0.3,0.6), c(-0.2,0.6)
      )
  
  if ( is.null( station.i ) ) {
    station.i = 1 : length( hydro.files )
  }

  for ( i in station.i ) {

    print( paste( bam.files[i] ) )
    
    CompareStage( hydro.file = hydro.files[ i ],
                  bam.path   = bam.path,
                  bam.file   = bam.files  [ i ],
                  start      = starts     [ i ],
                  end        = ends       [ i ],
                  bam.ylim   = bam.ylims  [[ i ]],
                  hydro.ylim = hydro.ylims[[ i ]],
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
CompareStage = function(
   hydro.path = '../data/Stage/CSV/',
   hydro.file = 'LS_stage_1993-07-29_2015-12-08.csv',
   bam.path  = '../data/out/out.Jan-1-2010_Dec-5-2015/',
   bam.file   = 'Long Sound.csv',
   start      = '2010-01-01',
   end        = '2015-12-05',
   bam.ylim   = c(-0.2,0.6),
   hydro.ylim = c(0,0.8),
   bam.note   = '',
   createPNG  = FALSE
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

  hydro.df = Read.DFE.CSV(
    path        = hydro.path,
    file        = hydro.file,
    skip        = 9,
    header      = FALSE,
    na.strings  = 'null',
    col.names   = c('stn','type','time','stage','val'),
    time.format = '%Y-%m-%d %H:%M',
    time.col    = 3,
    delete.col  = c(1,2,5)
  )

  
  #---------------------------------------------------------------------
  if ( is.null( dev.list() ) ) {
    newPlot( mfrow = c( 2, 1 ) )
  }
  else {
    par( mfrow = c( 2, 1 ) )
  }

  if ( createPNG ) {
    png( filename = sub( '.csv', ' Stage.png', bam.file ),
         width = 1200, height = 800, units = "px",
         pointsize = 12, bg = "white", res = 150 )
    par( mfrow = c( 2, 1 ) )
    par( mar   = c(3, 3, 0.5, 0.5)  )
    par( mgp   = c(1.7, 0.6, 0) )
  }
  
  plot( bam.Date, bam.df $ Stage, ylim = bam.ylim, xlim = xlim,
        type = 'l', col = 'blue', lwd = 2,
        xlab = 'Date', ylab = 'Stage (m)' )
  mtext( paste( 'BAM:', sub( '.csv', '', bam.file )), line = -1.5, cex = 1.5 )
  mtext( bam.note, line = -2.7, cex = 1.3 )
  mtext( paste( start, ' : ', end ), line = -1.5, cex = 1.3, side = 1 )

  plot( hydro.df $ time, hydro.df $ stage * 0.3048, col = 'red',
        type = 'l', lwd = 2, ylim = hydro.ylim, xlim = xlim,
        xlab = 'Date', ylab = 'Stage (m)' )
  mtext( substr( hydro.file, 1, 2 ), line = -1.5, cex = 1.5 )
  mtext( paste( start, ' : ', end ), line = -1.5, cex = 1.3, side = 1 )

  if ( createPNG ) {
    dev.off()
  }
}
