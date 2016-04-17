
#---------------------------------------------------------------
# 
#---------------------------------------------------------------
class Shoal:
    """Variables for each of the 410 shoals in Florida Bay. 
    Fluxes across the shoal are signed, identifying the 'upstream'
    basin (A or B). Water level and concentration differences are gradients 
    between the adjacent basins. Velocities are given for each depth 
    on a shoal."""

    def __init__( self, model ):

        self.model = model

        # matplotlib Figure variables
        self.line_xy    = None  # Read from shapefile
        self.Axes_plot  = None  # Created by matplotlib plot() (Line2D)

        # Basins for this shoal
        self.Basin_A     = None # Basin object
        self.Basin_B     = None # Basin object
        self.Basin_A_key = None # Basin number : key in Basins map
        self.Basin_B_key = None # Basin number : key in Basins map

        # Physical variables
        # JP: All of these dictionaries share the same keys
        # Some efficiency might be gained with one dictionary using
        # depth_ft keys holding dictionaries with the { variable : values }
        self.velocity            = dict() # { depth(ft) : (m/s)  }
        self.wet_length          = dict() # { depth(ft) : (m)    }
        self.friction_factor     = dict() # { depth(ft) : factor }
        self.h_upstream          = dict() # { depth(ft) : (m)    }
        self.h_downstream        = dict() # { depth(ft) : (m)    }
        self.cross_section       = dict() # { depth(ft) : (m^2)  }
        self.hydraulic_radius    = dict() # { depth(ft) : (m)    }
        self.manning_coefficient = None   # 
        self.land_length         = None   # (m)
        self.width               = None   # (m)
        self.cross_section_total = 0      # (m^2)
        self.level_difference    = 0      # (m)
        self.no_flow             = False  # True if land with 0 shoal width
        self.initial_velocity    = False  # True 1st VelocityHydraulicRadius()

        # Volume transports
        self.flow_sign           = 0      # -1, 0, 1 : B -> A, None, A -> B
        self.Q                   = dict() # { depth(ft) : Q(m^3/s) }
        self.Q_total             = 0      # (m^3/s)
        self.volume_A_B          = 0      # (m^3/timestep)
        self.volume_B_A          = 0      # (m^3/timestep)
        self.volume_residual     = 0      # (m^3/timestep)
        self.volume_total        = 0      # (m^3/timestep)

        # Solute transports
        # self.solute_transport_A_B      = None   # (mol/time)
        # self.solute_transport_B_A      = None   # (mol/time)
        # self.solute_residual_transport = None   # (mol/time)
        # self.solute_total_transport    = None   # (mol/time)

    #-----------------------------------------------------------
    # 
    #-----------------------------------------------------------
    def Print( self, shoal_number = None, print_all = False ) :
        '''Display shoal info on the gui msgText box.'''
        
        Basin_A = self.Basin_A
        Basin_B = self.Basin_B

        shoalInfo = '\nShoal: ' + str( shoal_number ) + '  '      +\
            Basin_A.name + ' [' + str( self.Basin_A_key ) + '] '  +\
            str( round( Basin_A.water_level, 2 ) ) + ' (m)  to  ' +\
            Basin_B.name + ' [' + str( self.Basin_B_key ) + '] '  +\
            str( round( Basin_B.water_level, 2 ) ) + ' (m)]\n'

        shoalInfo = shoalInfo +\
            'Width: ' + str( self.width ) + ' (m)'               +\
            '  Manning: ' + str( self.manning_coefficient )      +\
            '  Land Length: ' + str( self.land_length ) + ' (m)'

        shoalInfo = shoalInfo + '\nh_upstream: '
        for depth, h in self.h_upstream.items() :
            shoalInfo = shoalInfo + str( depth ) + 'ft: ' +\
                        str( round( h, 3 ) ) + ' '
        shoalInfo = shoalInfo + '(m)'

        shoalInfo = shoalInfo + '\nh_downstream: '
        for depth, h in self.h_downstream.items() :
            shoalInfo = shoalInfo + str( depth ) + 'ft: ' +\
                        str( round( h, 3 ) ) + ' '
        shoalInfo = shoalInfo + '(m)'
        
        shoalInfo = shoalInfo + '\nVelocities: '
        for depth, velocity in self.velocity.items() :
            shoalInfo = shoalInfo + str( depth ) + 'ft: ' +\
                        str( round( velocity, 3 ) ) + ' '
        shoalInfo = shoalInfo + '(m/s)'

        shoalInfo = shoalInfo + '\nQ: '
        for depth, Q in self.Q.items() :
            shoalInfo = shoalInfo + str( depth ) + 'ft: ' +\
                        str( round( Q, 3 ) ) + ' '
        shoalInfo = shoalInfo + '(m^3/s)  Q_total: ' +\
            str( round( self.Q_total, 1 ) ) + ' (m^3/s)\n'

        if print_all :
            shoalInfo = shoalInfo + '\nWet Length: '
            for depth, length in self.wet_length.items() :
                shoalInfo = shoalInfo + str( int( depth ) ) + 'ft: ' +\
                            str( round( length ) ) + '  '
                shoalInfo = shoalInfo + '(m)\n'

        self.model.gui.Message( shoalInfo )
