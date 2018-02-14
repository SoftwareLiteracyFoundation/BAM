'''Hydraulic functions for the Bay Assessment Model (BAM)'''

# Python distribution modules
from math import sqrt, pow

# Local modules
import constants

#---------------------------------------------------------------
# 
#---------------------------------------------------------------
def Hydro( model ) :
    '''Calculation of water and mass fluxes over shoals is followed by 
    mass balances for basins.
    
    At the beginning of each time step the velocity of water for each depth 
    increment i of each shoal j is calculated using the water levels in
    adjacent basins and Manning's equation. 
    
    The cross sectional area Aij of water for each depth of the shoal is 
    calculated from the length of each wet_area at each depth increment 
    of each shoal times a water level height.  If the downsteam water
    depth is positive, it is used as the height.  If not, the hydraulic
    radius of the flow is used. 

    The flux of water across each shoal is calculated as Fj = Σ Vij * Aij.
    
    The fluxes Fj are multiplied by the time step duration and summed 
    to give the net volume of water exchanged over the shoals.
    The net volume of water exchanged is added to the volume in the
    basin at the beginning of the time step. Other inputs of water during the 
    time step are added to each basin (rain, ET, runoff, groundwater). 
    The resulting new volume of water in each basin is used with the 
    bathymetric data for the basin to calculate a new water level in the basin.
    
    The mass flux of dissolved substances Mj is calculated as the product of 
    the concentration of the substance in the water Cj (g m-3) and the water 
    flux on each shoal Mj = Fj * Cj. 
    
    The mass fluxes Mj are summed around the boundary of each basin. 
    The net mass flux over the shoals is multiplied by the time step and, 
    along with other inputs and outputs of mass during the time step, added 
    to the mass in the basin at the beginning of the time step. The new 
    mass is divided by the water volume for the concentration at the end 
    of the time step. 
    '''
    pass

#---------------------------------------------------------------
# 
#---------------------------------------------------------------
def ShoalVelocities( model ) :
    '''At the beginning of each step for each shoal the water level in the 
    upstream basin is used to calculate the critical depth above the shoal.
    If the downstream water level is lower than h_crit there is sufficient
    head difference to create criticial flow. Velocity is estimated with an
    iterative solution between the two dependent variables of v and R 
    (R = hydraulic radius = ratio of cross sectional flow area to the
    wetted perimeter, which for a shallow, broad cross section can be 
    approximated by the average depth) via Cosby (2010) equations 1.13 & 1.15. 

    If the downstream level is higher than h_crit, a non-critical solution 
    is calculated using an iteration for the two dependent variables v and R
    via Cosby (2010) equations 1.10 & 1.11. 

    In either case, the velocity from the last time step, v0, and the water 
    levels from the current time step are used in equations 1.10 or 1.14 to 
    estimate the initial hydraulic radius, R0. A first estimate of the velocity 
    for the current time step, v1, is then calculated using the appropriate
    equation. The new velocity v1 is used to update the hydraulic radius R1, 
    which is used to calculate a new velocity, v2. If v1 and v2 agree to 
    within a specified tolerance, the v2 value is accepted.
    '''

    if model.args.DEBUG_ALL :
        print( '-> ShoalVelocities' )

    for shoal_number, Shoal in model.Shoals.items() :

        if model.args.DEBUG_ALL :
            if Shoal.Basin_A_key not in model.Basins.keys() or \
               Shoal.Basin_B_key not in model.Basins.keys() :
                continue
        
        # If shoal boundary is land (width zero) continue
        if Shoal.no_flow :
            continue
        
        # Process each shoal depth that has non-zero wet_length 
        for depth_ft, length in Shoal.wet_length.items() :

            if length < 1 :
                continue

            # Initial depth estimate & itertation setup
            ShoalBasinLevels( model, Shoal, depth_ft )

            if Shoal.flow_sign == 0 :
                continue

            # Compute initial estimate of velocity and hydraulic radius
            # Use initial_velocity flag rather than checking :
            #       if depth_ft not in Shoal.velocity.keys() : ...
            if not Shoal.initial_velocity :
                VelocityHydraulicRadius( Shoal, depth_ft )

            previous_velocity = Shoal.velocity[ depth_ft ]

            # Update friction_factor for next iteration or timestep
            hydraulic_radius = Shoal.hydraulic_radius[ depth_ft ]
            if hydraulic_radius > 0 :
                Shoal.friction_factor[ depth_ft ] = \
                    2 * constants.g * \
                    pow( Shoal.manning_coefficient, 2 ) * \
                    Shoal.width * \
                    pow( hydraulic_radius, -4/3 )
            else :
                Shoal.friction_factor[ depth_ft ] = 1E9
            
            #--------------------------------------------------------
            # Iteration to estimate velocity and hydraulic.radius
            iteration_exceeded = True

            for i in range( 1, model.max_iteration ) :

                VelocityHydraulicRadius( Shoal, depth_ft )

                velocity = Shoal.velocity[ depth_ft ]

                delta_velocity = previous_velocity - velocity

                if abs( delta_velocity ) <= model.velocity_tol :
                    iteration_exceeded = False
                    break

                previous_velocity = velocity

            if iteration_exceeded :
                msg = '\n*** Mannings: iterations exceeded for shoal ' +\
                    str( shoal_number ) + ' at depth ' + str( depth_ft ) + '\n'
                model.gui.Message( msg )

        # Set flag that this shoal has been initialized
        Shoal.initial_velocity = True 

