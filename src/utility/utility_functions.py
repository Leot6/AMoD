
import shutil
import copy
import numpy as np
import pandas as pd
from tqdm import tqdm
from dateutil.parser import parse
from tqdm import tqdm

from src.simulator.types import *
from src.utility.animation_generator import anim

from datetime import datetime, timedelta
from src.simulator.config import *


def compute_the_accumulated_seconds_from_0_clock(time_date: str) -> int:
    time_0_clock = time_date[0:10] + " 00:00:00"
    accumulated_sec = (parse(time_date) - parse(time_0_clock)).seconds
    return accumulated_sec


def get_time_stamp_datetime() -> datetime:
    return datetime.now()


def get_runtime_sec_from_t_to_now(t: datetime) -> float:
    return round((datetime.now() - t).total_seconds(), 2)


def timer_start() -> datetime:
    return datetime.now()


def timer_end(t: datetime) -> str:
    runtime_sec = (datetime.now() - t).total_seconds()
    return f"{runtime_sec:.3f}s"


def verify_the_current_epoch_is_in_the_main_study_horizon(epoch_end_time_sec: int) -> bool:
    main_sim_start_time_sec = WARMUP_DURATION_MIN * 60
    main_sim_end_time_sec = main_sim_start_time_sec + SIMULATION_DURATION_MIN * 60
    return main_sim_start_time_sec < epoch_end_time_sec <= main_sim_end_time_sec
