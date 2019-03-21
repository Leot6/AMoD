"""
constants are found here
"""
from dateutil.parser import parse


# demand file paths, demand volume (percentage of total), simulation start time and its nickname
DMD_PATH = './data/Manhattan-taxi-20160501.csv'
STN_PATH = './data/stations-630.csv'
DMD_VOL = 0.1
DMD_SST = parse('2016-05-01 00:00:00')
DMD_STR = 'Manhattan'

# fleet size, vehicle capacity and ridesharing size
FLEET_SIZE = 200
VEH_CAPACITY = 4
RIDESHARING_SIZE = 4

# maximum detour factor and maximum wait time window
MAX_DETOUR = 1.5
MAX_DELAY = 60 * 5
MAX_WAIT = 60 * 3

# warm-up time, study time and cool-down time of the simulation (in seconds)
T_WARM_UP = 60 * 0
T_STUDY = 30 + 30 * 60
T_COOL_DOWN = 60 * 0
T_TOTAL = (T_WARM_UP + T_STUDY + T_COOL_DOWN)

# methods for vehicle-request assignment and rebalancing
# ins = insertion heuristics, rtv = rtv-graph
# sar = simple anticipatory rebalancing, orp = optimal rebalancing problem, dqn = deep Q network
MET_ASSIGN = 'rtv'
MET_REBL = 'sar'

# intervals for vehicle-request assignment and rebalancing
INT_ASSIGN = 30
INT_REBL = 60

# coefficients for wait time and in-vehicle travel time in the cost function
COEF_WAIT = 1.5
COEF_INVEH = 1.0

# constant vehicle speed when road network is disabled (in meters/second)
CST_SPEED = 40

# if true, activate the animation
IS_ANIMATION = False

# constant vehicle speed when road network is disabled (in meters/second)
CST_SPEED = 30


# # parameters for Manhattan map
# map width and height (km)
MAP_WIDTH = 10.71
MAP_HEIGHT = 20.85

# coordinates
# (Olng, Olat) lower left corner
Olng = -74.0300
Olat = 40.6950
# (Olng, Olat) upper right corner
Dlng = -73.9030
Dlat = 40.8825


# # parameters for london map
# # map width and height (km)
# MAP_WIDTH = 8.3158
# MAP_HEIGHT = 4.4528
#
# # coordinates
# # (Olng, Olat) lower left corner
# Olng = -0.19
# Olat = 51.48
# # (Dlng, Dlat) upper right corner
# Dlng = -0.07
# Dlat = 51.52
# # number of cells in the gridded map
# Nlng = 10
# Nlat = 10
# # number of moving cells centered around the vehicle
# Mlng = 5
# Mlat = 5
# # length of edges of a cell
# Elng = 0.012
# Elat = 0.004
