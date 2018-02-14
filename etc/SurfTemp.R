
#-------------------------------------------------------------------------
# Using BK max surface temperature as a base, 
# Find regressions to BK maxTemp from GB and TC,
# and fill periods of BK missing data with GB and TC regressed data.
# Finally, call GapFill() to create surrogate data from random samples
# based on observed data over each year-day. 
#-------------------------------------------------------------------------
CreateMaxTemp = function() {
  L  = get(load('DailyMaxSurfTemp_List.Rdata'))
  bk = data.frame( Date=L$Date_BK, MaxTemp=L$BK )
  gb = data.frame( Date=L$Date_GB, MaxTemp=L$GB )
  tc = data.frame( Date=L$Date_TC, MaxTemp=L$TC )

  #-------------------------------------------------------
  # Linear regression to BK with available GB and TC
  #-------------------------------------------------------
  # GB Date's present in BK Date's, GB has more data
  gb.in.bk = match( gb$Date, bk$Date )
  # Get subset of BK that are at the same Date's as in GB
  BK       = bk$MaxTemp[ gb.in.bk ]
  plot( gb$MaxTemp, BK )
  # Linear Regression for BK maxTemp from GB
  # BK = 0.57196 + 0.99428 GB
  bk.gb.lm = lm( BK~gb$MaxTemp)
  summary(bk.gb.lm)
  abline(bk.gb.lm,lwd=2,col='red')

  tc.in.bk = match( tc$Date, bk$Date )
  BK       = bk$MaxTemp[ tc.in.bk ]
  plot( tc$MaxTemp, BK )
  # Linear Regression for BK maxTemp from TC
  # BK = 0.72327 + 1.00824 TC
  bk.tc.lm = lm( BK~tc$MaxTemp)
  summary(bk.tc.lm)
  abline(bk.tc.lm,lwd=2,col='red')

  #-------------------------------------------------------
  # Fill missing BK with available GB and TC
  #-------------------------------------------------------
  # GB Date's that are not in BK:
  gb.not.in.bk   = as.Date( setdiff( gb$Date, bk$Date ), origin = '1970-1-1' )
  i.gb.not.in.bk = match( gb.not.in.bk, gb $ Date )
  GB.df          = gb[ i.gb.not.in.bk, ]
  plot( GB.df $ Date, GB.df $ MaxTemp, type = 'l' )

  # TC Date's that are not in GB: (to be added to GB's not in BK
  tc.not.in.gb   = as.Date( setdiff( tc$Date, gb$Date ), origin = '1970-1-1' )
  i.tc.not.in.gb = match( tc.not.in.gb, tc $ Date )
  TC.df          = tc[ i.tc.not.in.gb, ]
  plot( TC.df $ Date, TC.df $ MaxTemp, type = 'l' )

  # Create a data.frame to hold the various max temp data in one record
  start = as.Date( '1999-9-1'  )
  end   = as.Date( '2017-6-30' )
  N     = as.numeric( end - start ) + 1
  df    = data.frame( Date = seq( start, end, 1 ),
                      MaxTemp = rep( NA, N ) )

  # Fill in BK data
  i.bk.dates.in.df = match( bk $ Date, df $ Date )
  df[ i.bk.dates.in.df, "Date"    ] = bk $ Date
  df[ i.bk.dates.in.df, "MaxTemp" ] = bk $ MaxTemp
  plot ( df $ Date, df $ MaxTemp, type='l' )
  lines( bk $ Date, bk $ MaxTemp, col='red')
  
  # Fill in GB data not in BK from GB.df 
  i.gb.dates.in.df = match( GB.df $ Date, df $ Date )
  df[ i.gb.dates.in.df, "Date"    ] = GB.df $ Date
  df[ i.gb.dates.in.df, "MaxTemp" ] = 0.57196 + GB.df $ MaxTemp * 0.99428 
  plot ( df $ Date, df $ MaxTemp, type='l' )
  lines( bk $ Date, bk $ MaxTemp, col='red')
  lines( GB.df $ Date, GB.df $ MaxTemp, col='blue')
  
  # Fill in TC data not in BK from TC.df 
  i.tc.dates.in.df = match( TC.df $ Date, df $ Date )
  df[ i.tc.dates.in.df, "Date"    ] = TC.df $ Date
  df[ i.tc.dates.in.df, "MaxTemp" ] = 0.72327 + TC.df $ MaxTemp * 1.00824
  plot ( df $ Date, df $ MaxTemp, type='l' )

  # Q/A and output
  i.low = which( df$MaxTemp < 5 )
  df[ i.low $ MaxTemp ] = NA

  # These seem to be bogus data in the BK timeseries
  # as.Date(c(14817, 14860, 14874, 14922), origin='1970-1-1')
  for ( i in c( 14817, 14860, 14874, 14922 ) ) {
    Date = as.Date( i, origin='1970-1-1' )
    row  = which( df $ Date == Date )
    df[ row, 'MaxTemp' ] = round( mean( df[ (row-1), 'MaxTemp' ],
                                        df[ (row+1), 'MaxTemp' ] ), 2 )
  }

  
  save( df, file = 'MaxTemp_1999-9-1_2017-6-30.Rdata' )

  # Create Surrogate data
  source( '~/R/GapFill.R' )
  df = GapFill( df, var='MaxTemp' )
  df $ MaxTemp = round( df $ MaxTemp, 2 ) # GapFill is full precision
  plot( df $ Date, df $ MaxTemp, type = 'l',
        xlab = '', ylab = 'Surface Temperature Max (C)' )
  
  save( df, file = 'MaxTemp_Filled_1999-9-1_2017-6-30.Rdata' )

  invisible( df )
}


