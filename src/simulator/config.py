"""
constants are found here
"""
import pickle
import os
from dateutil.parser import parse

##################################################################################
# Data File Path
##################################################################################
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
# map-data
PATH_TO_VEHICLE_STATIONS = f"{ROOT_PATH}/datalog-gitignore/map-data/stations-101.pickle"
PATH_TO_NETWORK_NODES = f"{ROOT_PATH}/datalog-gitignore/map-data/nodes.pickle"
PATH_TO_SHORTEST_PATH_TABLE = f"{ROOT_PATH}/datalog-gitignore/map-data/path-table.pickle"
PATH_TO_MEAN_TRAVEL_TIME_TABLE = f"{ROOT_PATH}/datalog-gitignore/map-data/mean-table.pickle"
PATH_TO_TRAVEL_DISTANCE_TABLE = f"{ROOT_PATH}/datalog-gitignore/map-data/dist-table.pickle"

# taxi-data
# SIMULATION_DAYs = ["03", "04", "05", "10", "11", "12", "17", "18", "19"]
# SIMULATION_DAYs = ["03", "04", "05", "10", "11", "12", "17", "18", "19"]
SIMULATION_DAYs = ["26", "25"]
TAXI_DATA_FILEs = [f"201605{day}-peak" for day in SIMULATION_DAYs]
PARTIAL_PATH_TO_TAXI_DATA = f"{ROOT_PATH}/datalog-gitignore/taxi-data/manhattan-taxi-"

# value-func-data
PARTIAL_PATH_TO_REPLAY_BUFFER_DATA = f"{ROOT_PATH}/datalog-gitignore/value-func-data/"

##################################################################################
# Mod System Config
##################################################################################
# dispatch_config
DISPATCHER = "OSP"        # 3 options: SBA, OSP-NR, OSP
REBALANCER = "NPO"        # 2 options: NONE, NPO

# fleet_config:
FLEET_SIZE = [1500]
VEH_CAPACITY = [6]

# request_config:
REQUEST_DENSITY = 1    # <= 1
MAX_PICKUP_WAIT_TIME_MIN = [7]
MAX_ONBOARD_DETOUR = 1.3   # < 2

##################################################################################
# Simulation Config
##################################################################################
SIMULATION_START_TIME = "2016-05-25 18:30:00"  # peak hour: 18:00:00 - 20:00:00
CYCLE_S = [30]
WARMUP_DURATION_MIN = 30        # 30 min
SIMULATION_DURATION_MIN = 60   # <= 1370 min
WINDDOWN_DURATION_MIN = 39      # 39 min
DEBUG_PRINT = False

##################################################################################
# Value Function Config
##################################################################################
COLLECT_DATA = True
ENABLE_VALUE_FUNCTION = False
EVAL_NET_FILE_NAME = "NET-LR1-GA95-FS1500-VC6-9D"

ONLINE_TRAINING = False
if not ENABLE_VALUE_FUNCTION:
    ONLINE_TRAINING = False

##################################################################################
# Animation Config - Manhattan Map
##################################################################################
RENDER_VIDEO = False
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


def config_change_fs(fs):
    global FLEET_SIZE
    FLEET_SIZE[0] = fs


def config_change_vc(vc):
    global VEH_CAPACITY
    VEH_CAPACITY[0] = vc


def config_change_wt(wt):
    global MAX_PICKUP_WAIT_TIME_MIN
    MAX_PICKUP_WAIT_TIME_MIN[0] = wt


def config_change_bp(bp):
    global CYCLE_S
    CYCLE_S[0] = bp
