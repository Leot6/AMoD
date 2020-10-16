"""
utility functions are found here
"""

import csv
import datetime
import numpy as np
from lib.simulator.config import *


# print and save results
def print_results(model):
    count_reqs = 0
    count_rejs = 0

    # (SWSD) both waiting time (wt) and travel delay (td) constraints have been satisfied
    count_served_1 = 0      # num of reqs that have been finished
    count_onboard_1 = 0     # num of reqs that are currently on board
    wait_time_1 = 0.0       # mean waiting time
    in_veh_time_1 = 0.0     # mean in-vehicle travel time
    in_veh_delay_1 = 0.0    # mean in-vehicle delay
    detour_factor_1 = 0.0   # mean in-vehicle travel detour

    # (VWSD) only travel delay constraint has been satisfied
    count_served_2 = 0
    count_onboard_2 = 0
    wait_time_2 = 0.0
    in_veh_time_2 = 0.0
    in_veh_delay_2 = 0.0
    detour_factor_2 = 0.0

    # (VWVD) both waiting time and travel delay constraints have been violated
    count_served_3 = 0
    count_onboard_3 = 0
    wait_time_3 = 0.0
    in_veh_time_3 = 0.0
    in_veh_delay_3 = 0.0
    detour_factor_3 = 0.0

    # comparison between estimated arrival time and actually arrival time
    count_earlier_than_Etp = 0
    count_later_than_Etp = 0
    count_earlier_than_Etd = 0
    count_later_than_Etd = 0

    # analyze requests whose demand time is within the period of study
    for req in model.reqs:
        if T_WARM_UP <= req.Cep <= T_WARM_UP + T_STUDY:
            count_reqs += 1
            if not np.isclose(req.Tp, -1.0):       # reqs that are accepted
                if not np.isclose(req.Td, -1.0):                # reqs that have been finished

                    if req.Tp < req.Etp:
                        count_earlier_than_Etp += 1
                    elif req.Tp > req.Etp * 1.2:
                        count_later_than_Etp += 1

                    if req.Td < req.Etd:
                        count_earlier_than_Etd += 1
                    elif req.Td > req.Etd * 1.2:
                        count_later_than_Etd += 1

                    if req.Td <= req.Cld:
                        if req.Tp <= req.Clp_backup:                         # satisfy both wt and td
                            count_served_1 += 1
                            wait_time_1 += req.Tp - req.Cep
                            in_veh_time_1 += req.Td - req.Tp
                            in_veh_delay_1 += req.Td - req.Tp - req.Ts
                            detour_factor_1 += req.D
                        else:                                                # violate wt but satisfy td
                            count_served_2 += 1
                            wait_time_2 += req.Tp - req.Cep
                            in_veh_time_2 += req.Td - req.Tp
                            in_veh_delay_2 += req.Td - req.Tp - req.Ts
                            detour_factor_2 += req.D
                    else:                                                    # violate both wt and td
                        count_served_3 += 1
                        wait_time_3 += req.Tp - req.Cep
                        in_veh_time_3 += req.Td - req.Tp
                        in_veh_delay_3 += req.Td - req.Tp - req.Ts
                        detour_factor_3 += req.D
                        # if req.Tp <= req.Clp_backup:
                        #     print()
                        #     print('SWVD: req', req.id, ', close wt', req.Clp_backup - req.Tp,
                        #           ', viol td', req.Cld - req.Td)
                        #     print()
                        # assert req.Tp > req.Clp_backup
                else:                                          # reqs that are currently on board
                    if req.Tp <= req.Clp_backup:                             # satisfy wt
                        count_onboard_1 += 1
                        wait_time_1 += req.Tp - req.Cep
                    elif req.Tp <= req.Clp_backup + (MAX_DELAY - MAX_WAIT):  # violate wt but expected to satisfy td
                        count_onboard_2 += 1
                        wait_time_2 += req.Tp - req.Cep
                    else:                                                    # violate wt and will violate td
                        count_onboard_3 += 1
                        wait_time_3 += req.Tp - req.Cep

            else:                                  # reqs that are rejected
                count_rejs += 1
    count_service_1 = count_served_1 + count_onboard_1
    count_service_2 = count_served_2 + count_onboard_2
    count_service_3 = count_served_3 + count_onboard_3
    assert count_rejs + count_service_1 + count_service_2 + count_service_3 == count_reqs

    if not count_served_1 == 0:
        wait_time_1 /= (count_served_1 + count_onboard_1)
        in_veh_time_1 /= count_served_1
        in_veh_delay_1 /= count_served_1
        detour_factor_1 /= count_served_1
    if not count_served_2 == 0:
        wait_time_2 /= (count_served_2 + count_onboard_2)
        in_veh_time_2 /= count_served_2
        in_veh_delay_2 /= count_served_2
        detour_factor_2 /= count_served_2
    if not count_served_3 == 0:
        wait_time_3 /= (count_served_3 + count_onboard_3)
        in_veh_time_3 /= count_served_3
        in_veh_delay_3 /= count_served_3
        detour_factor_3 /= count_served_3

    # service rate
    served_rate_1 = 0.0
    serving_rate_1 = 0.0
    service_rate_1 = 0.0
    served_rate_2 = 0.0
    serving_rate_2 = 0.0
    service_rate_2 = 0.0
    served_rate_3 = 0.0
    serving_rate_3 = 0.0
    service_rate_3 = 0.0
    if not count_reqs == 0:
        served_rate_1 = round(100.0 * count_served_1 / count_reqs, 2)
        serving_rate_1 = round(100.0 * count_onboard_1 / count_reqs, 2)
        service_rate_1 = round(100.0 * count_service_1 / count_reqs, 2)
        served_rate_2 = round(100.0 * count_served_2 / count_reqs, 2)
        serving_rate_2 = round(100.0 * count_onboard_2 / count_reqs, 2)
        service_rate_2 = round(100.0 * count_service_2 / count_reqs, 2)
        served_rate_3 = round(100.0 * count_served_3 / count_reqs, 2)
        serving_rate_3 = round(100.0 * count_onboard_3 / count_reqs, 2)
        service_rate_3 = round(100.0 * count_service_3 / count_reqs, 2)

    # total reqs
    service_rate_0 = service_rate_1 + service_rate_2 + service_rate_3
    count_service_0 = count_service_1 + count_service_2 + count_service_3
    served_rate_0 = served_rate_1 + served_rate_2 + served_rate_3
    count_served_0 = count_served_1 + count_served_2 + count_served_3
    serving_rate_0 = serving_rate_1 + serving_rate_2 + serving_rate_3
    count_onboard_0 = count_onboard_1 + count_onboard_2 + count_onboard_3

    wait_time_0 = 0.0
    in_veh_time_0 = 0.0
    in_veh_delay_0 = 0.0
    detour_factor_0 = 0.0
    if not count_served_0 == 0:
        wait_time_0 = (wait_time_1 * count_service_1 + wait_time_2 * count_service_2 +
                       wait_time_3 * count_service_3) / count_service_0
        in_veh_delay_0 = (in_veh_delay_1 * count_served_1 + in_veh_delay_2 * count_served_2 +
                          in_veh_delay_3 * count_served_3) / count_served_0

    wait_time_0 = round(wait_time_0, 2)
    in_veh_delay_0 = round(in_veh_delay_0, 2)
    wait_time_1 = round(wait_time_1, 2)
    in_veh_delay_1 = round(in_veh_delay_1, 2)
    wait_time_2 = round(wait_time_2, 2)
    in_veh_delay_2 = round(in_veh_delay_2, 2)
    wait_time_3 = round(wait_time_3, 2)
    in_veh_delay_3 = round(in_veh_delay_3, 2)

    # vehicle performance
    veh_service_dist = 0.0
    veh_service_time = 0.0
    veh_rebl_dist = 0.0
    veh_rebl_time = 0.0
    veh_load_by_dist = 0.0
    veh_load_by_time = 0.0
    for veh in model.vehs:
        veh_service_dist += veh.Ds
        veh_service_time += veh.Ts
        veh_rebl_dist += veh.Dr
        veh_rebl_time += veh.Tr
        if not veh.Ds + veh.Dr == 0:
            veh_load_by_dist += veh.Ld / (veh.Ds + veh.Dr)
        veh_load_by_time += veh.Lt / T_STUDY
    veh_service_dist /= model.V
    veh_service_time /= model.V
    veh_service_time_percent = 100.0 * veh_service_time / T_STUDY
    veh_rebl_dist /= model.V
    veh_rebl_time /= model.V
    veh_rebl_time_percent = 100.0 * veh_rebl_time / T_STUDY
    veh_load_by_dist /= model.V
    veh_load_by_time /= model.V

    print('*' * 80)
    print(model)
    print('simulation results:')
    print('  - requests (%d):' % count_reqs)
    print('    + ALL_: served rate: %.2f%% (%d), serving rate: %.2f%% (%d), service rate: %.2f%% (%d)'
          % (served_rate_0, count_served_0, serving_rate_0, count_onboard_0, service_rate_0, count_service_0))
    print('    +     : waiting time: %.2f s, in-vehicle travel delay: %.2f s' % (wait_time_0, in_veh_delay_0))
    print('    + SWSD: served rate: %.2f%% (%d), serving rate: %.2f%% (%d), service rate: %.2f%% (%d)'
          % (served_rate_1, count_served_1, serving_rate_1, count_onboard_1, service_rate_1, count_service_1))
    print('    +     : waiting time: %.2f s, in-vehicle travel delay: %.2f s' % (wait_time_1, in_veh_delay_1))
    print('    + VWSD: served rate: %.2f%% (%d), serving rate: %.2f%% (%d), service rate: %.2f%% (%d)'
          % (served_rate_2, count_served_2, serving_rate_2, count_onboard_2, service_rate_2, count_service_2))
    print('    +     : waiting time: %.2f s, in-vehicle travel delay: %.2f s' % (wait_time_2, in_veh_delay_2))
    print('    + VWVD: served rate: %.2f%% (%d), serving rate: %.2f%% (%d), service rate: %.2f%% (%d)'
          % (served_rate_3, count_served_3, serving_rate_3, count_onboard_3, service_rate_3, count_service_3))
    print('    +     : waiting time: %.2f s, in-vehicle travel delay: %.2f s' % (wait_time_3, in_veh_delay_3))
    # print('    + in-vehicle travel time: %.2f s, detour factor: %.2f' % (in_veh_time, detour_factor))
    print('  - vehicles:')
    print('    + vehicle average load: %.2f (distance weighted), %.2f (time weighted)'
          % (veh_load_by_dist, veh_load_by_time))
    print('    + vehicle service distance travelled: %.1f m' % veh_service_dist)
    print('    + vehicle service time travelled: %.1f s' % veh_service_time)
    print('    + vehicle service time percentage: %.1f%%' % veh_service_time_percent)
    print('    + vehicle rebalancing distance travelled: %.1f m' % veh_rebl_dist)
    print('    + vehicle rebalancing time travelled: %.1f s' % veh_rebl_time)
    print('    + vehicle rebalancing time percentage: %.1f%%' % veh_rebl_time_percent)
    print('*' * 80)

    print(f'earlier than Etp: {count_earlier_than_Etp/count_reqs*100:.2f}%({count_earlier_than_Etp})')
    print(f'later than Etp: {count_later_than_Etp / count_reqs*100:.2f}%({count_later_than_Etp})')
    print(f'earlier than Etd: {count_earlier_than_Etd / count_reqs*100:.2f}%({count_earlier_than_Etd})')
    print(f'later than Etd: {count_later_than_Etd / count_reqs*100:.2f}%({count_later_than_Etd})')

    # wait_time_0
    # in_veh_delay_0
    for req in model.reqs:
        if T_WARM_UP <= req.Cep <= T_WARM_UP + T_STUDY:
            if not np.isclose(req.Tp, -1.0):

                if np.isclose(req.Td, -1.0):
                    wait_time_1 += req.Tp - req.Cep
                    pass
                else:
                    wait_time_1 += req.Tp - req.Cep
                    in_veh_delay_1 += req.Td - req.Tp - req.Ts
                    pass



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
    #        round(wait_time_1, 2), round(in_veh_delay_1, 2), round(detour_factor_1, 2), round(in_veh_time_1, 2)]
    # writer.writerow(row)
    # row = [COEF_WAIT, model.start_time, end_time, runtime, 'runtime:', mean_runtime,
    #        'load (d):', round(veh_load_by_dist, 2), 'load (t):', round(veh_load_by_time, 2),
    #        'VWST:', str(service_rate_2) + '% (' + str(count_service_2) + ')',
    #        str(served_rate_2) + '% (' + str(count_served_2) + ')',
    #        str(serving_rate_2) + '% (' + str(count_onboard_2) + ')',
    #        round(wait_time_2, 2), round(in_veh_delay_2, 2), round(detour_factor_2, 2), round(in_veh_time_2, 2)]
    # writer.writerow(row)
    # row = [None, None, None, None, None, None, None, None, None, None,
    #        'VWVT:', str(service_rate_3) + '% (' + str(count_service_3) + ')',
    #        str(served_rate_3) + '% (' + str(count_served_3) + ')',
    #        str(serving_rate_3) + '% (' + str(count_onboard_3) + ')',
    #        round(wait_time_3, 2), round(in_veh_delay_3, 2), round(detour_factor_3, 2), round(in_veh_time_3, 2)]
    # writer.writerow(row)
    # f.close()
    #
    # # write and save the result analysis 11111
    # f = open('output/results11111.csv', 'a')
    # writer = csv.writer(f)
    # # writer.writerow(['date', 'method', 'fleet', 'capacity', 'coef_wait',  'reqs counted', 'all service', 'all served',
    # #                  'all WT', 'all TD', 'SWSD service', 'SWSD served', 'SWSD WT', 'SWSD TD', 'Travel time', 'Load'])
    # row = [DATE, DISPATCHER, model.V, str(model.K) + ' (' + str(RIDESHARING_SIZE) + ')', COEF_WAIT, count_reqs,
    #        count_service_0, count_served_0, wait_time_0, in_veh_delay_0,
    #        count_service_1, count_served_1, wait_time_1, in_veh_delay_1, TRAVEL_TIME, round(veh_load_by_time, 2)]
    # writer.writerow(row)
    # f.close()

    # write and save data of all requests
    f = open('output/requests.csv', 'w')
    writer = csv.writer(f)
    writer.writerow(['id', 'olng', 'olat', 'dlng', 'dlat', 'Ts', 'Tr', 'Cep', 'Tp', 'Td', 'WT', 'TD', 'D'])
    for req in model.reqs:
        if T_WARM_UP <= req.Cep <= T_WARM_UP + T_STUDY:
            row = [req.id, req.olng, req.olat, req.dlng, req.dlat, req.Ts, req.Tr, req.Cep, req.Tp, req.Td,
                   req.Tp - req.Cep if req.Tp >= 0 else -1, req.Td - req.Tp - req.Ts if req.Td >= 0 else -1, req.D]
            writer.writerow(row)
    f.close()

    # # write and save data of all requests
    # f = open('output/requests.csv', 'w')
    # writer = csv.writer(f)
    # writer.writerow(['ID', 'Ts', 'WT', 'TD', 'D'])
    # for req in model.reqs:
    #     if T_WARM_UP <= req.Cep <= T_WARM_UP + T_STUDY:
    #         if req.Tp >= 0 and req.Td >= 0:
    #             row = [req.id, req.Ts, round(req.Tp - req.Cep, 2), round(req.Td - req.Tp - req.Ts, 2), round(req.D, 2)]
    #         writer.writerow(row)
    # f.close()