#-------------------------------------------------------------------------
# Change in vapor pressure (and thus evaporation)
# from reference temp T2 to temp T1
#
#-------------------------------------------------------------------------
VaporPressureRatio = function(
  dH = 44000, # enthalpy of vaporization J/mol
  R  = 8.314, # universal gas constant   J/(mol K)
  T1 = seq( 10, 40, 0.2 ),
  T2 = 20
  ) {

  T1 = T1 + 273.15
  T2 = T2 + 273.15

  # Clausius-Clapeyron relation:
  # ln( P2/P1 ) = ( dH / R ) * (1/T2 - 1/T1) 
  P_Pref = exp( (dH/R) * (1/T2 - 1/T1) )

  if ( is.null( dev.list() ) ) {
    newPlot()
  }

  plot( T1 - 273.15, P_Pref, type = 'l', lwd = 2,
        xlab = 'Temperature (C)', ylab = 'P / Pref' )
  
  # summary(df$MaxTemp)
  # Min. 1st Qu.  Median    Mean 3rd Qu.    Max. 
  # 14.0    26.2    29.5    29.2    32.7    37.7 
  abline( v = c( 14, T2 - 273.15, 37.7 ) ) # Limits of the max temp data
  abline( h = 1 )


  invisible( data.frame( T = T1 - 273.15, P_Pref = P_Pref ) )
}

#-------------------------------------------------------------------------
#-------------------------------------------------------------------------
PlotSurfaceTempPanels = function() {
  
  newPlot(mfrow=c(4,2))

  dates=c("Date_BK","Date_LS","Date_TB","Date_LM","Date_GB","Date_MK","Date_TC")
  data=c("BK","LS","TB","LM","GB","MK","TC")

  L = get(load('DailyMaxSurfTemp_List.Rdata'))

  for(i in 1:length(data)){
    plot( L[[dates[i]]], L[[data[i]]],
          type = 'l', xlab = '', ylab = 'Max T (C)',
          ylim = c(15,35),
          xlim = c( as.Date('1999-9-1'), as.Date('2017-6-30') ) )
    mtext( data[i], side=3, line=-1.8, cex=1.5)
  }
}