#---------------------------------------------------------------
# 
#---------------------------------------------------------------
def ShoalBasinLevels( model, Shoal, depth_ft ) :
    '''Determine shoal water level elevations h_upstream and h_downstream.
    h_critical, h_upstream and h_downstream are elevations with respect to
    the shoal top elevation (0 depth). All water level elevations are 
    anomalies from the shoal elevation (0 depth), a convienent but limiting 
    convention. 

    Set flow_sign : -1 = Flow B -> A, 1 = Flow A -> B, 0 = No flow'''

    depth = depth_ft * 0.3048 # convert feet to meters

    Basin_A = Shoal.Basin_A
    Basin_B = Shoal.Basin_B

    # h_basin_* will be negative only if water_level is negative 
    # and greater in magnitude than depth
    h_Basin_A = Basin_A.water_level + depth
    h_Basin_B = Basin_B.water_level + depth

    if h_Basin_A < 0 and h_Basin_B < 0 :
        # If water level is below shoal: no flow
        Shoal.h_upstream      [ depth_ft ] = h_Basin_A
        Shoal.h_downstream    [ depth_ft ] = h_Basin_B
        Shoal.friction_factor [ depth_ft ] = 1E9
        Shoal.velocity        [ depth_ft ] = 0
        Shoal.hydraulic_radius[ depth_ft ] = 0
        Shoal.flow_sign                    = 0     # No flow

    elif h_Basin_A > h_Basin_B :
        Shoal.h_upstream  [ depth_ft ] = h_Basin_A
        Shoal.h_downstream[ depth_ft ] = h_Basin_B
        Shoal.flow_sign                = 1         # Flow A -> B

    else :
        Shoal.h_upstream  [ depth_ft ] = h_Basin_B
        Shoal.h_downstream[ depth_ft ] = h_Basin_A
        Shoal.flow_sign                = -1         # Flow B -> A

