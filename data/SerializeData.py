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
    # NOD_TTT = pd.read_csv('./Manhattan-graph/time-table-week.csv', index_col=0).values
    NOD_SPT = pd.read_csv('./Manhattan-graph/path-table-week.csv', index_col=0).values
    # EDG_NOD = pd.read_csv('./Manhattan-graph/edges.csv').values.tolist()
    # EDG_TTH = pd.read_csv('./Manhattan-graph/time-sat.csv', index_col=0).value

    print('load from csv file running time:', (time.time() - aa))

    # with open('REQ_DATA_2013.pickle', 'wb') as f:
    #     pickle.dump(REQ_DATA_2013, f)
    # with open('STN_LOC.pickle', 'wb') as f:
    #     pickle.dump(STN_LOC, f)
    # with open('NOD_LOC.pickle', 'wb') as f:
    #     pickle.dump(NOD_LOC, f)
    # with open('NOD_TTT.pickle', 'wb') as f:
    #     pickle.dump(NOD_TTT, f)
    with open('NOD_SPT.pickle', 'wb') as f:
        pickle.dump(NOD_SPT, f)
    # with open('EDG_NOD.pickle', 'wb') as f:
    #     pickle.dump(EDG_NOD, f)
    # with open('EDG_TTH.pickle', 'wb') as f:
    #     pickle.dump(EDG_TTH, f)

    bb = time.time()
    # with open('REQ_DATA_2013.pickle', 'rb') as f:
    #     REQ_DATA = pickle.load(f)
    # with open('STN_LOC.pickle', 'rb') as f:
    #     STN_LOC = pickle.load(f)
    # with open('NOD_LOC.pickle', 'rb') as f:
    #     NOD_LOC = pickle.load(f)
    # with open('NOD_TTT.pickle', 'rb') as f:
    #     NOD_TTT = pickle.load(f)
    with open('NOD_SPT.pickle', 'rb') as f:
        NOD_SPT = pickle.load(f)
    # with open('EDG_NOD.pickle', 'rb') as f:
    #     EDG_NOD = pickle.load(f)
    # with open('EDG_TTH.pickle', 'rb') as f:
    #     EDG_TTH = pickle.load(f)
    print('load from pickle file running time:', (time.time() - bb))
