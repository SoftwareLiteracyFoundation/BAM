
#----------------------------------------------------------------------
#
#----------------------------------------------------------------------
Distance.Time = function(
  v    = c( 0.2, 0.1, 0.05, 0.03 ),
  T.hr = seq( 0, 30, 0.5 ),
  ylim = c( 0, 5000 )
) {

  T.hr.D = list()

  for ( velocity in v ) {
    # RMS velocity since it is a sin[0:pi/2] tidal current
    D = 0.707 * velocity * T.hr * 3600
    T.hr.D[[ paste( as.character( velocity * 100 ), '.cm.s', sep = '' ) ]] = D
  }

  if ( length( dev.list() ) == 0 ) { newPlot() }
  col = c( 'red', 'blue', 'darkgreen', 'magenta', 'brown' )
  
  plot( 0, 0, cex = 0, ylab = 'Distance (m)', xlab = 'Time (hr)',
        xlim = c( T.hr[1], T.hr[length(T.hr)] ), ylim = ylim,
        cex.axis = 1.3, cex.lab = 1.3 )

  col.i = 1
  for ( D in T.hr.D ) {
    lines( T.hr, D, lwd = 3, col = col[ col.i ] )
    col.i = col.i + 1
  }
  abline( v = 6, lty = 2, col = 'darkred' )
  legend( 'topleft', paste( as.character( v * 100 ), ' (cm/s)', sep = '' ),
          col = col, lwd = 6, bty = 'n', cex = 1.3 )
}

#----------------------------------------------------------------------
#
#----------------------------------------------------------------------
Time.Length = function(
  v = c( 0.2, 0.1, 0.05, 0.03 ),
  L = seq( 2000, 10000, 100 ),
  ylim = c( 0, 48 )
) {

  L.T.hr = list()
  
  for ( velocity in v ) {
    T.hr = L / velocity / 3600
    L.T.hr[[ paste( as.character( velocity * 100 ), '.cm.s', sep = '' ) ]] = T.hr
  }

  if ( length( dev.list() ) == 0 ) { newPlot() }
  col = c( 'red', 'blue', 'darkgreen', 'magenta', 'brown' )
  
  plot( 0, 0, cex = 0, ylab = 'Time (hr)', xlab = 'Basin length (m)',
        xlim = c( L[1], L[length(L)] ), ylim = ylim,
        cex.axis = 1.3, cex.lab = 1.3 )

  col.i = 1
  for ( T.hour in L.T.hr ) {
    lines( L, T.hour, lwd = 3, col = col[ col.i ] )
    col.i = col.i + 1
  }
  abline( h = 6, lty = 2, col = 'darkred' )
  legend( 'topleft', paste( as.character( v * 100 ), ' (cm/s)', sep = '' ),
          col = col, lwd = 6, bty = 'n', cex = 1.3 )
}
