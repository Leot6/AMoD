"""
constants are found here
"""

from lib.Demand import *


# fleet size and vehicle capacity
FLEET_SIZE = 10
VEH_CAPACITY = 8
RIDESHARING_SIZE = 6


# de, demand volume and its nickname
DMD_MAT = M_Matrix
DMD_VOL = 120 * 200
DMD_STR = "London"

# warm-up time, study time and cool-down time of the simulation (in seconds)
T_WARM_UP = 60 * 0
T_STUDY = 30 + 30 * 10
T_COOL_DOWN = 60 * 0
T_TOTAL = (T_WARM_UP + T_STUDY + T_COOL_DOWN)

# methods for vehicle-request assignment and rebalancing
# ins = insertion heuristics, rtv = rtv-graph
# sar = simple anticipatory rebalancing, orp = optimal rebalancing problem, dqn = deep Q network
MET_ASSIGN = "rtv"
MET_REBL = "sar"

# intervals for vehicle-request assignment, reoptimization and rebalancing
INT_ASSIGN = 30
INT_REBL = 150

# if road network is enabled, use the routing server; otherwise use Euclidean distance
IS_ROAD_ENABLED = True
# if true, activate the animation
IS_ANIMATION = True
# if true, print the number of times OsrmEngine is called
IS_DEBUGGING = False

# maximum detour factor and maximum wait time window
MAX_DETOUR = 1.5
MAX_DELAY = 60 * 20
MAX_WAIT = 60 * 10

# constant vehicle speed when road network is disabled (in meters/second)
CST_SPEED = 6

# coefficients for wait time and in-vehicle travel time in the utility function
COEF_WAIT = 1.5
COEF_INVEH = 1.0

# coefficients for Simulated Annealing
SA_initT = 100
SA_minT = 1
SA_threshold = 150
SA_markov = 10


# map width and height (km)
MAP_WIDTH = 8.3158
MAP_HEIGHT = 4.4528

# coordinates
# (Olng, Olat) lower left corner
Olng = -0.19
Olat = 51.48
# (Dlng, Dlat) upper right corner
Dlng = -0.07
Dlat = 51.52
# number of cells in the gridded map
Nlng = 10
Nlat = 10
# number of moving cells centered around the vehicle
Mlng = 5
Mlat = 5
# length of edges of a cell
Elng = 0.012
Elat = 0.004
