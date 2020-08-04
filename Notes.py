'''Developer and general notes for the Bay Assessment Model (BAM)'''

#------------------------------------------------------------------
#------------------------------------------------------------------
def Versions() :
    '''
    Version 1.4.1 2020-8-4
      Update to Matplotlib 3.1.
      canvas.draw() cannot be called from thread outside Tk mainloop. 

    Version 1.4 2018-6-29
      Update to Matplotlib 2.2.

    Version 1.3 2018-2-7
      Add coastal basin max surface water temperature timeseries (-st).

      Add ET 'amplification' from increased thermodynamic (kinetic)
      equilibrium vapor pressure to specified basins (-ea).

      Add model.VaporPressureRatio() method and reference temperature (-rt).

      Replace "Salt Factor" in Basin_Parameters.csv file with "ET Amplify".

    Version 1.2 2017-11-12
      Update data period of record to 1999-9-1 : 2016-12-31

      Add Pause and Stop buttons to pause and exit the simulation loop.

    Version 1.1 2017-3-27
      Replaced multiprocess module (dill based serializer) with
      standard Python multiprocessing module.

      Moved model simulation loop from Run() into ModelLoop()
      that can be run as a thread (-nT) allowing user interaction 
      with the gui during model simulation.

      Added non-gui option (-ng).

    Version 1.0 2016-4-18
      Initial release.
    '''
    pass

#------------------------------------------------------------------
#------------------------------------------------------------------
def Installation() :
    '''
    Installation (Debian/Ubuntu):

    apt install python3
    apt install python3-tk
    apt install tk-dev
    apt install libffi-dev  # for cairocffi/matplotlib.backends
    python3 -m pip install numpy
    python3 -m pip install scipy
    python3 -m pip install cairocffi  # for matplotlib.backends
    python3 -m pip install matplotlib
    python3 -m pip install pyshp      # github.com/GeospatialPython/pyshp
    '''
    pass

#------------------------------------------------------------------
#------------------------------------------------------------------
def ToDo() :
    '''
      -------------------------------------------------------------
      Wind dependence.
      Groundwater : include as Runoff?
      -------------------------------------------------------------
      Flush output files
      Plot archived data with run id
      Add I/O file list to RunInfo.txt
      Hardcoded boundary basins : read from config file
      Redo shapefile/init files to include new boundary basins
      Remove phantom shoals that don't connect basins
      Replace shoal hydro dictionaries with explicitly indexed numpy arrays?
      Replace numeric lists with pre-allocated numpy arrays?
      Add Help (Notes.py __doc__ etc...)
    '''
    pass

#------------------------------------------------------------------
#------------------------------------------------------------------
def Data() :
    '''
    Available data for boundary conditions.

Data     File                                          Start       End
===========================================================================
Rain     DailyRainFilled_cm_1999-9-1_2016-12-31.csv  1999-09-01  2016-12-31
ET       PET_1999-9-1_2016-12-31.cs                  1999-09-01  2016-12-31
Salinity DailySalinityFilled_1999-9-1_2016-12-31.csv 1999-09-01  2016-12-31
Tide     HourlyTide1990_2020.tar.gz (See [1])        1990-01-01  2021-01-01
Runoff   EDEN_Stage_OffsetMSL.csv                    1999-09-01  2017-06-30
Flow     S197_Flow_1999-9-1_2017-10-25.csv           1999-09-01  2017-10-25

[1] To speed up processing of tidal data initialization, tidal data can
    be subsets of this span, i.e. 2010-01-01 through 2016-01-01. See the
    (-bt, --basinTide) option and the associated init file. 
    '''
    pass

#------------------------------------------------------------------
#------------------------------------------------------------------
def Limitations() :
    '''
    This is a 'basin' model, not a finite element model. The physical basis
    is inter-basin Mannings flow over shoals with conservation of mass. 

    The simplified physical basis is problematic:

    1) No wave propagation : stage/volume changes are instantaneous.
    2) No diffusion/mixing : concentration equilibriums are instantaneous.
    3) Mannings flow over shoals that are deep or narrow is not justifiable.
    4) Water levels are not geodetic, but anomalies. 
    5) Sea surface gradients and geomorphic changes are ignored.

    Model representation of basins, shoals and forcings is incomplete:

    1) There are shoals with missing channels.
       The Keys are largely considered flow barriers, ignoring many channels.
    2) Evaporation is a single daily timeseries applied to the entire domain.
    3) Rainfall is a sparse set of daily timeseries. Single or multiple 
       gauges can be weighted, summed, and applied to a basin.
    '''
    pass

#------------------------------------------------------------------
#------------------------------------------------------------------
def General() :
    '''
    Basin parameters are initialized in the basinInit -bi file.

    Rain is taken from the nearest rain station, with the basin : gauge
    mapping defined in the basinParameter -bp file.  Salinities can be 
    fixed from the observed data (not simulated) with -gs for basins : gauges
    listed in the basinParameter -bp file. 

    To check mass balance turn off all normal inputs and 
    specify a fixed flow into Blue Bank with -fb of 1000 m^3/s, 
    t = 60 s timestep and all shoal mannings coefficients of 0.1 :

./bam.py -t 60 -E "2010-1-1 08:00" -nt -nm -ne -nr -nR -nb -fb -si 'n' -sm 0.1

    Blue Bank should then equilibriate over 8 hours to:

    Blue Bank : dt = 60 s
      Stage: 0.01 (m)
      Salinity: 17.76 (g/kg)
      Volume: 0.0425 (km^3)
      Shoal Flux: 1004.91 (m^3/s)

    For a more accurate rendition, run with -t 1 :
    Blue Bank : dt = 1 s
      Stage: 0.01 (m)
      Salinity: 17.77 (g/kg)
      Volume: 0.0425 (km^3)
      Shoal Flux: 1000.0 (m^3/s)

    See etc/Notes.txt for mass balance calculation verification. 

    If runtime is an issue, executing without the gui (-ng) 
    and without a separate thread (-nT) improves runtime. 

    BAM Simulation Times for 1999-9-1 : 2015-12-7
    ---------------------------------------------
    With gui         : 12.7 hours
    No gui (-ng -nT) :  7.8 hours
    '''
    pass

