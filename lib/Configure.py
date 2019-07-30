"""
constants are found here
"""
import pickle
import pandas as pd
from dateutil.parser import parse

# ride-sharing logic mode
# MODEE = 'VT'
MODEE = 'VT_replan'
# MODEE = 'VT_replan_all'

# travel mode
# IS_STOCHASTIC = True
IS_STOCHASTIC = False
# IS_STOCHASTIC_CONSIDERED = True
IS_STOCHASTIC_CONSIDERED = False

# taxi requests data, station loctions, graph nodes and travel time table
STN_LOC = pd.read_csv('./data/stations-630.csv')
NOD_LOC = pd.read_csv('./data/nodes.csv').values.tolist()
# REQ_DATA = pd.read_csv('./data/Manhattan-taxi-20160507.csv')
with open('./data/REQ_DATA.pickle', 'rb') as f:
    REQ_DATA = pickle.load(f)
# NOD_TTT = pd.read_csv('./data/travel-time-table.csv', index_col=0).values
with open('./data/NOD_TTT.pickle', 'rb') as f:
    NOD_TTT = pickle.load(f)
with open('./data/NOD_SPT.pickle', 'rb') as f:
    NOD_SPT = pickle.load(f)
with open('./data/NET_NYC.pickle', 'rb') as f:
    NET_NYC = pickle.load(f)

# demand volume (percentage of total), simulation start time and its nickname
DMD_VOL = 0.3
DMD_SST = parse('2015-05-02 00:00:00')
DMD_STR = 'Manhattan'

# fleet size, vehicle capacity and ridesharing size
FLEET_SIZE = 1000
VEH_CAPACITY = 4
RIDESHARING_SIZE = 4

# maximum wait time window, maximum total delay and maximum in-vehicle detour
MAX_WAIT = 30 * 5
MAX_DELAY = MAX_WAIT * 2
MAX_DETOUR = 1.3

# intervals for vehicle-request assignment and rebalancing
INT_ASSIGN = 60
INT_REBL = INT_ASSIGN * 1

# warm-up time, study time and cool-down time of the simulation (in seconds)
T_WARM_UP = 60 * 0
T_STUDY = 60 * 30
T_COOL_DOWN = 60 * 0
T_TOTAL = (T_WARM_UP + T_STUDY + T_COOL_DOWN)

# methods for vehicle-request assignment and rebalancing
MET_ASSIGN = 'ILP'
MET_REBL = 'naive'
# MET_REBL = 'None'

# running time threshold for RTV building(each single vehicle) and ILP solver
CUTOFF_RTV = 600
CUTOFF_ILP = 15

# if true, activate the animation / analysis
IS_ANIMATION = False
IS_ANALYSIS = True
IS_DEBUG = False

# coefficients for wait time, in-vehicle travel time in the cost function
COEF_WAIT = 1.0
COEF_INVEH = 1.0


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
