"""
utility functions are found here
"""

import csv
import datetime
import numpy as np
import pandas as pd
from lib.simulator.config import *


# print and save results
def print_results(model):
    count_reqs = 0
    count_rejs = 0
    reqs_stat = []
    vehs_stat = []

    # analyze requests whose demand time is within the period of study
    for req in model.reqs:
        if T_WARM_UP <= req.Cep <= T_WARM_UP + T_STUDY:
            count_reqs += 1
            pass
            if np.isclose(req.Tp, -1.0):
                count_rejs += 1
                pass
            else:
                max_wait = req.Clp_backup - req.Tr
                actual_wait = round(req.Tp - req.Tr, 2)
                max_delay = round(req.Cld - req.Tr - req.Ts, 2)
                actual_delay = round(req.Td - req.Tr - req.Ts, 2) if not np.isclose(req.Td, -1.0) else -1
                extra_delay = actual_delay - max_delay
                if extra_delay > 1:
                    req.update_price_act(extra_delay)
                actual_price = req.price_act
                reqs_stat.append((req.id, req.Ds, req.Ts, max_wait, actual_wait, max_delay, actual_delay, actual_price))
    # reqs that are accepted
    df_reqs_ALL = pd.DataFrame(
        reqs_stat, columns=['id', 'Ds', 'Ts', 'MaxWait', 'ActualWait', 'MaxDelay', 'ActualDelay', 'ActualPrice'])
    req_total_dist = df_reqs_ALL['Ds'].sum() / 1000
    req_mean_dist = df_reqs_ALL['Ds'].mean() / 1000

    def compute_service_rate(df_reqs, num_reqs):
        count_onboard = df_reqs[(df_reqs['ActualDelay'] == -1)].shape[0]
        count_served = df_reqs.shape[0] - count_onboard
        count_service = count_onboard + count_served
        serving_rate = 100.0 * count_onboard / num_reqs
        served_rate = 100.0 * count_served / num_reqs
        service_rate = serving_rate + served_rate
        mean_Ts = df_reqs['Ts'].mean()
        mean_wait = df_reqs['ActualWait'].mean()
        mean_delay = df_reqs[(df_reqs['ActualDelay'] != -1)]['ActualDelay'].mean()

        return count_onboard, count_served, count_service, serving_rate, served_rate, service_rate, \
               mean_Ts, mean_wait, mean_delay

    count_onboard_ALL, count_served_ALL, count_service_ALL, serving_rate_ALL, served_rate_ALL, service_rate_ALL, \
    mean_Ts_ALL, mean_wait_ALL, mean_delay_ALL = compute_service_rate(df_reqs_ALL, count_reqs)

    # reqs that violate td
    df_reqs_VD = df_reqs_ALL[(df_reqs_ALL['ActualDelay'] > df_reqs_ALL['MaxDelay'])]
    # df_reqs_VD.to_csv('output/reqs_VD.csv', index=False)
    count_onboard_VD, count_served_VD, count_service_VD, serving_rate_VD, served_rate_VD, service_rate_VD, \
    mean_Ts_VD, mean_wait_VD, mean_delay_VD = compute_service_rate(df_reqs_VD, count_service_ALL)

    # # reqs that satisfy both waiting time (wt) and travel delay (td) constraints
    # df_reqs_SWSD = df_reqs_ALL[(df_reqs_ALL['ActualWait'] <= df_reqs_ALL['MaxWait']) &
    #                            (df_reqs_ALL['ActualDelay'] <= df_reqs_ALL['MaxDelay'])]
    # # reqs that violate both wt and td
    # df_reqs_VWVD = df_reqs_ALL[(df_reqs_ALL['ActualWait'] > df_reqs_ALL['MaxWait']) &
    #                            (df_reqs_ALL['ActualDelay'] > df_reqs_ALL['MaxDelay'])]
    # # reqs that violate wt
    # df_reqs_VW = df_reqs_ALL[(df_reqs_ALL['ActualWait'] > df_reqs_ALL['MaxWait'])]

    # vehicle performance
    for veh in model.vehs:
        vehs_stat.append((veh.id, veh.Ts, veh.Ts_empty, veh.Lt, veh.Tr, veh.Ds, veh.Ds_empty, veh.Ld, veh.Dr,
                          len(veh.served_rids_STUDY), len(veh.onboard_rids_STUDY)))
    df_vehs = pd.DataFrame(vehs_stat, columns=['id', 'Ts', 'Ts_empty', 'Lt', 'Tr', 'Ds', 'Ds_empty', 'Ld', 'Dr',
                                               'num_req_served', 'num_req_onboard'])
    veh_total_reqs = df_vehs['num_req_served'].sum() + df_vehs['num_req_onboard'].sum()
    veh_mean_time = df_vehs['Ts'].mean()
    veh_mean_time_percent = 100.0 * veh_mean_time / T_STUDY
    veh_mean_empty_time = df_vehs['Ts_empty'].mean()
    veh_empty_time_percent = 100.0 * veh_mean_empty_time / veh_mean_time
    veh_mean_load_by_time = df_vehs['Lt'].sum() / df_vehs['Ts'].sum()
    veh_mean_rebl_time = df_vehs['Tr'].mean()
    veh_rebl_time_percent = 100.0 * veh_mean_rebl_time / veh_mean_time

    veh_mean_dist = df_vehs['Ds'].mean() / 1000
    veh_total_dist = df_vehs['Ds'].sum() / 1000
    veh_mean_empty_dist = df_vehs['Ds_empty'].mean() / 1000
    veh_total_empty_dist = df_vehs['Ds_empty'].sum() / 1000
    veh_mean_rebl_dist = df_vehs['Dr'].mean() / 1000
    veh_mean_load_by_dist = df_vehs['Ld'].sum() / (veh_total_dist * 1000)

    # system performance
    income = df_reqs_ALL['ActualPrice'].sum()
    outcome = veh_total_dist * 1
    profit = income - outcome

    print('*' * 80)
    print(model)
    print('simulation results:')
    print(f'  - requests ({count_reqs}):')
    print(f'    + total req distance: {req_total_dist:.2f} km, mean: {req_mean_dist:.2f} km')
    print(f'    + ALL_: served: {served_rate_ALL:.2f}% ({count_served_ALL}), '
          f'serving: {serving_rate_ALL:.2f}% ({count_onboard_ALL}), '
          f'service: {service_rate_ALL:.2f}% ({count_service_ALL})')
    print(f'    +     : Ts: {mean_Ts_ALL:.2f} s, waiting: {mean_wait_ALL:.2f} s, delay: {mean_delay_ALL:.2f} s')
    print(f'    + __VD: served: {served_rate_VD:.2f}% ({count_served_VD}), '
          f'serving: {serving_rate_VD:.2f}% ({count_onboard_VD}), '
          f'service: {service_rate_VD:.2f}% ({count_service_VD})')
    print(f'    +     : Ts: {mean_Ts_VD:.2f} s, waiting: {mean_wait_VD:.2f} s, delay: {mean_delay_VD:.2f} s')
    print(f'  - vehicles ({veh_total_reqs}):')
    print(f'    + vehicle service distance: {veh_total_dist:.2f} km, mean: {veh_mean_dist:.2f} km')
    # print(f'    + vehicle empty distance: {veh_total_empty_dist:.2f} km, mean: {veh_mean_empty_dist:.2f} km')
    print(f'    + vehicle mean service time: {veh_mean_time:.2f} s ({veh_mean_time_percent:.2f}%), '
          f'empty time: {veh_mean_empty_time:.2f} s ({veh_empty_time_percent:.2f}%)')
    print(f'    + vehicle mean rebalancing time: {veh_mean_rebl_time:.2f} s ({veh_rebl_time_percent:.2f}%),'
          f' distance: {veh_mean_rebl_dist:.2f} km')
    print(f'    + vehicle average load: {veh_mean_load_by_dist:.2f} (distance weighted), '
          f'{veh_mean_load_by_time:.2f} (time weighted)')
    print(f'  - system :')
    print(f'    + income: {income:.2f}, outcome: {outcome:.2f}, profit:{profit:.2f}')
    print('*' * 80)

    # # write and save the result analysis
    # f = open('output/results.csv', 'a')
    # writer = csv.writer(f)
    # # writer.writerow(['scenario', 'demand starts', 'demand ends', 'demand number',
    # #                      'fleet size', 'capacity',  'max wait (s)', 'max wait (s)', 'method', 'interval (s)',
    # #                      'service type', 'total service rate', 'served rate (finished)', 'serving rate (in-car)',
    # #                      'mean wt', 'mean ivd', 'mean detour', 'mean ivt'])
    # DMD_EST = DMD_SST + datetime.timedelta(seconds=model.T)
    # row = [DMD_STR, DMD_SST, DMD_EST, str(count_reqs) + ' (' + str(DMD_VOL * 100) + '%)',
    #        model.V, str(model.K) + ' (' + str(RIDESHARING_SIZE) + ')', MAX_WAIT, MAX_DELAY, DISPATCHER, INT_ASSIGN,
    #        'SWST:', str(service_rate_1) + '% (' + str(count_service_1) + ')',
    #        str(served_rate_1) + '% (' + str(count_served_1) + ')',
    #        str(serving_rate_1) + '% (' + str(count_onboard_1) + ')',
    #        round(mean_wait_1, 2), round(in_veh_delay_1, 2), round(detour_factor_1, 2), round(in_veh_time_1, 2)]
    # writer.writerow(row)
    # f.close()


