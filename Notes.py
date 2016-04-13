
#------------------------------------------------------------------
#------------------------------------------------------------------
def InstallationNotes() :
    '''
    Installation:

  sudo apt-get install python3
  sudo apt-get install python3-tk
  sudo apt-get install tk-dev
  sudo apt-get install libffi-dev  # for cairocffi/matplotlib.backends
  sudo apt-get install python3-pip
  sudo pip3    install cairocffi   # for matplotlib.backends
  sudo pip3    install numpy
  sudo pip3    install scipy
  sudo pip3    install matplotlib
  sudo pip3    install pyshp       # https://github.com/GeospatialPython/pyshp
  sudo pip3 install git+https://github.com/uqfoundation/dill.git@master
  sudo pip3 install git+https://github.com/uqfoundation/multiprocess.git@master
    '''
    pass

#------------------------------------------------------------------
#------------------------------------------------------------------
def DataNotes() :
    '''
    Available data for boundary conditions.

Data  File                                          Start       End
==========================================================================
Rain     DailyRainFilled_cm_1999-9-1_2015-12-8.csv  1999-09-01  2015-12-08
ET       PET_1999-9-1_2015-12-8.csv                 1999-09-01  2015-12-08
Salinity DailySalinityFilled_1999-9-1_2015-12-8.csv 1999-09-01  2015-12-08
Tide     HourlyTide1990_2020.tar.gz (See [1])       1990-01-01  2021-01-01
Runoff   EDEN_Stage_OffsetMSL.csv                   1999-09-01  2015-12-31

[1] To speed up processing of tidal data initialization, tidal data are
    subsets of this span, i.e. 2010-01-01 through 2016-01-01. 
    '''
    pass

#------------------------------------------------------------------
#------------------------------------------------------------------
def LimitationNotes() :
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
       gauges can be wieghted, summed, and applied to a basin.
    '''
    pass

#------------------------------------------------------------------
#------------------------------------------------------------------
def GeneralNotes() :
    '''
    To check mass balance turn off all normal inputs and 
    specify a fixed flow into Blue Bank with -bc, a 60 s timestep and
    all shoal mannings coefficients of 0.1 :

    ./bam.py -t 60 -nt -nm -ne -nr -nR -bc -si 'n' -sm 0.1

    Blue Bank should then equilibriate to:
     Stage: 0.03 (m)
     Salinity: 11.41 (g/kg)
     Volume: 0.0429 (km^3)
     Shoal Flux: 100130.59 (m^3/t)

    See etc/Notes.txt for mass balance calculation verification. 

    Basin parameters are initialized in the basinInit -bi file.

    Rain is taken from the nearest rain station, with the basin : gauge
    mapping defined in the basinParameter -bp file.  Salinities can be 
    fixed from the observed data, not simulated with -gs for basins : gauges
    listed in the basinParameter -bp file. 
    '''
    pass

#------------------------------------------------------------------
#------------------------------------------------------------------
def DevelopmentNotes() :
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
def MultiprocessNotes() :
    '''
    The Python multiprocessing module uses Pickle to serialize objects
    to/from the mutiprocesses, but some things can't be pickled. 
    Imo, this is a broken part of the OO Python implementation.
    To work around this, there is a user contributed fork of 
    multiprocessing named multiprocess which uses the dill 
    serialization module instead of pickle.  The multiprocess 
    module therefore allows class instances to be passed to/from
    the processes.

    This is useful since we return a scipy interpolation function
    from ReadTideBoundaryData() and multiprocessing can't. 

    However, even multiprocess doesn't handle Tk objects. So there
    is a kludge to work around this and functions have been 
    isolated into pool_functions.py.

    See:
    https://github.com/uqfoundation/multiprocess.git
    https://github.com/uqfoundation/dill.git
    http://stackoverflow.com/questions/1816958/
           cant-pickle-type-instancemethod-when-using-pythons-
           multiprocessing-pool-ma?lq=1
    http://stackoverflow.com/questions/19984152/
           what-can-multiprocessing-and-dill-do-together
    http://stackoverflow.com/questions/8804830/
           python-multiprocessing-pickling-error

    Currently, multiprocess is used to parallelize reading and 
    interpolation of tidal boundary data. 

    To test use of multiprocess in general, the code was reorganzed 
    to remove class and graphics objects from the Shoal class, which
    required making the Basins and Shoals maps global, and was tested
    with multiprocess and multiprocessing parallelizing the shoal
    loop in hydro.MassTransport and in hydro.ShoalVelocities. The 
    result was significantly slower run times and exhaustion of memory
    resources since there are 410 shoals and the loops are not deep
    enough to CPU-limit across processes.  Process-based parallelism 
    with pools is ill-posed for this application.
    '''

#------------------------------------------------------------------
#------------------------------------------------------------------
def LegacyNotes() :
    '''
    FATHOM is not SI, but mixes English and metric units... :-(
    
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
