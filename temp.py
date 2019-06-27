import mosek
import time
import requests
import numpy as np
import pandas as pd
from tqdm import trange
from time import sleep


# get the best route from origin to destination
def get_routing(olng, olat, dlng, dlat):
    url = create_url(olng, olat, dlng, dlat, steps='true', annotations='false')
    response, code = call_url(url)
    if code:
        return response['routes'][0]['legs'][0]
    else:
        return None


# get the duration of the best route from origin to destination
def get_duration(olng, olat, dlng, dlat):
    url = create_url(olng, olat, dlng, dlat, steps='false', annotations='false')
    response, code = call_url(url)
    if code:
        return response['routes'][0]['duration']
    else:
        return None


# generate the request in url format
def create_url(olng, olat, dlng, dlat, steps='false', annotations='false'):
    ghost = '0.0.0.0'
    gport = 5000
    return 'http://{0}:{1}/route/v1/driving/{2},{3};{4},{5}?alternatives=false&steps=' \
           '{6}&annotations={7}&geometries=geojson'.format(
            ghost, gport, olng, olat, dlng, dlat, steps, annotations)


# send the request and get the response in Json format
def call_url(url):
    while True:
        try:
            response = requests.get(url, timeout=1)
            json_response = response.json()
            code = json_response['code']
            if code == 'Ok':
                return json_response, True
            else:
                print('Error: %s' % (json_response['message']))
                return json_response, False
        except requests.exceptions.Timeout:
            # print('Time out: %s' % url)
            time.sleep(2)
        except Exception as err:
            print('Failed: %s' % url)
            # return None
            time.sleep(2)


if __name__ == "__main__":
    a = get_duration(-73.98590087890625, 40.76803970336913, -73.9839859008789, 40.73009872436523)
    b = get_duration(-73.97929382324219, 40.75576400756836, -73.98801422119139, 40.75846862792969)
    c = get_duration(-73.9915771484375, 40.7447509765625, -73.97570037841797, 40.7654685974121)

    print(a, b, c)
    # b = get_routing(-73.958875, 40.820005, -73.958871, 40.820003)
    # # print(a, b['distance'])
    # #
    # # for i in trange(4, desc='1st loop'):
    # #     for j in trange(5, desc='2nd loop'):
    # #         for k in trange(50, desc='3nd loop', leave=False):
    # #             sleep(0.01)
    #
    # dates = pd.date_range('20130101', periods=6)
    # df = pd.DataFrame(np.arange(24).reshape((6, 4)), index=dates, columns=['A', 'B', 'C', 'D'])
    # print(df)
    # df.loc['20130101', 'B'] = 2
    # print(df.loc['20130101', 'B'])
    #

