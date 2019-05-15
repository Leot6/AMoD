"""
serialize data to pickle file to save time on initialization
"""

import pickle
import time
import pandas as pd

if __name__ == '__main__':
    aa = time.time()
    # REQ_DATA = pd.read_csv('Manhattan-taxi-20150502.csv')
    NOD_TTT = pd.read_csv('travel-time-table.csv', index_col=0).values
    print('load from csv file running time:', (time.time() - aa))

    # with open('REQ_DATA.pickle', 'wb') as f:
    #     pickle.dump(REQ_DATA, f)
    with open('NOD_TTT.pickle', 'wb') as f:
        pickle.dump(NOD_TTT, f)

    bb = time.time()
    # with open('REQ_DATA.pickle', 'rb') as f:
    #     REQ_DATA = pickle.load(f)
    # with open('NOD_TTT.pickle', 'rb') as f:
    #     NOD_TTT = pickle.load(f)
    # print('load from pickle file running time:', (time.time() - bb))
