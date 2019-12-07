"""
serialize data to pickle file to save time on initialization
"""

import pickle
import time
import pandas as pd

if __name__ == '__main__':
    aa = time.time()
    # REQ_DATA_2013 = pd.read_csv('Manhattan-taxi-20130503.csv')
    # STN_LOC = pd.read_csv('./Manhattan-graph/stations-630.csv')
    # NOD_LOC = pd.read_csv('./Manhattan-graph/nodes.csv').values.tolist()
    NOD_TTT = pd.read_csv('./Manhattan-graph/time-table-sun.csv', index_col=0).values
    # NOD_SPT = pd.read_csv('./Manhattan-graph/path-table-sun.csv', index_col=0).values

    print('load from csv file running time:', (time.time() - aa))

    # with open('REQ_DATA_2013.pickle', 'wb') as f:
    #     pickle.dump(REQ_DATA_2013, f)
    # with open('STN_LOC.pickle', 'wb') as f:
    #     pickle.dump(STN_LOC, f)
    # with open('NOD_LOC.pickle', 'wb') as f:
    #     pickle.dump(NOD_LOC, f)
    with open('NOD_TTT.pickle', 'wb') as f:
        pickle.dump(NOD_TTT, f)
    # with open('NOD_SPT.pickle', 'wb') as f:
    #     pickle.dump(NOD_SPT, f)

    bb = time.time()
    # with open('REQ_DATA_2013.pickle', 'rb') as f:
    #     REQ_DATA = pickle.load(f)
    # with open('STN_LOC.pickle', 'rb') as f:
    #     STN_LOC = pickle.load(f)
    # with open('NOD_LOC.pickle', 'rb') as f:
    #     NOD_LOC = pickle.load(f)
    with open('NOD_TTT.pickle', 'rb') as f:
        NOD_TTT = pickle.load(f)
    # with open('NOD_SPT.pickle', 'rb') as f:
    #     NOD_SPT = pickle.load(f)
    print('load from pickle file running time:', (time.time() - bb))
