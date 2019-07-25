import time
import math
import requests
import pickle
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


def plot_lognorm(data):
    params = lognorm.fit(data)
    xvals = np.linspace(0, max(data))
    pdf = lambda x: lognorm.pdf(xvals, *params)
    yvals = pdf(xvals)
    plt.plot(xvals, yvals)
    plt.show()


if __name__ == "__main__":

    onid = 10
    dnid = 900

    # aa = time.time()
    # print('aa running time:', (time.time() - aa))

    a = [4, 6, 8, 1, 11, 1, 14, 13, 7, 8, 16, 12, 12, 1, 16, 11, 4, 2, 6, 6, 1, 4, 4, 13]
    b = [30, 29, 17, 23, 24, 23, 27, 29, 21, 53, 18, 30, 28, 12, 36, 3, 5, 11, 17, 11, 23, 12, 9, 14]
    c = [62, 27, 40, 35, 19, 24, 30, 40, 39, 32, 28, 38, 38, 29, 34, 22, 25, 30, 13, 33, 27, 15, 18, 29]
    data = c
    shape, loc, scale = lognorm.fit(data)
    std = shape  # sigma
    median = scale
    mean = np.log(median)
    print(std, loc, median, mean)
    s = sorted(np.random.lognormal(mean, std, 10000))
    s1 = [round(i, 2) for i in s]
    print(s1[:10], s1[-10:])
    # plot_lognorm(data)



