#---------------------------------------------------------------
# 
#---------------------------------------------------------------
def VelocityHydraulicRadius( Shoal, depth_ft ) :
    '''Compute flow velocity based on heads and flow regime.'''

    h_upstream      = Shoal.h_upstream     [ depth_ft ]
    h_downstream    = Shoal.h_downstream   [ depth_ft ]
    friction_factor = Shoal.friction_factor[ depth_ft ]

    h_critical = ( 2 * h_upstream ) / ( 3 + friction_factor )
            
    if h_downstream < h_critical :
        Shoal.h_downstream[ depth_ft ] = h_critical
        h_downstream                   = h_critical

    # If both h_ are negative : no flow
    level_difference       = h_upstream - h_downstream
    Shoal.level_difference = level_difference

    # Velocity head
    h_velocity = level_difference / ( 1 + friction_factor )

    # sqrt[ (m/s^2) * (m) ] = (m/s)
    Shoal.velocity[ depth_ft ] = Shoal.flow_sign * \
                                 sqrt( 2 * constants.g * h_velocity )

    # If the flow cross section is a wide, shallow rectangle, then the
    # average depth is an approximation of the hydraulic radius
    Shoal.hydraulic_radius[ depth_ft ] = \
        max( 0, ( h_upstream - h_velocity + h_downstream ) ) / 2

