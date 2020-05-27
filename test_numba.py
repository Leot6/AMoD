#coding:utf-8
import time

from numba import jit, prange
import numpy as np


def adds(x,y,m):
    return [x*i for i in range(y)]


@jit(parallel=True,nogil=True)
# @njit(parallel=True,nogil=True)
def adds1(x,y,m):
    sd =  np.empty((y))
    for i in prange(y):
        for j in range(m):
            sd[i]=x*i*m
    return sd


@jit(parallel=True,nogil=True)
def test(n):
    temp = np.empty((50, 50)) # <--- allocation is hoisted as a loop invariant as `np.empty` is considered pure
    for i in prange(n):
        temp[:] = 0           # <--- this remains as assignment is a side effect
        for j in range(50):
            temp[j, j] = i
    return temp


if __name__=="__main__":
    n = 50
    max = 100000000
    m=100
    st1 = time.time()
    val_1 = adds(n,max,m)
    print('time 1', time.time()-st1)

    st2 = time.time()
    val_2 = adds1(n,max,m)
    print('time 2', time.time()-st2)

    # st3 = time.time()
    # tmp = test(100**3*10)
    # print(time.time()-st3)
