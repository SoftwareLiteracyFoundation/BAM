
#------------------------------------------------------------------
#
#------------------------------------------------------------------
CreateTide = function (
  path            = '../data/HourlyTide/',
  cape.sable.tide = 'Cape_Sable_1990-01-01_2021-01-02.csv',
  long.key.tide   = 'Long_Key_1990-01-01_2021-01-02.csv',
  region2.tide    = 'Region2_1990-01-01_2021-01-02.csv',
  region3.tide    = 'Region3_1990-01-01_2021-01-02.csv'
) {

  # Comparison of Cape Sable and Long Key tides shows that Long Key is
  # 'delayed' by 6 - 8 hours and attenuated by 2.7 - 3
  # Heuristically we assume that Region 2 is 2/3 amplitude and 3 hours
  # delayed from Cape Sable, and Region 3 is 4/3 amplitude and 3 hours
  # prior to Long Key. 
  
  # hourly tide data
  #---------------------------------
  # Time, WL.(m).demeaned
  # 1990-01-01 12:00 AM EST, 0.211
  # 1990-01-01 1:00 AM EST,  0.14
  df.in = read.csv( paste( path, cape.sable.tide, sep = '' ),
                    header = TRUE, 
                    colClasses = c( 'character', 'numeric' ) )

  # Region 2 is assumed to be a delayed (3 hours) and scaled
  # (0.66) version of the cape.sable data
  # Remove the first three hours of data, but keep the times intact
  data = df.in $ WL..m..demeaned [ 4 : nrow( df.in ) ]
  Time = df.in $ Time[ 1 : ( nrow( df.in ) - 3 ) ]

  df.region2 = data.frame( Time, round( data * 2 / 3, 3 ) )
  write.table( df.region2, file = region2.tide,
               sep = ',', quote = FALSE,
               col.names = c( 'Time', 'WL.(m).demeaned' ),
               row.names = FALSE )

  print( head( df.region2 ) )
  print( tail( df.region2 ) )
  
  # Region 3 is assumed to be prior (3 hours) and scaled
  # (1.33) version of the long.key data
  # These are the values from XTide:
  # HourlyTide> tide -l "Long Key, western end, Florida"
  # -b "1989-12-31 21:00" -e "1990-01-01 03:00" -mm -um -s 01:00
  # Indexing /usr/share/xtide/harmonics-initial.tcd...
  # Indexing /usr/share/xtide/harmonics-dwf-20100529-free.tcd...
  # 1989-12-31  9:00 PM EST 0.375638
  # 1989-12-31 10:00 PM EST 0.432238
  # 1989-12-31 11:00 PM EST 0.448363
  # 1990-01-01 12:00 AM EST 0.420069
  # 1990-01-01  1:00 AM EST 0.348880
  # 1990-01-01  2:00 AM EST 0.245524

  # but have to demean the data...
  # > head(df)
  #                      Time WL..m..demeaned
  # 1 1990-01-01 12:00 AM EST           0.211
  # 2  1990-01-01 1:00 AM EST           0.140
  # 3  1990-01-01 2:00 AM EST           0.036

  # > c(  0.420069, 0.348880, 0.245524 ) - c( 0.211, 0.140, 0.036 )
  # [1] 0.2091 0.2089 0.2095

  # So the first three values are:
  # > c( 0.375638, 0.432238, 0.448363 ) - 0.2092
  # [1] 0.1664 0.2230 0.2392
  

  # Shift the data by +three hours and add the prior values,
  # but keep the times intact
  df.in = read.csv( paste( path, long.key.tide, sep = '' ),
                    header = TRUE, 
                    colClasses = c( 'character', 'numeric' ) )

  data = df.in $ WL..m..demeaned
  Time = df.in $ Time

  data [ 4 : nrow( df.in ) ] = data [ 1 : ( nrow( df.in ) - 3 ) ]
  data [ 1 : 3 ] = c( 0, 0, 0 ) # c( 0.1664, 0.2230, 0.2392 )

  df.region3 = data.frame( Time, round( data * 4 / 3, 3 ) )
  write.table( df.region3, file = region3.tide,
               sep = ',', quote = FALSE,
               col.names = c( 'Time', 'WL.(m).demeaned' ),
               row.names = FALSE )

  print( head( df.region3 ) )
  print( tail( df.region3 ) )
}
