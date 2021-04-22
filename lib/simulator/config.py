"""
constants are found here
"""
import pickle
import os
import numpy as np
from dateutil.parser import parse

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

# ************************************************************************************** #
# # parameters for Simulator # #
# taxi requests data, station loctions
DATE = '20160525'
TRIP_NUM = '400k'  # 400k(404310), 500k(504985), 600k(605660), 700k(703260), 800k(800752)，1200k(1219956)
STN_NUM = '101'  # '101' or '630'

with open(f'{root_path}/data-gitignore/NYC_REQ_DATA_{TRIP_NUM}.pickle', 'rb') as f:
    REQ_DATA = pickle.load(f)
with open(f'{root_path}/data-gitignore/NYC_STN_LOC_{STN_NUM}.pickle', 'rb') as f:
    STN_LOC = pickle.load(f)

# demand volume (percentage of total), simulation start time and its nickname
DMD_VOL = 1  # <= 1
DMD_SST = parse(DATE + ' 00:00:00')
# DMD_SST = parse(DATE + ' 18:30:00')
REQ_INIT_IDX = 0
DMD_STR = 'Manhattan'

# warm-up time, study time and cool-down time of the simulation (in seconds), 24 hour = 1440 min
T_WARM_UP = 60 * 0    # = 60 * 30
T_STUDY = 60 * 60     # < 60 * 1371
T_COOL_DOWN = 60 * 0  # = 60 * 39
# T_TOTAL = (T_WARM_UP + T_STUDY + T_COOL_DOWN)

# fleet size, vehicle capacity and ridesharing size
FLEET_SIZE = 2000  #  int(2000 * DMD_VOL)
VEH_CAPACITY = 4
RIDESHARING_SIZE = int(VEH_CAPACITY * 1.8)

# maximum wait time window, maximum total delay and maximum in-vehicle detour
MAX_WAIT = 60 * 5
MAX_DELAY = MAX_WAIT * 2
MAX_DETOUR = 1.3
# MAX_DETOUR = 0
# MAX_DETOUR = np.inf

# intervals for vehicle-request assignment and rebalancing
INT_ASSIGN = 30
INT_REBL = INT_ASSIGN * 1

# dispatching and rebalancing methods
DISPATCHER = 'GI'
# DISPATCHER = 'SBA'
# DISPATCHER = 'OSP'
# DISPATCHER = 'RTV'

REBALANCER = 'NR'
# REBALANCER = 'none'

OBJECTIVE = 'Time'
# OBJECTIVE = 'ServiceRate'
# OBJECTIVE = 'Reliability'
# OBJECTIVE = 'Profit'
Reliability_Shreshold = 0

# if true, activate the animation / analysis
IS_ANIMATION = False
# IS_ANIMATION = True
IS_ANALYSIS = True
# IS_DEBUG = False
IS_DEBUG = True

# travel time mode
# IS_STOCHASTIC_TRAFFIC = True
IS_STOCHASTIC_TRAFFIC = False
# IS_STOCHASTIC_SCHEDULE = True
IS_STOCHASTIC_SCHEDULE = False
# IS_STOCHASTIC_ROUTING = True
IS_STOCHASTIC_ROUTING = False
LEVEl_OF_STOCHASTIC = 4

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
    # T_STUDY = 60 * 60
    # VEH_CAPACITY = 8
    if TRIP_NUM == '400k':
        REQ_INIT_IDX = 269500
        # FLEET_SIZE = 2000
    elif TRIP_NUM == '500k':
        REQ_INIT_IDX = 337100
        # FLEET_SIZE = 2400
    elif TRIP_NUM == '600k':
        REQ_INIT_IDX = 404700
        # FLEET_SIZE = 2700
    elif TRIP_NUM == '700k':
        REQ_INIT_IDX = 468700
        # FLEET_SIZE = 3000
    elif TRIP_NUM == '800k':
        REQ_INIT_IDX = 532800
        # FLEET_SIZE = 3300
    elif TRIP_NUM == '1000k':
        REQ_INIT_IDX = 669600
        # FLEET_SIZE = 3900
    elif TRIP_NUM == '1200k':
        REQ_INIT_IDX = 815300
        # FLEET_SIZE = 4500
    if IS_DEBUG:
        T_COOL_DOWN = 1

T_TOTAL = (T_WARM_UP + T_STUDY + T_COOL_DOWN)
