
Version = 'Version 0.1 2016-mm-dd'

# WGS Ellipsoidal Gravity Formula at 25.1 N
g = 9.7896248

textFont = 'Arial 12'

# Used to set appropriate legend and data type for map plot 
# in basin.SetBasinMapColor
BasinMapPlotVariable = [ 'Salinity', 'Stage', 'Temperature', 'Phosphate',
                         'Nitrate', 'Ammonium', 'Oxygen', 'TOC' ]

# Used to select basin variable for timeseries plots
BasinPlotVariable = [ 'Salinity',   'Stage',       'Volume', 'Flow',
                      'Rain',       'Evaporation', 'Runoff', 'Groundwater',
                      'Temperature','Phosphate', '  Nitrate','Ammonium',
                      'Oxygen' ]

PlotVariableUnit = { 'Salinity'    : '(ppt)',    'Stage'       : '(m)',
                     'Volume'      : '(m^3)',    'Flow'        : '(m^3/dt)',
                     'Rain'        : '(m^3/dt)', 'Evaporation' : '(m^3/dt)',
                     'Runoff'      : '(m^3/dt)', 'Groundwater' : '(m^3/dt)', 
                     'Temperature' : '(C)',      'Phosphate'   : '(mol/m^3/dt)',
                     'Nitrate'     : '(mol/m^3/dt)',
                     'Ammonium'    : '(mol/m^3/dt)',
                     'Oxygen'      : '(mol/m^3/dt)' }

# Python analog of a C++ enumeration using a class
class Status:
    Init, Running, Finished, Paused, Halted, Plot = range( 6 )
