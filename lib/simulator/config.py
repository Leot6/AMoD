"""
constants are found here
"""
import pickle
import os
from dateutil.parser import parse

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

# ************************************************************************************** #
# # parameters for Simulator # #
# taxi requests data, station loctions
TRAVEL_TIME = 'WEEK'
DATE = '20160525'
TRIP_NUM = '1200k'  # 400k(404310), 500k(504985), 600k(605660), 700k(703260), 800k(800752)，1200k(1219956)
STN_NUM = '101'  # '101' or '630'

trip_path = 'trip-data-gitignore' if TRIP_NUM == '700k' or TRIP_NUM == '800k' \
                                     or TRIP_NUM == '1000k' or TRIP_NUM == '1200k' else ''

with open(f'{root_path}/data/{trip_path}/NYC_REQ_DATA_{TRIP_NUM}.pickle', 'rb') as f:
    REQ_DATA = pickle.load(f)
with open(f'{root_path}/data/NYC_STN_LOC_{STN_NUM}.pickle', 'rb') as f:
    STN_LOC = pickle.load(f)

# demand volume (percentage of total), simulation start time and its nickname
DMD_VOL = 1  # <= 1
# DMD_SST = parse(DATE + ' 00:00:00')
DMD_SST = parse(DATE + ' 18:30:00')
REQ_INIT_IDX = 0
DMD_STR = 'Manhattan'

# DISPATCHER = 'GI'
DISPATCHER = 'SBA'
# DISPATCHER = 'RTV'
# DISPATCHER = 'OSP'

REBALANCER = 'NR'
# REBALANCER = 'none'

# warm-up time, study time and cool-down time of the simulation (in seconds), 24 hour = 1440 min
T_WARM_UP = 60 * 30
T_STUDY = 60 * 1370  # < 60 * 1371
T_COOL_DOWN = 60 * 39
# T_TOTAL = (T_WARM_UP + T_STUDY + T_COOL_DOWN)

# fleet size, vehicle capacity and ridesharing size
FLEET_SIZE = 2000
VEH_CAPACITY = 8
RIDESHARING_SIZE = int(VEH_CAPACITY * 1.8)

# maximum wait time window, maximum total delay and maximum in-vehicle detour
MAX_WAIT = 60 * 5
MAX_DELAY = MAX_WAIT * 2
# MAX_DETOUR = -1
MAX_DETOUR = 1.3

# intervals for vehicle-request assignment and rebalancing
INT_ASSIGN = 30
INT_REBL = INT_ASSIGN * 1

# coefficients for wait time in the cost function
COEF_WAIT = 1

# if true, activate the animation / analysis
IS_ANIMATION = False
IS_ANALYSIS = True
IS_DEBUG = False
# IS_DEBUG = True

# travel time mode
# IS_STOCHASTIC = True
IS_STOCHASTIC = False
# IS_STOCHASTIC_CONSIDERED = True
IS_STOCHASTIC_CONSIDERED = False

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

# ************************************************************************************** #

if DMD_SST == parse(DATE + ' 18:30:00'):
    T_STUDY = 60 * 60
    VEH_CAPACITY = 8
    if TRIP_NUM == '400k':
        REQ_INIT_IDX = 269500
        FLEET_SIZE = 2000
    elif TRIP_NUM == '500k':
        REQ_INIT_IDX = 337100
        FLEET_SIZE = 2300
    elif TRIP_NUM == '600k':
        REQ_INIT_IDX = 404700
        FLEET_SIZE = 2600
    elif TRIP_NUM == '700k':
        REQ_INIT_IDX = 468700
        FLEET_SIZE = 2900
    elif TRIP_NUM == '800k':
        REQ_INIT_IDX = 532800
        FLEET_SIZE = 3200
    elif TRIP_NUM == '1000k':
        REQ_INIT_IDX = 669600
        FLEET_SIZE = 3800
    elif TRIP_NUM == '1200k':
        REQ_INIT_IDX = 815300
        FLEET_SIZE = 4400
    if IS_DEBUG:
        T_COOL_DOWN = 1

T_TOTAL = (T_WARM_UP + T_STUDY + T_COOL_DOWN)
