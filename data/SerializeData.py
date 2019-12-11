"""
serialize data to pickle file to save time on initialization
"""

import pickle
import time
import pandas as pd

if __name__ == '__main__':
    aa = time.time()
    date = '20130511'
    REQ_DATA = pd.read_csv('Manhattan-taxi-' + date + '.csv')
    # STN_LOC = pd.read_csv('./Manhattan-graph/stations-630.csv')
    # NOD_LOC = pd.read_csv('./Manhattan-graph/nodes.csv').values.tolist()
    # NOD_TTT = pd.read_csv('./Manhattan-graph/time-table-sun.csv', index_col=0).values
    # NOD_SPT = pd.read_csv('./Manhattan-graph/path-table-sun.csv', index_col=0).values

    print('load from csv file running time:', (time.time() - aa))

    with open('NYC_REQ_DATA_' + date + '.pickle', 'wb') as f:
        pickle.dump(REQ_DATA, f)
    # with open('STN_LOC.pickle', 'wb') as f:
    #     pickle.dump(STN_LOC, f)
    # with open('NOD_LOC.pickle', 'wb') as f:
    #     pickle.dump(NOD_LOC, f)
    # with open('NOD_TTT.pickle', 'wb') as f:
    #     pickle.dump(NOD_TTT, f)
    # with open('NOD_SPT.pickle', 'wb') as f:
    #     pickle.dump(NOD_SPT, f)

    bb = time.time()
    with open('NYC_REQ_DATA_' + date + '.pickle', 'rb') as f:
        REQ_DATA = pickle.load(f)
    # with open('STN_LOC.pickle', 'rb') as f:
    #     STN_LOC = pickle.load(f)
    # with open('NOD_LOC.pickle', 'rb') as f:
    #     NOD_LOC = pickle.load(f)
    # with open('NOD_TTT.pickle', 'rb') as f:
    #     NOD_TTT = pickle.load(f)
    # with open('NOD_SPT.pickle', 'rb') as f:
    #     NOD_SPT = pickle.load(f)
    print('load from pickle file running time:', (time.time() - bb))
