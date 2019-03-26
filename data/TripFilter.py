"""
filter out the trips starts/ends within Manhattan area
"""

import time
import pandas as pd
import sys
sys.path.append('..')
from lib.Route import get_duration


def IsPtInPoly(lng, lat):
    # coordinates around Manhattan
    point_list = [(-74.022, 40.697), (-73.972, 40.711), (-73.958, 40.749), (-73.938, 40.771), (-73.937, 40.786),
                  (-73.928, 40.794), (-73.926, 40.801), (-73.932, 40.808), (-73.933, 40.835), (-73.924, 40.851),
                  (-73.911, 40.866), (-73.909, 40.873), (-73.927, 40.879), (-74.011, 40.751)]
    iSum = 0
    iCount = len(point_list)

    if iCount < 3:
        return False

    for i in range(iCount):
        # vlng: vertex longtitude,  vlat: vertex latitude

        vlng1 = point_list[i][0]
        vlat1 = point_list[i][1]

        if i == iCount - 1:
            vlng2 = point_list[0][0]
            vlat2 = point_list[0][1]
        else:
            vlng2 = point_list[i + 1][0]
            vlat2 = point_list[i + 1][1]

        if ((lat >= vlat1) and (lat < vlat2)) or ((lat >= vlat2) and (lat < vlat1)):
            if abs(vlat1 - vlat2) > 0:
                pLon = vlng1 - ((vlng1 - vlng2) * (vlat1 - lat)) / (vlat1 - vlat2);

                if pLon < lng:
                    iSum += 1

    if iSum % 2 != 0:
        return True
    else:
        return False


if __name__ == '__main__':
    stime = time.time()

    # labels' names
    # # # for green taxi
    # pickup_time = 'lpep_pickup_datetime'
    # dropoff_time = 'Lpep_dropoff_datetime'
    # olng = 'Pickup_longitude'
    # olat = 'Pickup_latitude'
    # dlng = 'Dropoff_longitude'
    # dlat = 'Dropoff_latitude'
    # passenger_count = 'Passenger_count'
    # trip_dist = 'Trip_distance'

    # for yellow taxi
    pickup_time = 'tpep_pickup_datetime'
    dropoff_time = 'tpep_dropoff_datetime'
    olng = 'pickup_longitude'
    olat = 'pickup_latitude'
    dlng = 'dropoff_longitude'
    dlat = 'dropoff_latitude'
    passenger_count = 'passenger_count'
    trip_dist = 'trip_distance'

    # # read all trips
    # CSV_FILE_PATH = '/Users/leot/Downloads/green_tripdata_2016-05.csv'
    # df = pd.read_csv(CSV_FILE_PATH)
    # print('number of all trips:', df.shape[0])
    # print(df.head(2))  # get the label for pickup time in csv file
    # # filter out trips in one day
    # df1 = df.loc[lambda x: x[pickup_time].str.startswith('2016-05-07')]
    # df1[pickup_time] = pd.to_datetime(df1[pickup_time])
    # df1.sort_values(pickup_time, inplace=True)
    # df1.to_csv('yellow-taxi-20160502.csv', index=False)
    # df1.head(2).to_csv('temp.csv', index=False)  # a sample file to read the labels' names
    #
    # df1 = pd.read_csv('yellow-taxi-20160502.csv')
    # print('number of trips in selected day:', df1.shape[0])
    # # filter out useful parameters: time, lng & lat, passenger number...
    # df2 = df1.loc[:, [pickup_time, passenger_count, olng, olat, dlng, dlat, trip_dist, dropoff_time]]
    # print(df2.head(2))  # check the format
    # # roughly filter out the trips in a square area
    # df3 = df2[(df2[olng] > -74.0300) & (df2[olng] < -73.9030)
    #          & (df2[olat] > 40.6950) & (df2[olat] < 40.8825)
    #          & (df2[dlng] > -74.0300) & (df2[dlng] < -73.9030)
    #          & (df2[dlat] > 40.6950) & (df2[dlat] < 40.8825)]
    # print('number of trips after rough filter:', df3.shape[0])
    # # filter out the trips starting within Manhattan
    # df4 = df3[df3.apply(lambda x: IsPtInPoly(x[olng], x[olat]), axis=1)]
    # # filter out the trips ending in Manhattan
    # df5 = df4[df4.apply(lambda x: IsPtInPoly(x[dlng], x[dlat]), axis=1)]
    # print('number of trips in Manhattan:', df5.shape[0])
    # # filter out the trips longer than 2 min
    # df6 = df5[df5.apply(lambda x: get_duration(x[olng], x[olat], x[dlng], x[dlat]) > 120, axis=1)]
    # print('number of trips longer than 2 min :', df6.shape[0])
    # df6.to_csv('Manhattan-green-taxi-20160507.csv', index=False)

    # # rename the column index
    # df7 = pd.read_csv('Manhattan-yellow-taxi-20160507.csv')
    # df7 = df7.loc[:, [pickup_time, passenger_count, olng, olat, dlng, dlat, trip_dist, dropoff_time]]
    # df7.columns = ['ptime', 'npass', 'olng', 'olat', 'dlng', 'dlat', 'dist', 'dtime']
    # df7.to_csv('Manhattan-yellow-taxi-20160507-1.csv', index=False)

    # # merge green taxi and yellow taxi together
    # df8 = pd.read_csv('Manhattan-green-taxi-20160507.csv')
    # df8['taxi'] = 'green'
    # print('number of green taxi trips:', df8.shape[0])
    # df9 = pd.read_csv('Manhattan-yellow-taxi-20160507.csv')
    # df9['taxi'] = 'yellow'
    # print('number of green taxi trips:', df9.shape[0])
    # frames = [df8, df9]
    # df10 = pd.concat(frames, ignore_index=True)
    # df10.sort_values('ptime', inplace=True)
    # print('number of all taxi trips:', df10.shape[0])
    # df10.to_csv('Manhattan-taxi-20160507.csv', index=False)

    df11 = pd.read_csv('Manhattan-taxi-20160507.csv')
    print('number of all taxi trips in 20160507:', df11.shape[0])

    runtime = time.time() - stime
    print('...running time : %.05f seconds' % runtime)