#-------------------------------------------------------------------------
#-------------------------------------------------------------------------
PlotSurfaceTempOverlay = function(
  file  = 'DailyMaxSurfTemp_List.Rdata',
  start = '1999-9-1',
  end   = '2017-6-30',
  addET = FALSE
) {

  L = get( load( file ) )
  
  dataLabel = c( 'BK', 'LS', 'TB', 'GB', 'LM', 'MK', 'TC' )

  if ( is.null( dev.list() ) ) { newPlot() }

  xlim = c( as.Date( start ), as.Date( end ) )
      
  plot ( L $ Date_GB, L $ GB, type = 'l', xlim = xlim,
         xlab = '', xaxt = 'n', ylab = 'Daily Maximum Surface Temp (C)' )
  lines( L $ Date_TB, L $ TB, col = 'red' )
  lines( L $ Date_BK, L $ BK, col = 'magenta' )
  lines( L $ Date_MK, L $ MK, col = 'brown' )
  lines( L $ Date_LM, L $ LM, col = 'blue' )
  lines( L $ Date_TC, L $ TC, col = 'green' )
  lines( L $ Date_LS, L $ LS, col = 'yellow' )

  axis.Date( side = 1,
    at = as.Date( paste( as.character(seq(1999,2017,1)), '-1-1', sep='' ) ) )

  legend( 'topleft', legend = dataLabel, lwd = 5, bty = 'n', bg = 'white',
          col = c( 'magenta', 'yellow', 'red',
                   'black', 'blue', 'brown', 'green'), cex = 1.1 )

  if ( addET ) {
    et = read.csv('../data/ET/PET_1999-9-1_2016-12-31.csv',as.is=T,header=T)
    Date = as.Date(et$Time)
    lines(Date,et$PET*5)
    abline( v = as.Date('2015-7-21'), lwd=6, lty = 2, col='red' )
    
    legend( 'bottomleft', legend = 'USGS EDEN PET', col = 'black',
            fill = 'black', cex = 1.5, bty = 'n' )

  }
}

#-------------------------------------------------------------------------
#-------------------------------------------------------------------------
ReadSurfaceTemp = function(
  out.file = 'DailyMaxSurfTemp_List.Rdata'
) {

  source( '~/R/ReadData4EverCSV.R' )
  
  files = c( 'BK_SurfaceTemp.csv', 'LS_Temp.csv',     'TB_SurfTemp.csv',
             'GB_SurfaceTemp.csv', 'LM_SurfTemp.csv', 'MK_SurfTemp.csv',
             'TC_SurfTemp.csv' )

  dataLabel = c( 'BK', 'LS', 'TB', 'GB', 'LM', 'MK', 'TC' )

  L = list()
  
  for ( i in 1 : length( files ) ) {

    file = files[i]
    
    dfi = Read.DFE.CSV( file = file, out.file = NULL, skip = 8, 
                        header = TRUE, na.strings = "null",
                        col.names = NULL, time.col = 3, delete.col = c( 1,2,5) )

    print( paste( file, names( dfi ) ) )
    print( head( dfi ) )
    
    dateLabel = paste( "Date_", dataLabel[i], sep = '' )
    L[[ dateLabel    ]] = as.Date( dfi $ date )
    L[[ dataLabel[i] ]] = dfi [ , 'maximum.celsius.' ]
  }

  if ( is.null( dev.list() ) ) { newPlot() }
      
  plot ( L $ Date_GB, L $ GB, type = 'l',
         xlab = '', ylab = 'Daily Maximum Surface Temp (C)' )
  lines( L $ Date_TB, L $ TB, col = 'red' )
  lines( L $ Date_BK, L $ BK, col = 'magenta' )
  lines( L $ Date_MK, L $ MK, col = 'brown' )
  lines( L $ Date_LM, L $ LM, col = 'blue' )
  lines( L $ Date_TC, L $ TC, col = 'green' )
  lines( L $ Date_LS, L $ LS, col = 'yellow' )

  legend( 'bottom', bty = 'n', legend = dataLabel, lwd = 5, 
          col = c( 'magenta', 'yellow', 'red',
                   'black', 'blue', 'brown', 'green'), cex = 1.5 )

  if ( ! is.null( out.file ) ) {
    save( L, file = out.file )
  }
  
  invisible( L )
}
