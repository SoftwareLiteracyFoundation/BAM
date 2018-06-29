'''Constants for the Bay Assessment Model (BAM)'''

Version  = 'Version 1.4 2018-6-29'
#Version = 'Version 1.3 2018-2-7'
#Version = 'Version 1.2 2017-11-12'
#Version = 'Version 1.1 2017-3-27'
#Version = 'Version 1.0 2016-4-18'

# WGS Ellipsoidal Gravity Formula at 25.1 N
g = 9.7896248

textFont   = 'Arial 12'
buttonFont = 'Arial 10'

# Used to set appropriate legend and data type for map plot 
# in basin.SetBasinMapColor
BasinMapPlotVariable = [ 'Salinity', 'Stage' ] #, 'Temperature', 'Phosphate',
                         #'Nitrate', 'Ammonium', 'Oxygen', 'TOC' ]

# Used to select basin variable for timeseries plots
BasinPlotVariable = [ 'Salinity',   'Stage',       'Volume', 'Flow',
                      'Rain',       'Evaporation', 'Runoff', 'Groundwater' ]
                      #'Temperature','Phosphate',   'Nitrate','Ammonium',
                      #'Oxygen' ]

PlotVariableUnit = { 'Salinity'    : '(ppt)',   'Stage'       : '(m)',
                     'Volume'      : '(m^3)',   'Flow'        : '(m^3/s)',
                     'Rain'        : '(m^3/s)', 'Evaporation' : '(m^3/s)',
                     'Runoff'      : '(m^3/s)', 'Groundwater' : '(m^3/s)' }
                     #'Temperature': '(C)',     'Phosphate'   : '(mol/m^3/s)',
                     #'Nitrate'    : '(mol/m^3/s)',
                     #'Ammonium'   : '(mol/m^3/s)',
                     #'Oxygen'     : '(mol/m^3/s)' }

# Python analog of a C++ enumeration using a class
class Status:
    Init, Running, Finished, Paused, Halted, Plot = range( 6 )
