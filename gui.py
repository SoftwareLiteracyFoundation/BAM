'''tkinter Tcl/Tk GUI for the Bay Assessment Model (BAM)'''

# Python distribution modules
from subprocess  import Popen
from datetime    import timedelta, datetime
from collections import OrderedDict as odict
from os.path     import exists as path_exists
from random      import randint

strptime = datetime.strptime

# Note that these are separate modules:
#   tkinter.filedialog
#   tkinter.messagebox
#   tkinter.font
import tkinter as Tk
from   tkinter import messagebox
from   tkinter import filedialog
from   tkinter import ttk # tk themed widgets within tkinter (tkinter.ttk)

# Community modules
from numpy import linspace, isnan
from numpy import all as npall
from numpy import NaN as npNaN

from matplotlib.colors   import ListedColormap
from matplotlib.colors   import BoundaryNorm
from matplotlib.colorbar import ColorbarBase

# These matplotlib objects are only used in MouseClick 
from matplotlib.lines   import Line2D
from matplotlib.patches import Polygon
# Used in PlotData
from matplotlib.dates  import YearLocator, MonthLocator, DayLocator
from matplotlib.dates  import DateFormatter
from matplotlib.pyplot import cm
# Modules to embed matplotlib figure in a Tkinter window, see:
# http://matplotlib.org/examples/user_interfaces/embedding_in_tk.html
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_tkagg import NavigationToolbar2TkAgg

# Local modules 
from init import InitTimeBasins
from init import GetBasinSalinityData
from init import GetBasinStageData
from init import GetTimeIndex
import constants

