#----------------------------------------------------------------------
#
#----------------------------------------------------------------------
Gulf.Salinity = function(
  path      = '../data/Salinity/',
  salt.file = 'DailySalinityFilled_1999-9-1_2015-12-8.csv',
  out.file  = 'Gulf.Salinity_1999-9-1_2015-12-8.csv'
) {

  df = read.csv( paste( path, salt.file, sep = '' ), as.is = TRUE,
                 header = TRUE )

  Date = strptime( df $ Date, '%Y-%m-%d' )

  # Gulf Salinity 
  # Take the mean of the 4 western station salinities
  S = rowMeans( cbind( df $ MK, df $ JK, df $ LR, df $ PK ) )

  #-----------------------------------------------
  if ( length( dev.list() ) == 0 ) {
    newPlot()
  }
  plot ( Date, df $ MK, type = 'l', col = 'red', ylim = c(25,50) )
  lines( Date, df $ JK, col = 'blue' )
  lines( Date, df $ LR, col = 'darkgreen' )
  lines( Date, df $ PK, col = 'brown' )
  lines( Date, S, lwd = 3 )

  df = data.frame( Date = as.POSIXct( Date, origin = '1970-1-1' ),
                   Salinity = round( S, 2 ) )
  write.csv( df, file = paste( path, out.file, sep = '' ),
             row.names = FALSE, quote = FALSE )

  invisible( df )
}
  
#----------------------------------------------------------------------
#
#----------------------------------------------------------------------
Ocean.Salinity = function(
  path      = '../data/Salinity/',
  salt.file = 'DailySalinityFilled_1999-9-1_2015-12-8.csv',
  out.file  = 'Ocean.Salinity_1999-9-1_2015-12-8.csv',
  tol       = 5,
  max.sift  = 200,
  max.imf   = 20,
  imfs      = seq( 7, 10 )
) {

  library( hht )
  
  df = read.csv( paste( path, salt.file, sep = '' ), as.is = TRUE,
                 header = TRUE )

  Date = strptime( df $ Date, '%Y-%m-%d' )

  sig = df $ PK
  tt  = as.numeric( as.POSIXct( Date, origin = '1970-1-1' ) )
  
  EMD = Sig2IMF( sig,  tt,
                 stop.rule = "type5",
                 tol       = tol,
                 max.sift  = max.sift,
                 max.imf   = max.imf )
  
  # Ocean salinity from PK IMFs
  IMF      = EMD $ imf
  Salinity = EMD $ residue

  for ( imf in imfs ){
    Salinity = Salinity + IMF[,imf]
  }

  for ( imf in imfs ) {
    mean.freq = mean( EMD $ hinstfreq[, imf] )
    print( paste( 'IMF', imf, '<T_day> =', round( 1 / mean.freq / 86400 ) ) )
  }
  
  df = data.frame( Date = as.POSIXct( Date, origin = '1970-1-1' ),
                   Salinity = round( Salinity, 2 ) )
  
  if ( ! is.null( out.file ) ) {
    write.csv( df, file = paste( path, out.file, sep = '' ),
               row.names = FALSE, quote = FALSE )
  }
  
  #-----------------------------------------------
  if ( length( dev.list() ) == 0 ) {
    newPlot()
  }
  plot ( Date, sig, type = 'l', col = 'red', lwd = 2, ylim = c(25,45) )
  lines( Date, df $ Salinity, col = 'blue', lwd = 3 )

  invisible( list( EMD = EMD, df = df ) )
}

