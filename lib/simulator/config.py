"""
constants are found here
"""
import pickle
from dateutil.parser import parse

# ************************************************************************************** #
# # parameters for S # #
# taxi requests data, station loctions
TRAVEL_TIME = 'WEEK'
DATE = '20150506'  # '20150505' or '20150506'
STN_NUM = '101'  # '101' or '630'
with open(f'./data/NYC_REQ_DATA_{DATE}.pickle', 'rb') as f:
    REQ_DATA = pickle.load(f)
with open(f'./data/NYC_STN_LOC_{STN_NUM}.pickle', 'rb') as f:
    STN_LOC = pickle.load(f)

# demand volume (percentage of total), simulation start time and its nickname
DMD_VOL = 1
DMD_SST = parse(DATE + ' 00:00:00')
DMD_STR = 'Manhattan'

# DISPATCHER = 'GI'
# DISPATCHER = 'OSP'
DISPATCHER = 'OSP-SR'
# DISPATCHER = 'OSP-RO'

# warm-up time, study time and cool-down time of the simulation (in seconds)
T_WARM_UP = 60 * 10
T_STUDY = 60 * 1000
T_COOL_DOWN = 60 * 19
T_TOTAL = (T_WARM_UP + T_STUDY + T_COOL_DOWN)

# fleet size, vehicle capacity and ridesharing size
FLEET_SIZE = 3000
VEH_CAPACITY = 6

# maximum wait time window, maximum total delay and maximum in-vehicle detour
MAX_WAIT = 60 * 5
MAX_DELAY = 60 * 10
# MAX_DETOUR = -1
MAX_DETOUR = 1.3

# intervals for vehicle-request assignment and rebalancing
INT_ASSIGN = 30
INT_REBL = INT_ASSIGN * 1

# if true, activate the animation / analysis
IS_ANIMATION = False
IS_ANALYSIS = True
IS_DEBUG = False
# IS_DEBUG = True

# travel time mode
# IS_STOCHASTIC = True
IS_STOCHASTIC = False
IS_STOCHASTIC_CONSIDERED = True
# IS_STOCHASTIC_CONSIDERED = False

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
# # coordinates
# # (Olng, Olat) lower left corner
# Olng = -0.19
# Olat = 51.48
# # (Dlng, Dlat) upper right corner
# Dlng = -0.07
# Dlat = 51.52

# ************************************************************************************** #
# # parameters for A1_OSP # #
# ride-sharing logic mode

# ridesharing size in computation
RIDESHARING_SIZE = int(VEH_CAPACITY * 1.8)
if DISPATCHER == 'OSP-SR':
    RIDESHARING_SIZE = 1

# methods for vehicle-request assignment and rebalancing
MET_ASSIGN = 'ILP'
# MET_REBL = 'naive'
MET_REBL = 'none'

# running time threshold for VTtable building(each single vehicle) and ILP solver
CUTOFF_VT = 3000
CUTOFF_ILP = 1200

# coefficients for wait time, in-vehicle travel time in the cost function
COEF_WAIT = 1.0
COEF_INVEH = 1.0

# ************************************************************************************** #
# # parameters for A2_GI # #
# ride-sharing logic mode
if DISPATCHER == 'GI':
    INT_ASSIGN = 1
    RIDESHARING_SIZE = 0