#---------------------------------------------------------------
# 
#---------------------------------------------------------------
def MassTransport( model ) :
    '''See notes in Hydro'''

    if model.args.DEBUG_ALL :
        print( '-> MassTransport' )

    #--------------------------------------------------------------------
    # Sum the total flow over all shoal depths over the timestep
    #--------------------------------------------------------------------
    # Q(m^3/s) = v(m/s)   * A(m^2)
    # Vol(m^3) = Q(m^3/s) * dt(s)
    for shoal_number, Shoal in model.Shoals.items() :

        # If shoal boundary is land (zero width) continue
        if Shoal.no_flow :
            continue
        
        Basin_A = Shoal.Basin_A
        Basin_B = Shoal.Basin_B
        
        #--------------------------------------------------------
        # Process each shoal depth that has non-zero wet_length 
        #--------------------------------------------------------
        for depth_ft, length in Shoal.wet_length.items() :

            if length < 1 :
                continue

            # This updates flow_sign, h_upstream, h_downstream at depth_ft
            ShoalBasinLevels( model, Shoal, depth_ft )

            if Shoal.flow_sign == 0 :
                Shoal.cross_section[ depth_ft ] = 0
                Shoal.Q            [ depth_ft ] = 0
                continue

            # What depth to use for the flow cross-sectional area:
            # upstream, downstream, or some median?
            # downstream makes sense since it's where the water is 
            # flowing into the basin, but it can be negative 
            h_flow = None

            h_downstream     = Shoal.h_downstream    [ depth_ft ]
            hydraulic_radius = Shoal.hydraulic_radius[ depth_ft ]

            if h_downstream > 0 :
                h_flow = h_downstream
            else :
                h_flow = hydraulic_radius

            cross_section = h_flow * Shoal.wet_length[ depth_ft ]

            if cross_section < 0 :
                raise ValueError ( 'Negative Shoal.cross_section' )

            Shoal.cross_section[ depth_ft ] = cross_section

            # Q(m^3/s) = v(m/s) * A(m^2)
            Shoal.Q[ depth_ft ] = Shoal.velocity[ depth_ft ] * cross_section

        # Sum flow across shoal (m^3/s) 
        Shoal.Q_total             = sum( Shoal.Q.values() )
        Shoal.cross_section_total = sum( Shoal.cross_section.values() )

        # Transfer volumes across shoal into basins
        # The sign of Q handles the transfer direction
        # flow_sign positive : A -> B
        # flow_sign negative : B -> A
        delta_volume = Shoal.Q_total * model.timestep # (m^3/timestep)

        Shoal.volume_A_B =  delta_volume # (m^3/timestep)
        Shoal.volume_B_A = -delta_volume # (m^3/timestep)

        if not Basin_A.boundary_basin :
            Basin_A.water_volume -= delta_volume
        if not Basin_B.boundary_basin :
            Basin_B.water_volume += delta_volume

        # Shallow banks can have no volume at low stage
        # Limit the volume to a lower bound
        if Basin_A.water_volume < 0 :
            Basin_A.water_volume = 0
        if Basin_B.water_volume < 0 :
            Basin_B.water_volume = 0
        if Basin_A.water_volume == 0 or Basin_B.water_volume == 0 :
            continue  # don't transfer salt

        # Establish source basin and it's salinity
        if Shoal.flow_sign == 1 :     # flow from A -> B
            source_salinity = Basin_A.salinity
        elif Shoal.flow_sign == -1  : # flow from B -> A
            source_salinity = Basin_B.salinity
        else :
            source_salinity = 0

        # Transfer salt 
        # delta salt_mass = salinity (g/kg) * Vol (m^3) * rho (kg/m^3)
        # Water at 25 C rho = 997 kg/m^3
        delta_salt_mass = source_salinity * delta_volume * 997

        if not Basin_A.boundary_basin :
            Basin_A.salt_mass -= delta_salt_mass

        if not Basin_B.boundary_basin :
            Basin_B.salt_mass += delta_salt_mass

        if Basin_A.salt_mass < 0 :
            Basin_A.salt_mass = 0
        if Basin_B.salt_mass < 0 :
            Basin_B.salt_mass = 0

    #----------------------------------------------------------------
    # Sum basin flow and compute salinity
    #----------------------------------------------------------------
    for Basin in model.Basins.values() :

        if Basin.boundary_basin :
            continue

        Basin.shoal_transport = 0

        for Shoal in Basin.Shoals :
            if Basin is Shoal.Basin_A :
                Basin.shoal_transport += Shoal.volume_A_B
            elif Basin is Shoal.Basin_B :
                Basin.shoal_transport += Shoal.volume_B_A 
            else :
                raise Exception( 'Invalid Basin in Shoal' )

        # Salinity adjustment o/oo = g/kg = g / ( m^3 * (kg/m^3) )
        if not Basin.salinity_from_data and Basin.water_volume :
            new_salinity = Basin.salt_mass / ( Basin.water_volume * 997 )

            # On shallow banks a low stage/volume can spike the salinity
            # Log a message
            if new_salinity > 90 :
                if Basin.name not in [ 'First National Bank', 
                                       'Ninemile Bank',  'Conchie Channel',
                                       'Johnson Key',    'Sandy Key',
                                       'Dildo Key Bank', 'Snake Bight', 
                                       'Rankin Bight',   'Rankin Lake',
                                       'Deer Key',       'Swash Keys' ] :
                    msg = '*** MassTransport: Basin ' + Basin.name +\
                          ' old salinity: ' + str( round( Basin.salinity, 1)) +\
                          ' new salinity: ' + str( round( new_salinity, 1 ) ) +\
                          ' volume: '    + str( round( Basin.water_volume ) ) +\
                          ' salt mass: ' + str( round( Basin.salt_mass ) )    +\
                          ' at ' + str( model.current_time ) + '\n'
                    model.gui.Message( msg )
                    print( msg )

                # Ignore the new salinity... 
                # Play God and wish some salt away...
                Basin.salt_mass = Basin.salt_mass * 0.5 # JP ???

            else :
                Basin.salinity = new_salinity

    #----------------------------------------------------------------
    # If EDEN stage is used to drive EVER runoff, sum the shoal transport
    # for reporting the total runoff in output data. 
    #----------------------------------------------------------------
    if not model.args.noStageRunoff :

        for Basin, Shoals in model.runoff_stage_shoals.items() :

            Basin.runoff_EVER = 0

            for Shoal in Shoals :
                # All EVER runoff destination basins are Shoal.Basin_B
                # Flow sign convention is: flow out +, flow in -
                if Basin is Shoal.Basin_B :
                    Basin.runoff_EVER -= Shoal.volume_A_B
                else :
                    raise Exception( 'Invalid Basin in Shoal (Runoff)' )
            
#---------------------------------------------------------------
# 
#---------------------------------------------------------------
def Depths( model ) :
    '''Update basin depths from volume changes.'''

    for Basin in model.Basins.values() :
        
        if not Basin.area : # Boundary basins have no area
            continue

        Basin.Area() # Update area at current water levels

        volume_difference = Basin.water_volume - Basin.previous_volume

        h_difference = volume_difference / Basin.area

        Basin.water_level += h_difference

        # Update previous_volume for next iteration
        Basin.previous_volume = Basin.water_volume