#---------------------------------------------------------------
# 
#---------------------------------------------------------------
class GUI:
    '''GUI : tkinter & ttk with embedded matplotlib figure.'''

    def __init__( self, root, model ):

        self.model = model
        
        # GUI objects
        self.Tk_root            = root
        self.figure             = None   # matplotlib figure set onto canvas
        self.figure_axes        = None   # 
        self.canvas             = None   # 
        self.colorbar           = None   # legend
        self.basinListBox       = None   # in the mainframe
        self.basinListBoxMap    = dict() # { basin name : listbox index }
        self.shoalListBox       = None   # a Toplevel pop-up
        self.gaugeListBox       = None   # a Toplevel pop-up
        self.msgText            = None   # Tk.Text widget for gui messages

        self.buttonStyle = ttk.Style() # Note that BAM.TButton is child class
        self.buttonStyle.configure( 'BAM.TButton', font = constants.buttonFont )
        self.checkButtonStyle = ttk.Style() 
        self.checkButtonStyle.configure('BAM.TCheckbutton',
                                         font = constants.textFont )
        
        self.mapOptionMenu      = None # map plot variable selection
        self.plotOptionMenu     = None # timeseries plot variable selection
        self.startTimeEntry     = None # simulation start time
        self.endTimeEntry       = None # simulation end time

        self.plotVar_IntVars    = odict() # { plotVariable : Tk.IntVar() }
        
        if not self.model.args.noGUI :
            # Set Tk-wide Font default for filedialog
            # But it doesn't set filedialog window or button fonts
            #root.tk.call( "option", "add", "*Font", constants.textFont ) 
            root.option_add( "*Font", constants.textFont )

            self.mapPlotVariable    = Tk.StringVar()
            self.plotVariable       = Tk.StringVar()
            self.current_time_label = Tk.StringVar()
            self.start_text         = Tk.StringVar( value = model.args.start )
            self.end_text           = Tk.StringVar( value = model.args.end   )

        self.plot_dir           = model.args.basinOutputDir
        self.last_plot_dir      = self.plot_dir

        # matplotlib colors can be names ('red', 'blue', 'green') or 
        # R, G, B tuple in the range [0,1] or fraction of gray in [0,1] '0.5'
        # These 10 colors define the legend and map color ranges
        self.colors = [ [ 0., 0., 1. ], [ 0., .2,  1. ], 
                        [ 0., .4, 1. ], [ 0., .6,  1. ],
                        [ 0., .8, 1. ], [ 1., .8,  0. ],
                        [ 1., .6, 0. ], [ 1., .4,  0. ],
                        [ 1., .2, 0. ], [ 1.,  0., 0. ] ]

    #------------------------------------------------------------------
    #
    #------------------------------------------------------------------
    def FloridaBayModel_Tk ( self ) :
        '''User interface for the Florida Bay Model'''

        icon = None

        try :
            icon = Tk.PhotoImage( file = self.model.args.path +\
                                 'data/init/PyFBM_icon.png' )
        except :
            icon = Tk.PhotoImage( file = self.model.args.path +\
                                 'data/init/PyFBM_icon.gif' )

        if icon :
            self.Tk_root.iconphoto( True, icon )

        # Create the main widget Frame (window) and a control frame
        mainframe    = ttk.Frame( self.Tk_root, padding = "3 3 3 3" )
        controlframe = ttk.Frame( self.Tk_root, padding = "1 1 1 1" )
        
        # Create matplotlib figure and the canvas it is rendered onto
        self.figure = Figure( figsize   = (5, 4), # width x height (in)
                              dpi       = 150, 
                              facecolor = 'grey' )

        self.figure_axes = self.figure.add_axes( ( 0, 0, 1, 1 ), 
                                                 frameon = False, 
                                                 axisbg  = 'none' )
        
        # Map limits are UTM Zone 17R in (m)
        self.figure_axes.set_xlim( ( 490000,  569000  ) )
        self.figure_axes.set_ylim( ( 2742000, 2799000 ) )

        self.canvas = FigureCanvasTkAgg( self.figure, master = mainframe )

        self.canvas.mpl_connect( 'pick_event', self.MouseClick )

        # Setup the menu bar
        menuBar = Tk.Menu( self.Tk_root )
        self.Tk_root.config( menu = menuBar )
        # File Menu -----------------------------------------------
        menuFile = Tk.Menu( menuBar, tearoff=False, font = constants.textFont )
        menuBar.add_cascade( menu = menuFile, label = ' File ', 
                             font = constants.textFont )
        menuFile.add_command( label = ' Init',   command = self.OpenInitFile )
        menuFile.add_command( label = ' Edit',   command = self.EditFile     )
        # Dir Menu -----------------------------------------------
        menuDir = Tk.Menu( menuBar, tearoff=False, font = constants.textFont )
        menuBar.add_cascade( menu = menuDir, label = ' Dir ', 
                             font = constants.textFont )
        menuDir.add_command( label = 'Plot Disk', command = self.GetPlotDir   )
        menuDir.add_command( label = ' Output ',  command = self.GetOutputDir )
        # Help Menu -----------------------------------------------
        menuHelp = Tk.Menu( menuBar, tearoff=False, font = constants.textFont )
        menuBar.add_cascade( menu = menuHelp, label = 'Help', 
                             font = constants.textFont )
        menuHelp.add_command( label = 'About', command = self.ShowAboutInfo )

        # Entry for start and end time, register CheckTimeEntry validatecommand
        checkTimeCommand = controlframe.register( self.CheckTimeEntry )

        self.startTimeEntry = ttk.Entry( mainframe, width = 15, 
                                         font = constants.textFont,
                                         justify = Tk.LEFT, 
                                         textvariable = self.start_text,
                                         validatecommand = ( checkTimeCommand, 
                                                             '%P', '%W' ),
                                         validate = 'focusout' )

        self.endTimeEntry = ttk.Entry( mainframe, width = 15, 
                                       font = constants.textFont,
                                       justify = Tk.LEFT, 
                                       textvariable = self.end_text,
                                       validatecommand = ( checkTimeCommand, 
                                                           '%P', '%W' ),
                                       validate = 'focusout' )

        # Current model time
        currentTimeLabel = Tk.Label( mainframe, width = 18, height = 1, 
                                     bg = 'white',
                                     font = constants.textFont,
                                     justify = Tk.CENTER, 
                                     textvariable = self.current_time_label )

        # Text box for messages
        self.msgText = Tk.Text( mainframe, height = 5,
                                background='white', font = constants.textFont )
        self.Message( self.model.Version )
        self.Message( self.model.args.commandLine + '\n' )
        
        msgScrollBar = ttk.Scrollbar( mainframe, orient = Tk.VERTICAL, 
                                      command = self.msgText.yview )

        self.msgText.configure( yscrollcommand = msgScrollBar.set )

        # Basin Listbox
        self.basinListBox = Tk.Listbox( mainframe, height = 5, width = 20, 
                                        selectmode = Tk.EXTENDED, 
                                        font = constants.textFont )

        # Insert the basin names into the Listbox
        # The listvariable = [] option won't work if
        # there is whitespace in a name, so insert them manually
        i = 0
        for Basin in self.model.Basins.values() :
            self.basinListBox.insert( i, Basin.name )
            self.basinListBoxMap[ Basin.name ] = i
            i = i + 1

        # Listbox vertical scroll bar : calls model.basinListBox.yview
        scrollBar = ttk.Scrollbar( mainframe, orient = Tk.VERTICAL, 
                                   command = self.basinListBox.yview )

        # Tell the Listbox that it will scroll according to the scrollBar
        self.basinListBox.configure( yscrollcommand = scrollBar.set )

        # Listbox calls ProcessBasinListbox() when selection changes
        self.basinListBox.bind('<<ListboxSelect>>', self.ProcessBasinListbox)

        # Colorize alternating lines of the listbox
        for i in range( 0, len( self.model.Basins.keys() ), 2):
            self.basinListBox.itemconfigure( i, background = '#f0f0ff' )
            
        #--------------------------------------------------------------------
        # These widgets are in the control frame
        # OptionMenu for map plot types
        self.mapPlotVariable.set( constants.BasinMapPlotVariable[0] )

        self.mapOptionMenu = Tk.OptionMenu( controlframe, 
                                            self.mapPlotVariable,
                                            *constants.BasinMapPlotVariable )

        self.mapOptionMenu.config        ( font = constants.buttonFont )
        self.mapOptionMenu['menu'].config( font = constants.buttonFont )
        self.mapOptionMenu.config( bg = 'white' )

        # Button for self.Init()
        initButton = ttk.Button( controlframe, text = "Init",
                                 style = 'BAM.TButton',
                                 command = lambda : InitTimeBasins(self.model))

        # Button for model.Run()
        runButton = ttk.Button( controlframe, text = "Run",
                                style = 'BAM.TButton',
                                command = self.model.Run )

        # Button for model.Pause()
        pauseButton = ttk.Button( controlframe, text = "Pause",
                                  style = 'BAM.TButton',
                                  command = self.model.Pause )

        # Button for model.Stop()
        stopButton = ttk.Button( controlframe, text = "Stop",
                                 style = 'BAM.TButton',
                                 command = self.model.Stop )

        # Button for model.GetRecordVariables()
        recordVarButton = ttk.Button( controlframe, text = "Record",
                                      style = 'BAM.TButton',
                                      command = self.GetRecordVariables )

        # OptionMenu for variable timeseries plot types
        self.plotVariable.set( constants.BasinPlotVariable[0] )

        self.plotOptionMenu = Tk.OptionMenu( controlframe, self.plotVariable,
                                             *constants.BasinPlotVariable )
        
        self.plotOptionMenu.config        ( font = constants.buttonFont )
        self.plotOptionMenu['menu'].config( font = constants.buttonFont )
        self.plotOptionMenu.config( bg = 'white' )

        # Button for model.PlotRunData()
        plotRunButton = ttk.Button( controlframe, text = "Plot Run",
                                    style = 'BAM.TButton',
                                    command = self.PlotRunData )

        # Button for model.PlotArchiveData()
        plotArchiveButton = ttk.Button( controlframe, text = "Plot Disk",
                                        style = 'BAM.TButton',
                                        command = self.PlotArchiveData )

        # Button for PlotGaugeSalinityData()
        # Can't set text color in ttk Button, use standard Tk
        plotGaugeSalinityButton = Tk.Button( controlframe, text = "Salinity",
                                    command = self.PlotGaugeSalinityData,
                                    font = constants.buttonFont,
                                    foreground = 'blue' )
        
        # Button for PlotGaugeStageData()
        # Can't set text color in ttk Button, use standard Tk
        plotGaugeStageButton = Tk.Button( controlframe, text = "Stage",
                                          command = self.PlotGaugeStageData,
                                          font = constants.buttonFont,
                                          foreground = 'blue' )
        
        #-------------------------------------------------------------------
        # Setup the window layout with the 'grid' geometry manager. 
        # The value of the "sticky" option is a string of 0 or more of the 
        # compass directions N S E W, specifying which edges of the cell the 
        # widget should be "stuck" to.
        mainframe.grid( row = 0, column = 0, sticky = (Tk.N, Tk.W, Tk.E, Tk.S) )
        
        controlframe.grid( in_ = mainframe, row = 1, column = 1, 
                           rowspan = 3, sticky = (Tk.N, Tk.S) )

        #-------------------------------------------------------------------
        # Grid all the widgets - This is the layout of the window
        # This application has 5 columns and 4 rows
        # Column 1 row 1 has the controlframe with its own grid manager
        #           col 0     |    col 1     |   col 2    |   col 3  |  col 4
        # row 0   Basin List  |    <-----------   Message Text  ----------->  
        # row 1       \/      |   Controls   | Model Time |  Start   |  End 
        # row 2       \/      |      \/      |  <----------  Map  --------->
        # row 3       \/      |      \/      |               \/
        #
        #-------------------------------------------------------------------
        self.basinListBox.grid( column = 0, row = 0, rowspan = 4, 
                                sticky = (Tk.N,Tk.S,Tk.W,Tk.E) )
        
        scrollBar.grid( column = 0, row = 0, rowspan = 4, 
                        sticky = (Tk.E,Tk.N,Tk.S) )

        self.msgText.grid( column = 1, row = 0, columnspan = 4,
                            sticky = (Tk.N,Tk.S,Tk.W,Tk.E) )

        msgScrollBar.grid( column = 4, row = 0, 
                           sticky = (Tk.E,Tk.N,Tk.S) )

        currentTimeLabel.grid    ( column = 2, row = 1 )
        self.startTimeEntry.grid ( column = 3, row = 1 )
        self.endTimeEntry.grid   ( column = 4, row = 1 )
        
        #-------------------------------------------------------------
        # controlframe.grid is set above
        self.mapOptionMenu.grid( in_ = controlframe, row = 0 )
        initButton.grid        ( in_ = controlframe, row = 1 )
        runButton.grid         ( in_ = controlframe, row = 2 )
        pauseButton.grid       ( in_ = controlframe, row = 3 )
        stopButton.grid        ( in_ = controlframe, row = 4 )

        ttk.Separator( orient = Tk.HORIZONTAL ).grid( in_ = controlframe, 
                                                      row = 5, pady = 5,
                                                      sticky = (Tk.E,Tk.W) )

        recordVarButton.grid   ( in_ = controlframe, row = 6 )

        ttk.Separator( orient = Tk.HORIZONTAL ).grid( in_ = controlframe, 
                                                      row = 7, pady = 5,
                                                      sticky = (Tk.E,Tk.W) )

        self.plotOptionMenu.grid( in_ = controlframe, row = 8  )
        plotRunButton.grid      ( in_ = controlframe, row = 9  )
        plotArchiveButton.grid  ( in_ = controlframe, row = 10 )

        ttk.Separator( orient = Tk.HORIZONTAL ).grid( in_ = controlframe, 
                                                      row = 11, pady = 5,
                                                      sticky = (Tk.E,Tk.W) )

        plotGaugeSalinityButton.grid( in_ = controlframe, row = 12,
                                      sticky = (Tk.E,Tk.W) )
        plotGaugeStageButton.grid   ( in_ = controlframe, row = 13,
                                      sticky = (Tk.E,Tk.W) )
        #-------------------------------------------------------------
        
        self.canvas.get_tk_widget().grid ( column = 2, row = 2, 
                                           columnspan = 3, rowspan = 2,
                                           sticky = (Tk.N,Tk.S,Tk.W,Tk.E) )
    
        # For each widget in the mainframe, set some padding around
        # the widget to space things out and look better
        for child in mainframe.winfo_children():
            child.grid_configure( padx = 2, pady = 2 )

        # Add a Sizegrip to make resizing easier.
        #ttk.Sizegrip( mainframe ).grid( column = 99, row = 99, 
        #                                sticky = (Tk.N,Tk.S,Tk.E,Tk.W))

        # Setup the resize control with the 'grid' geometry manager. 
        # Every column and row has a "weight" grid option associated with it, 
        # which tells it how much it should grow if there is extra room in 
        # the master to fill. By default, the weight of each column or row 
        # is 0, meaning don't expand to fill space. Here we set the weight
        # to 1 telling the widget to expand and fill space as the window 
        # is resized. 
        # Make Sure to set on the root window!!!
        self.Tk_root.columnconfigure( 0, weight = 1 )
        self.Tk_root.rowconfigure   ( 0, weight = 1 )

        mainframe.columnconfigure( 0, weight = 0 )
        mainframe.columnconfigure( 1, weight = 0 )
        mainframe.columnconfigure( 2, weight = 1 )
        #mainframe.columnconfigure( 3, weight = 1 )
        #mainframe.columnconfigure( 4, weight = 1 )

        mainframe.rowconfigure   ( 0, weight = 1 )
        mainframe.rowconfigure   ( 1, weight = 0 )
        mainframe.rowconfigure   ( 2, weight = 1 ) 
        mainframe.rowconfigure   ( 3, weight = 1 )
        
        # MapPlotVarUpdate() will refresh the legend on mapPlotVariable changes
        self.mapPlotVariable.trace( 'w', self.MapPlotVarUpdate )

        self.RenderShoals( init = True )
        self.PlotLegend()
        self.canvas.show()

    #------------------------------------------------------------------
    #
    #------------------------------------------------------------------
    def Message ( self, msg ) :
        '''Display message in msgText box or on console, log to run_info.'''
        if not self.model.args.noGUI :
            self.msgText.insert( Tk.END, msg )
            self.msgText.see   ( Tk.END )
        else :
            print( msg )

        self.model.run_info.append( msg )

    #------------------------------------------------------------------
    #
    #------------------------------------------------------------------
    def MapPlotVarUpdate ( self, *args ) :
        '''User has changed mapPlotVariable, update the legend.'''
        if self.model.args.DEBUG_ALL :
            print( '-> MapPlotVarUpdate: ', args[0], ', ', args[2] )

        self.PlotLegend()
        self.canvas.show()

    #-----------------------------------------------------------
    #
    #-----------------------------------------------------------
    def InitPlotVars( self ):
        '''Create map of plotVariables and Tk.IntVar() to associate
        with the checkButtons accessed in GetRecordVariables(). These
        Tk.IntVars are held in the plotVar_IntVars map, and read in
        SetRecordVariables() to determine which variables will be
        recorded into the basin.plot_variables maps for eventual
        plotting and archiving'''

        if self.model.args.DEBUG_ALL :
            print( '-> InitPlotVars' )

        self.plotVar_IntVars.clear()

        for plotVariable in constants.BasinPlotVariable :
            if not self.model.args.noGUI :
                self.plotVar_IntVars[ plotVariable ] = Tk.IntVar()
            else :
                # Use the IntVar() class defined below
                self.plotVar_IntVars[ plotVariable ] = IntVar()

        # Set Salinity, Stage, Flow, Volume, Rain, ET as defaults
        self.plotVar_IntVars[ 'Salinity'    ].set( 1 )
        self.plotVar_IntVars[ 'Stage'       ].set( 1 )
        self.plotVar_IntVars[ 'Flow'        ].set( 1 )
        self.plotVar_IntVars[ 'Volume'      ].set( 1 )
        self.plotVar_IntVars[ 'Rain'        ].set( 1 )
        self.plotVar_IntVars[ 'Evaporation' ].set( 1 )
        self.plotVar_IntVars[ 'Runoff'      ].set( 1 )

        # Initialize the basin.plot_variables
        for plotVariable, intVar in self.plotVar_IntVars.items() :

            for basin in self.model.Basins.values() :
                basin.plot_variables.clear()

                if intVar.get() :
                    basin.plot_variables[ plotVariable ] = []

    #-----------------------------------------------------------
    #
    #-----------------------------------------------------------
    def GetRecordVariables( self ):
        '''Pop up checkbuttons to select basin variables to record'''

        if self.model.args.DEBUG_ALL :
            print( '-> GetRecordVariables' )

        #-------------------------------------------------------
        # A top level pop up widget
        top = Tk.Toplevel()
        top.wm_title( 'Variables' )
        top.minsize( width = 150, height = 100 )

        top.grid()

        setButton = ttk.Button( top, text = "Set",
                                style = 'BAM.TButton',
                                command = self.SetRecordVariables )

        closeButton = ttk.Button( top, text = "Close",
                                  style = 'BAM.TButton',
                                  command = lambda: top.destroy() )

        checkButtons = odict()

        for plotVariable in constants.BasinPlotVariable :
            checkButtons[ plotVariable ] = \
                ttk.Checkbutton( top, text = plotVariable,
                                 style = 'BAM.TCheckbutton',
                                 variable = self.plotVar_IntVars[plotVariable])

        for checkButton in checkButtons.values() :
            checkButton.grid( sticky = Tk.W, 
                              padx = 30, pady = 3 )

        setButton.grid  ( padx = 15, pady = 2 )
        closeButton.grid( padx = 15, pady = 2 )

    #-----------------------------------------------------------
    #
    #-----------------------------------------------------------
    def SetRecordVariables( self ):
        '''Callback method for Set button in GetRecordVariables().
        Sets the basin.plot_variables entries based on the selected
        plotVariable checkboxes in GetRecordVariables()'''

        if self.model.args.DEBUG_ALL :
            print( '-> SetRecordVariables' )
            for plotVariable, intVar in self.plotVar_IntVars.items() :
                print( plotVariable, ' : ', intVar, '=', intVar.get() )
        
        # Reset time and basins
        InitTimeBasins( self.model )
        msg ='*** All records erased, time reset to start time, basins reset.\n'
        self.Message( msg )

        for plotVariable, intVar in self.plotVar_IntVars.items() :

            for basin in self.model.Basins.values() :
                basin.plot_variables.clear()

                if intVar.get() :
                    basin.plot_variables[ plotVariable ] = []

    #----------------------------------------------------------------
    # 
    #----------------------------------------------------------------
    def PlotRunData( self ) :
        '''Plot data for selected basins from the current simulation.'''

        if self.model.args.DEBUG_ALL :
            print( '-> PlotRunData', flush = True )

        # Get a list of Basins from the Listbox
        BasinList = self.GetBasinListbox()

        if len( BasinList ) == 0 :
            msg = '\nPlotRunData: No basins are selected.\n'
            self.Message( msg )
            return

        # Get the plotVariable type from the plotOptionMenu
        plotVariable = self.plotVariable.get()

        # Get the data
        dataList   = []
        basinNames = []

        for Basin in BasinList :
            if plotVariable not in Basin.plot_variables.keys() :
                msg = '\nPlotRunData: ' + plotVariable + ' data ' +\
                      'is not present for basin ' + Basin.name + '.\n'
                self.Message( msg )
                return

            dataList.append( Basin.plot_variables[ plotVariable ] )
            basinNames.append( Basin.name )

        self.PlotData( self.model.times, dataList, basinNames, plotVariable,
                       period_record_days = self.model.simulation_days )

    #----------------------------------------------------------------
    # 
    #----------------------------------------------------------------
    def PlotArchiveData( self ) :
        '''Plot data from a previous run stored on disk.'''

        if self.model.args.DEBUG :
            print( '-> PlotArchiveData', flush = True )

        # Get a list of Basins from the Listbox
        BasinList = self.GetBasinListbox()

        if len( BasinList ) == 0 :
            msg = '\nPlotArchiveData: No basins are selected.\n'
            self.Message( msg )
            return

        self.last_plot_dir = self.plot_dir
        
        if self.model.args.DEBUG :
            print( self.plot_dir )

        # Get the data into 
        all_times  = []
        times      = []
        basinNames = []
        dataList   = []

        # Get the plotVariable type from the plotOptionMenu
        plotVariable = self.plotVariable.get()

        for Basin in BasinList :

            basinNames.append( Basin.name )

            # Read the basin .csv data to get [times] and [data]
            file_name = self.plot_dir + '/' + \
                        Basin.name + self.model.args.runID + '.csv'
            try :
                fd = open( file_name, 'r' )
            except OSError as err :
                msg = "\nPlotArchiveData: OS error: {0}\n".format( err )
                self.Message( msg )
                return

            rows = fd.readlines()
            fd.close()

            # Time,  Stage (m),  Flow (m^3/t),  Salinity (ppt),	Volume (m^3)
            # 2000-01-01 00:00:00,  0.0,    0.0,     37.0,	52475622.557
            # 2000-01-01 01:00:00, -0.0,    45.772,  37.0,	52459564.487
            variables = rows[ 0 ].split(',')
            for i in range( len( variables ) ) :
                variables[ i ] = variables[ i ].strip()

            # column index for Time
            time_col_i = variables.index( 'Time' )

            # column index for plotVariable
            try :
                unit_str   = constants.PlotVariableUnit[ plotVariable ]
                data_col_i = variables.index( plotVariable + ' ' + unit_str )

            except ValueError as err :
                msg = "\nPlotArchiveData: {0}\n".format( err )
                self.Message( msg )
                return

            # Get all times in file from first Basin in BasinList
            if Basin == BasinList[ 0 ] :
                for i in range( 1, len( rows ) ) :
                    words  = rows[ i ].split(',')
                    time_i = datetime.strptime( words[ time_col_i ].strip(),
                                                '%Y-%m-%d %H:%M:%S' )
                    all_times.append( time_i )

                # Find index in dates for start_time & end_time
                start_i, end_i = GetTimeIndex( plotVariable, all_times,
                                               self.model.start_time, 
                                               self.model.end_time )

            # Populate only data needed for the simulation timeframe
            times = all_times[ start_i : end_i + 1 ]
            data  = []
            for i in range( start_i, end_i + 1 ) :
                row   = rows[ i + 1 ]
                words = row.split(',')

                value_string = words[ data_col_i ]

                if 'NA' in value_string :
                    data.append( npNaN )
                else :
                    data.append( float( value_string ) )

            # If data is all NA don't plot
            if npall( isnan( data ) ) :
                msg = "\nPlotArchiveData: " + plotVariable + ' for basin ' +\
                      Basin.name + ' does not exist.\n'
                self.Message( msg )
            else :
                dataList.append( data )

        period_record = times[ len( times ) - 1 ] - times[ 0 ] # timedelta

        self.PlotData( times, dataList, basinNames, plotVariable,
                       period_record_days = period_record.days,
                       path = ' from: ' + self.plot_dir )

    #----------------------------------------------------------------
    # 
    #----------------------------------------------------------------
    def PlotGaugeSalinityData( self ) :
        '''Plot salinity data from gauge observations.'''

        if self.model.args.DEBUG :
            print( '-> PlotGaugeSalinityData', flush = True )

        BasinList = self.GetBasinListbox()

        if len( BasinList ) == 0 :
            msg = '\nPlotGaugeSalinityData: No basins are selected.\n'
            self.Message( msg )
            return

        basin_names = [ Basin.name for Basin in BasinList ]

        # Read the salinity .csv gauge data to get [times] and [data]
        if not self.model.salinity_data :
            GetBasinSalinityData( self.model )

        # plotVariables are salinity stations IDs : 'MD', 'GB'...
        plotVariables = []
        for Basin in BasinList :
            if Basin.salinity_station :
                plotVariables.append( Basin.salinity_station )

        # Get times[] from model.salinity_data.keys()
        times = [ datetime( year  = key_tuple[0], 
                            month = key_tuple[1], 
                            day   = key_tuple[2] )
                  for key_tuple in self.model.salinity_data.keys() ]

        # Get data
        dataList = []
        for plotVariable in plotVariables :
            data = []
            for key in self.model.salinity_data.keys() :
                data.append( self.model.salinity_data[key][plotVariable] )
            dataList.append( data )

        if not dataList :
            msg = 'No salinity gauge data for these basins.\n'
            self.Message( msg )
            return

        period_record = times[ -1 ] - times[ 0 ] # timedelta

        self.PlotData( times, dataList,
                       basinNames         = basin_names,
                       plotVariable       = 'Salinity',
                       period_record_days = period_record.days,
                       title              = 'Gauge: ',
                       path  = ' from: ' + self.model.args.salinityFile )


    #----------------------------------------------------------------
    # 
    #----------------------------------------------------------------
    def PlotGaugeStageData( self ) :
        '''Plot stage data from gauge observations.'''

        if self.model.args.DEBUG :
            print( '-> PlotGaugeStageData', flush = True )

        BasinList = self.GetBasinListbox()

        if len( BasinList ) == 0 :
            msg = '\nPlotGaugeStageData: No basins are selected.\n'
            self.Message( msg )
            return

        basin_names = [ Basin.name for Basin in BasinList ]

        # Read the stage .csv gauge data to get [times] and [data]
        if not self.model.stage_data :
            GetBasinStageData( self.model )

        # plotVariables are stations IDs : 'MD', 'GB'...
        # which are the same as the salinity_station
        plotVariables = []
        for Basin in BasinList :
            if Basin.salinity_station :
                plotVariables.append( Basin.salinity_station )

        # Get times[] from model.salinity_data.keys()
        times = [ datetime( year  = key_tuple[0], 
                            month = key_tuple[1], 
                            day   = key_tuple[2] )
                  for key_tuple in self.model.stage_data.keys() ]

        # Get data
        dataList = []
        for plotVariable in plotVariables :
            data = []
            for key in self.model.stage_data.keys() :
                try :
                    data.append( self.model.stage_data[ key ][ plotVariable ] )
                except KeyError : 
                    msg = 'No stage gauge data for ' + plotVariable + '.\n'
                    self.Message( msg )
                    break

            if data :
                dataList.append( data )

        if not dataList :
            msg = 'No stage gauge data for these basins.\n'
            self.Message( msg )
            return

        period_record = times[ -1 ] - times[ 0 ] # timedelta

        self.PlotData( times, dataList,
                       basinNames         = basin_names,
                       plotVariable       = 'Stage',
                       period_record_days = period_record.days,
                       title              = 'Gauge: ',
                       path  = ' from: ' + self.model.args.basinStage )

    #----------------------------------------------------------------
    # 
    #----------------------------------------------------------------
    def PlotData( self, time, dataList, basinNames, plotVariable, 
                  period_record_days, title = 'Basins: ', path = '' ) :
        ''' '''

        if self.model.args.DEBUG_ALL :
            print( '-> PlotData', flush = True )

            for Basin in BasinList :
                print( '\t', Basin.name, '\t: ', plotVariable )

        if not len( dataList ) or not len( time ):
            return

        #-------------------------------------------------------
        # A top level pop up widget
        top = Tk.Toplevel()
        top.wm_title( title + plotVariable + path )

        colors = iter( cm.rainbow( linspace( 0, 1, len( dataList ) ) ) )
        color  = next( colors )

        figure = Figure( figsize = ( 8, 5 ), dpi = 100 )
        axes   = figure.add_subplot( 111 )

        axes.plot( time, dataList[ 0 ], label = basinNames[ 0 ],
                   linewidth = 2, color = color )

        for i in range( 1, len( dataList ) ) :
            color  = next( colors )
            axes.plot( time, dataList[ i ], 
                       label = basinNames[ i ],
                       linewidth = 2, color = color )

        axes.set_xlabel( 'Date' )
        axes.set_ylabel( plotVariable + ' ' +\
                         constants.PlotVariableUnit[ plotVariable ] )
        axes.fmt_xdata = DateFormatter('%Y-%m-%d')
        
        # matplotlib does not default ticks well... arghhh
        if period_record_days < 15 :
            axes.xaxis.set_major_locator  ( DayLocator() )
            axes.xaxis.set_major_formatter( DateFormatter('%d') )

        elif period_record_days < 91 :
            axes.xaxis.set_major_locator  ( MonthLocator() )
            axes.xaxis.set_major_formatter( DateFormatter('%m-%d') )
            axes.xaxis.set_minor_locator  ( DayLocator(bymonthday=[7,14,21]))
            axes.xaxis.set_minor_formatter( DateFormatter('%d') )

        elif period_record_days < 181 :
            axes.xaxis.set_major_locator  ( MonthLocator() )
            axes.xaxis.set_major_formatter( DateFormatter('%b-%d') )
            axes.xaxis.set_minor_locator  ( DayLocator(bymonthday=[15]))
            axes.xaxis.set_minor_formatter( DateFormatter('%d') )

        elif period_record_days < 366 :
            axes.xaxis.set_major_locator  ( MonthLocator() )
            axes.xaxis.set_major_formatter( DateFormatter('%b') )

        elif period_record_days < 731 :
            axes.xaxis.set_major_locator  ( YearLocator() )
            axes.xaxis.set_major_formatter( DateFormatter('%Y') )
            axes.xaxis.set_minor_locator  ( MonthLocator(bymonth=[3,5,7,9,11]))
            axes.xaxis.set_minor_formatter( DateFormatter('%b') )

        elif period_record_days < 1826 :
            axes.xaxis.set_major_locator  ( YearLocator() )
            axes.xaxis.set_major_formatter( DateFormatter('%Y') )
            axes.xaxis.set_minor_locator  ( MonthLocator(bymonth=[7]) )
            axes.xaxis.set_minor_formatter( DateFormatter('%b') )

        else :
            axes.xaxis.set_major_locator  ( YearLocator() )
            axes.xaxis.set_major_formatter( DateFormatter('%Y') )

        legend = axes.legend( loc = 'upper center', fontsize = 9,
                              frameon = False, labelspacing = None )

        #figure.autofmt_xdate( bottom = 0.2, rotation = 90 )
        figure.set_tight_layout( True ) # tight_layout()

        # Tk.DrawingArea
        canvas = FigureCanvasTkAgg( figure, master = top )

        try :
            canvas.show()
        except RuntimeError as err :
            msg = "\nPlotData: {0}. \n".format( err ) +\
                  " Try setting the start/end time to cover the data record.\n"
            self.Message( msg )
            top.destroy()
            return

        canvas.get_tk_widget().pack( side = Tk.TOP, fill = Tk.BOTH, 
                                     expand = True )

        toolbar = NavigationToolbar2TkAgg( canvas, top )
        toolbar.update()
        canvas._tkcanvas.pack( side = Tk.TOP, fill = Tk.BOTH, expand = True )

    #----------------------------------------------------------------
    # 
    #----------------------------------------------------------------
    def RenderBasins( self, init = False ):
        ''' '''

        for Basin in self.model.Basins.values() :

            if Basin.boundary_basin :
                continue

            basin_xy = Basin.basin_xy

            if basin_xy is None :
                continue

            basin_name = Basin.name

            if init :
                # Initialize Basin.color with salinity color
                Basin.SetBasinMapColor( 'Salinity', 
                                        self.model.args.salinity_legend_bounds )
                
                if not Basin.Axes_fill : 
                    PolygonList = self.figure_axes.fill( 
                        basin_xy[:,0], basin_xy[:,1], 
                        fc     = Basin.color, 
                        ec     = 'white', 
                        zorder = -1, 
                        picker = True,
                        label  = basin_name ) # NOTE: this is a list...!

                    Basin.Axes_fill = PolygonList[ 0 ] 

            else :
                # Don't call fill() again if not init, it creates a new Polygon
                Basin.Axes_fill.set_color( Basin.color )

    #----------------------------------------------------------------
    # 
    #----------------------------------------------------------------
    def RenderShoals( self, init = False ):
        ''' '''

        for Shoal in self.model.Shoals.values():
            line_xy = Shoal.line_xy

            if line_xy is None :
                continue

            shoal_number = Shoal.name

            if init :
                Line2D_List = self.figure_axes.plot( line_xy[:,0], 
                                                     line_xy[:,1], 
                                                     #color, 
                                                     linewidth = 3,
                                                     label     = shoal_number,
                                                     picker    = True )

                Shoal.Axes_plot = Line2D_List[ 0 ]

            else :
                Shoal.Axes_plot.set_color( (1, 1, 1) )
                
    #----------------------------------------------------------------
    # 
    #----------------------------------------------------------------
    def PlotLegend( self, init = True ) :
        ''' '''

        if self.model.args.DEBUG_ALL:
            print( '-> PlotLegend', flush = True )

        # Add an axes at position rect [left, bottom, width, height] 
        # where all quantities are in fractions of figure width and height.
        # Just returns the existing axis if it already exists
        legendAxis = self.figure.add_axes( [ 0.05, 0.95, 0.7, 0.03 ] )

        legend_color_map = ListedColormap( self.colors )

        #-----------------------------------------------------------
        # Set appropriate legend and data type for map plot
        plotVariable = self.mapPlotVariable.get()

        legend_bounds = None
        legend_label  = None

        if plotVariable == 'Salinity' :
            legend_bounds = self.model.args.salinity_legend_bounds
            legend_label  = 'Salinity (ppt)'

        elif plotVariable == 'Stage' : 
            legend_bounds = self.model.args.stage_legend_bounds
            legend_label  = 'Stage (m)'

        elif plotVariable == 'Temperature' or plotVariable == 'Phosphate' or \
             plotVariable == 'Nitrate'     or plotVariable == 'Ammonium'  or \
             plotVariable == 'Oxygen'      or plotVariable == 'TOC' :
            
            msg = '\nInvalid map legend variable selected, showing Stage.\n'
            self.Message( msg )
            legend_label  = 'Stage (m)'
            legend_bounds = self.model.args.stage_legend_bounds

        else :
            msg = '\nError.  Failed to find map legend type, showing Stage.\n'
            self.Message( msg )
            legend_label  = 'Stage (m)'
            legend_bounds = self.model.args.stage_legend_bounds
        #-----------------------------------------------------------

        norm = BoundaryNorm( legend_bounds, legend_color_map.N )

        if init :
            self.colorbar = ColorbarBase( 
                legendAxis, 
                cmap         = legend_color_map,
                norm         = norm,
                ticklocation = 'bottom',
                ticks        = legend_bounds,
                #boundaries   = legend_bounds,
                spacing      = 'proportional', #'uniform',
                orientation  = 'horizontal' )
        else:
            self.colorbar.set_norm( norm )
            self.colorbar.update_ticks( legend_bounds )
        
        self.colorbar.set_label( legend_label, size = 12 )
        self.colorbar.ax.tick_params( labelsize = 10 )

    #----------------------------------------------------------------
    # 
    #----------------------------------------------------------------
    def MouseClick( self, event ):
        '''For event.mouseevent see: 
        http://matplotlib.org/api/backend_bases_api.html
        #matplotlib.backend_bases.MouseEvent'''

        if self.model.args.DEBUG_ALL:
            print( '-> MouseClick' )
            print( 'event.mouseevent: ',        event.mouseevent )
            print( 'event.mouseevent.button: ', event.mouseevent.button )
            print( 'event.artist: ',            event.artist     )

        left_click   = False
        middle_click = False
        right_click  = False

        BasinObj = None

        if   event.mouseevent.button == 1 :
            left_click   = True
        elif event.mouseevent.button == 2 :
            middle_click = True
        elif event.mouseevent.button == 3 :
            right_click  = True

        #--------------------------------------------------------
        # Left Click selects an object, either Basin or Shoal
        # and prints its info
        if left_click :

            # Shoals are instantiated as Line2D 
            if isinstance( event.artist, Line2D ):
                line = event.artist

                # find the Shoal object
                for shoal_number, Shoal in self.model.Shoals.items() :
                    if Shoal.Axes_plot == None :
                        continue

                    if Shoal.Axes_plot.get_label == line.get_label :

                        Shoal.Print( shoal_number )
                        break

            # Basins are instantiated as Polygon
            elif isinstance( event.artist, Polygon ):
                patch = event.artist

                # Find the Basin object
                Basin = None
                for Basin in self.model.Basins.values() :
                    if Basin.Axes_fill == None :
                        continue
                    
                    if Basin.Axes_fill.get_label() == patch.get_label() :
                        Basin.Print()
                        break

                # Select this basin in the basinListBox
                self.basinListBox.selection_clear( first = 1, 
                               last = max( self.basinListBoxMap.values() ) )

                self.basinListBox.selection_set( 
                    self.basinListBoxMap[ Basin.name ] )

                self.basinListBox.see( self.basinListBoxMap[ Basin.name ] )

        #--------------------------------------------------------
        # Middle Click selects a Basin and prints it's info
        elif middle_click :

            # Basins are instantiated as Polygon
            if isinstance( event.artist, Polygon ):
                patch = event.artist

                # Find the Basin object
                for Basin in self.model.Basins.values() :
                    if Basin.Axes_fill == None :
                        continue
                    
                    if Basin.Axes_fill.get_label() == patch.get_label() :
                        Basin.Print()
                        break

        #--------------------------------------------------------
        # Right Click selects a Basin and pops up its Shoal list
        # Selecting a listbox item prints the shoal information
        elif right_click :

            # Basins are instantiated as Polygon
            if isinstance( event.artist, Polygon ):
                patch = event.artist

                # Find the Basin object
                for Basin in self.model.Basins.values() :
                    if Basin.Axes_fill == None :
                        continue
                    
                    if Basin.Axes_fill.get_label() == patch.get_label() :

                        BasinObj = Basin

                        if self.model.args.DEBUG_ALL :
                            print( '<<<< Basin Right Click:', 
                                   Basin.name, ' Shoals:', Basin.shoal_nums,
                                   '>>>>', flush = True )
                        break

            if BasinObj :
                # A top level pop up widget
                top = Tk.Toplevel()
                top.title( BasinObj.name + ' Shoals' ) 

                # Shoal Listbox
                self.shoalListBox = Tk.Listbox( top, height = 11, width = 30, 
                                                selectmode = Tk.EXTENDED,
                                                font = constants.textFont )

                # Insert shoal numbers into the Listbox
                # The listvariable = [] option won't work if
                # there is whitespace in a name, so insert them manually
                i = 1
                for shoal_number in BasinObj.shoal_nums :
                    Basin_A_key = self.model.Shoals[ shoal_number ].Basin_A_key
                    Basin_B_key = self.model.Shoals[ shoal_number ].Basin_B_key

                    shoalInfo = str( shoal_number ) + '   ' +\
                        self.model.Basins[ Basin_A_key ].name + ' : ' +\
                        self.model.Basins[ Basin_B_key ].name
                        
                    self.shoalListBox.insert( i, shoalInfo )
                    i = i + 1

                # Create a vertical scroll bar for the Listbox
                # Call the Listbox yview func when the user moves the scrollbar
                scrollBar = ttk.Scrollbar( top, orient = Tk.VERTICAL, 
                                           command = self.shoalListBox.yview )

                # Tell the Listbox it will scroll according to the scrollBar
                self.shoalListBox.configure( yscrollcommand = scrollBar.set )

                # Colorize alternating lines of the listbox
                for i in range( 0, len( BasinObj.shoal_nums ), 2):
                    self.shoalListBox.itemconfigure( i, background = '#f0f0ff' )

                # Can use pack here since this is a standalone widget that
                # doesn't interact with a grid geometry
                scrollBar.pack( side = Tk.LEFT, expand = True, fill = Tk.Y )
                self.shoalListBox.pack( side = Tk.RIGHT, expand = True, 
                                        fill = Tk.BOTH )

                # Tell Listbox to call ProcessShoalListbox()
                self.shoalListBox.bind( '<<ListboxSelect>>', 
                                        self.ProcessShoalListbox )

    #----------------------------------------------------------------
    # 
    #----------------------------------------------------------------
    def ProcessShoalListbox( self, *args ):
        '''Read the Shoal listbox selection, Print the Shoal info.'''
        # \n separated items in one string
        selected = self.shoalListBox.selection_get()

        shoal_list = selected.split( '\n' ) # A list of strings

        if self.model.args.DEBUG_ALL:
            print( '-> ProcessShoalListbox() ', len( shoal_list ), '\n',
                   shoal_list, flush = True )

        # Find the Shoal objects and store in Shoal_list
        Shoal_list = []
        for shoal_info in shoal_list :
            words = shoal_info.split()
            shoal_number = int( words[ 0 ] )
            Shoal = self.model.Shoals[ shoal_number ]
            Shoal_list.append( Shoal )
            Shoal.Print( shoal_number )

        # return Shoal_list

    #----------------------------------------------------------------
    # 
    #----------------------------------------------------------------
    def ProcessBasinListbox( self, *args ):
        '''Print the Basin listbox selections'''
        Basin_list = self.GetBasinListbox()
        
        for Basin in Basin_list :
            Basin.Print()

    #----------------------------------------------------------------
    # 
    #----------------------------------------------------------------
    def GetBasinListbox( self ):
        '''Read the Basin listbox selection.
        Return a list of Basin objects.'''

        # Get the names of selected basins
        # \n separated items in one string
        try :
            selected = self.basinListBox.selection_get()
        except Tk._tkinter.TclError :
            # Nothing is selected
            return []

        basin_name_list = selected.split( '\n' ) # A list of strings

        if self.model.args.DEBUG_ALL :
            print( '-> GetBasinListbox() ', len( basin_name_list ), '\n',
                   basin_name_list, flush = True )

        # Find the Basin objects and store in Basin_list
        Basin_list = []
        for basin_name in basin_name_list :
            for Basin in self.model.Basins.values() :
                # Since the Basins keys are basin numbers, match the names
                if Basin.name == basin_name :
                    Basin_list.append( Basin )

        return Basin_list

    #-----------------------------------------------------------
    #
    #-----------------------------------------------------------
    def ShowAboutInfo( self ):
        messagebox.showinfo( message = self.model.Version )

    #-----------------------------------------------------------
    #
    #-----------------------------------------------------------
    def OpenInitFile( self ):
        '''Open a basin initialization file and call InitTimeBasin.'''
        if self.model.args.DEBUG_ALL :
            print( '-> OpenInitFile(): ', flush = True ) 

        input_file = filedialog.askopenfilename(
            initialdir  = self.model.args.path + 'data/init/',
            initialfile = 'Basin_Initial_Values.csv', 
            filetypes   = [('Basin Init Files', '*.csv')],
            multiple    = False,
            title       = 'Basin Initialization File' )

        if not input_file :
            return

        # Since we store the path and files seperately, but input_file
        # contains the whole path, strip off the model base path.
        # Since askopenfilename returns the entire path that may not
        # have the same prefix specified in args.path (since args.path
        # may be referring to a symbolic link), strip off everything
        # prior to data/init  : this is stupid since it now requires
        # this file to reside in data/init... 
        input_file = input_file[ input_file.rfind( 'data/init/' ) : ]
        
        self.model.args.basinInit = input_file

        InitTimeBasins( self.model )

    #-----------------------------------------------------------
    #
    #-----------------------------------------------------------
    def EditFile( self ):
        '''Edit a file with the current editor.'''
        if self.model.args.DEBUG_ALL:
            print( '-> EditFile(): ', flush = True ) 

        edit_file = filedialog.askopenfilename(
            initialdir  = self.model.args.path,
            # initialfile = '', 
            filetypes = [ ('Data',   '*.csv'), 
                          ('Source', '*.py' ),
                          ('R',      '*.R'  ),
                          ('All',    '*'    ) ],
            multiple  = False )

        if not edit_file :
            return

        cmdLine = self.model.args.editor + ' ' + edit_file.replace(' ', '\ ')

        try :
            sp = Popen( cmdLine, shell = True )
        except OSError as err:
            msg = "\nEditFile: OS error: {0}\n".format( err )
            self.Message( msg )
        except ValueError as err:
            msg = "\nEditFile: Value error: {0}\n".format( err )
            self.Message( msg )
        except:
            errMsg = "\nEditFile Error:" + sys.exc_info()[0] + '\n.'
            self.Message( msg )
            raise Exception( errMsg )

    #-----------------------------------------------------------
    #
    #-----------------------------------------------------------
    def GetPlotDir( self ):
        '''Set the directory for disk/archive plots.'''
        if self.model.args.DEBUG_ALL :
            print( '-> (): GetPlotDir', flush = True ) 

        # Tk.filedialog.askdirectory clears the listbox selection, save it
        BasinList = self.GetBasinListbox()

        if path_exists( self.last_plot_dir ) :
            initial_plot_dir = self.last_plot_dir
        else :
            initial_plot_dir = self.model.args.homeDir

        # Get the file path and runid
        archive_dir = filedialog.askdirectory(
            initialdir  = initial_plot_dir,
            title       = 'Plot Archive Directory',
            mustexist   = True )

        # Reset the listbox selection
        for Basin in BasinList :
            self.basinListBox.selection_set(self.basinListBoxMap[ Basin.name ])

        if not archive_dir :
            return

        self.plot_dir = archive_dir

    #-----------------------------------------------------------
    #
    #-----------------------------------------------------------
    def GetOutputDir( self ):
        '''Set the directory for basin output files.'''
        if self.model.args.DEBUG_ALL :
            print( '-> (): GetOutputDir', flush = True ) 

        # Tk.filedialog.askdirectory clears the listbox selection, save it
        BasinList = self.GetBasinListbox()

        if path_exists( self.model.args.basinOutputDir ) :
            initial_out_dir = self.model.args.basinOutputDir
        else :
            initial_out_dir = self.model.args.homeDir

        # Get the file path and runid
        output_dir = filedialog.askdirectory(
            initialdir  = initial_out_dir,
            title       = 'Basin Output Directory',
            mustexist   = False )

        # Reset the listbox selection
        for Basin in BasinList :
            self.basinListBox.selection_set(self.basinListBoxMap[ Basin.name ])

        if not output_dir :
            return

        self.model.args.basinOutputDir = output_dir

        self.Message( 'Set basin output directory to: ' +\
                      self.model.args.basinOutputDir + '\n' )

    #-----------------------------------------------------------
    #
    #-----------------------------------------------------------
    def CheckTimeEntry( self, newTime, widgetName ):
        '''Validate the time entry for an update to start_time or end_time.
        Times must be on hour boundaries (zero minutes) since the tidal
        data is aligned on the hour.'''

        if self.model.args.DEBUG_ALL :
            print( '-> CheckTimeEntry(): ', newTime, flush = True ) 

        try :
            if ':' in newTime :
                format_string = '%Y-%m-%d %H:%M'
            else :
                format_string = '%Y-%m-%d'

            time = datetime.strptime( newTime, format_string )

        except ValueError :
            # Reset text to original values, return False
            if widgetName == str( self.startTimeEntry ) :
                start_text = \
                    str( self.model.start_time.strftime( '%Y-%m-%d %H:%M' ) )
                self.start_text.set( start_text )

            elif widgetName == str( self.endTimeEntry ) :
                end_text = str(self.model.end_time.strftime( '%Y-%m-%d %H:%M' ))
                self.end_text.set( end_text )

            return False

        # Align the time to an hour boundary
        time = time - timedelta(minutes = time.minute, seconds = time.second)

        # Save both initial times so comparison in InitTimeBasins is valid
        self.model.previous_start_time = self.model.start_time
        self.model.previous_end_time   = self.model.end_time

        if widgetName == str( self.startTimeEntry ) :
            start_text = str( time.strftime( '%Y-%m-%d %H:%M' ) )
            self.start_text.set( start_text )
            self.model.start_time = time

        elif widgetName == str( self.endTimeEntry ) :
            end_text = str( time.strftime( '%Y-%m-%d %H:%M' ) )
            self.end_text.set( end_text )
            self.model.end_time = time

        InitTimeBasins( self.model )

        if self.model.args.DEBUG_ALL :
            print( '   New time: ', str( time ), flush = True ) 

        return True

#---------------------------------------------------------------
# 
#---------------------------------------------------------------
class IntVar :
      '''Surrogate for Tk.IntVar() when non-GUI option invoked.
    Provides set() and get() methods.'''

      def __init__( self, value = 0 ):
          self.value = value

      def set( self, value ) :
          self.value = value

      def get( self ) :
          return self.value