#------------------------------------------------------------------
#------------------------------------------------------------------
def Development() :
    '''
    Geospatial Python pyshp: Reads shape files for basins and shoals
    https://github.com/GeospatialPython/pyshp

    Can't use multiprocessing with class objects or graphics objects
    since it uses pickle to serialize communication objects, see
    the MultiprocessNotes()__doc__.

    Tk (Tkinter) and Tk themed widgets (ttk)
    https://docs.python.org/3/library/tkinter.html
    
    Note that a tkinter Tk() StringVar() can not be created
    until after the root widget is created: root = Tk.Tk()
    StringVar() has get() and set() methods for Label updates. 
    
    Modules to embed matplotlib figure in a Tkinter window
    http://matplotlib.org/examples/user_interfaces/embedding_in_tk.html

    Can't use the NavigationToolbar2TkAgg with grid since its' init
    function calls pack(), see:
    /usr/local/lib/python3.4/dist-packages/matplotlib/backends/backend_tkagg.py
    It would be nice to have on the map since it displays xy coordinates
    from mouse position. 

    Tkinter to tkinter (python2 to python3)
    -----------------------------------------
    Tkinter        → tkinter
    ttk            → tkinter.ttk
    tkMessageBox   → tkinter.messagebox
    tkColorChooser → tkinter.colorchooser
    tkFileDialog   → tkinter.filedialog
    tkCommonDialog → tkinter.commondialog
    tkSimpleDialog → tkinter.simpledialog
    tkFont         → tkinter.font
    Tkdnd          → tkinter.dnd
    ScrolledText   → tkinter.scrolledtext
    Tix            → tkinter.tix
    
    To inspect arguments of a module function:
    import inspect : inspect.getargspec( functionName )

    To profile the model:
    python3 -m cProfile -s time ./bam.py -nt > bam_profile.txt
    '''
    pass

#------------------------------------------------------------------
#------------------------------------------------------------------
def Multiprocessing() :
    '''
    Currently, multiprocessing.pool.Pool.map_async() is used to 
    parallelize reading and interpolation of tidal boundary data. 

    The Python multiprocessing module uses Pickle to serialize objects
    to/from the mutiprocesses, but some things can't be pickled. 
    Imo, this is a broken part of the OO Python implementation.
    So there is a kludge to work around this by isolating the objects
    and functions into pool_functions.py. 

    See:
    http://stackoverflow.com/questions/1816958/
           cant-pickle-type-instancemethod-when-using-pythons-
           multiprocessing-pool-ma?lq=1
    http://stackoverflow.com/questions/8804830/
           python-multiprocessing-pickling-error

    Note that a 'solution' proposed in the above threads is to use
    a fork of multiprocessing called multiprocess that uses the dill
    serializer instead of pickle. While this does handle a wider-range
    of objects, it doesn't work for embedded Tk objects. 

    To test use of multiprocess in general, the code was reorganzed 
    to remove class and graphics objects from the Shoal class, which
    required making the Basins and Shoals maps global, and was tested
    with multiprocessing parallelizing the shoal loop in 
    hydro.MassTransport and in hydro.ShoalVelocities.  The result was 
    significantly slower run times and exhaustion of memory resources
    since there are 410 shoals and the loops are not deep enough to 
    CPU-limit across processes.  Process-based parallelism with pools 
    is ill-posed for this application.
    '''

#------------------------------------------------------------------
#------------------------------------------------------------------
def Legacy() :
    '''
    FATHOM is not SI, but profusely mixes English and metric units... :-(
    BAM suffers this as well, but only in that dynamic boundary timeseries
    flow data (i.e. S197) are specified in cfs but converted to m^3/s in
    BoundaryConditions(). 
    
    Water levels are not geodetic, but are anomalies from the shoal depth.  
    This imposes all shoal depths of 0 are at the the same elevation.
    All tidal forcings are also anomalies from their respective means, 
    which lacks realism in variable sea level across the model domain. 

    This is likely a poor decision of convenience based on the bathymetric
    survey data with an assumed reference elevation of 0 ? 

    -----------------------------------------------------------------
    Incredible: a glimpse into the genius of poorly crafted fortran:

    MANY(LDAY,KK,JJ)=SCLX*MANX(MHI,KK,JJ)+SCLY*MANX(MLO,KK,JJ)
    MANY(LDAY,KK,JJ)=MANX(LMON,KK,JJ)
    XMNX=MANY(LDAY,NRGLN(JS,1),1)
    XN(JS)=GRAV2*WIDX(JS)*XMNX*XMNX
    DATA EXP43/1.3333333/
    FACT=10.**(ALOG10(XN(LS)) - EXP43*ALOG10(RAD))
     
    But do the gymnastics of trying to save a few cpu cycles
    warrant the log transforms and cryptic constants?  

    Also note the 3-dimensional arrays used to store state variables
    and configuration parameters, in fact, it appears that some arrays
    hold indices into other arrays... speechless.  And then there's
    the hardcoding of parameters such as basin and shoal depths.
    Not enough?  There is code duplication instead of functionalization,
    NO whitespace!!! A .bat masquerading as a makefile, a non-standard
    compiler, authors unresponsive to queries etc... 
    What would Tim Riley say?
    '''
    pass
