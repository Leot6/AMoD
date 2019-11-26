import time
import math
import requests
import pickle
import mosek
import re
import copy
import networkx as nx
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from heapq import heappush, heappop
from itertools import count, islice
from tqdm import tqdm
from collections import deque
from scipy.stats import lognorm

CUTOFF_ILP = 10


if __name__ == "__main__":
    a = {1, 2, 3, 4, 12, 435}
    b = {1, 2, 3, 4, 12, 435}

    a1 = time.time()
    a.issubset(b)
    print('    a1 running time:', round((time.time() - a1), 10))

    a2 = time.time()
    a < b
    print('    a2 running time:', round((time.time() - a2), 10))



















