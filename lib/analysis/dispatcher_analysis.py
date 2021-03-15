

import time
import pickle
import copy
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import sys
import os
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
os.sys.path.append(root_path)
from tqdm import tqdm
from lib.simulator.config import TRIP_NUM, FLEET_SIZE, IS_DEBUG
from lib.dispatcher.osp.osp_assign import ILP_assign
from lib.dispatcher.rtv.rtv_graph import change_rtv_graph_param, search_feasible_trips
from lib.dispatcher.sba.single_req_batch_assign import ridesharing_match_sba
from lib.dispatcher.gi.greedy_insertion import heuristic_insertion
from lib.analysis.animation_generator import anim, anim_compare_sches_found, anim_sche

current_file_path = os.path.abspath(os.path.dirname(__file__))
# numreqs_file_path = f'{current_file_path}/numreqs-data'
# replay_file_path = f'{current_file_path}/replay-data-gitignore'
# if not os.path.exists(numreqs_file_path):
#     os.mkdir(numreqs_file_path)
# if not os.path.exists(replay_file_path):
#     os.mkdir(replay_file_path)


class DispatcherAnalysis:

    def __init__(self, is_replay=False):
        self.numreqs_data_osp = []
        self.numreqs_data_rtv1 = []
        self.numreqs_data_rtv2 = []
        self.numreqs_data_sba = []
        self.numreqs_data_gi = []
        self.anime_data = []
        self.is_replay = is_replay

    def run_comparison_analysis(self, vehs, reqs, queue, reqs_picking, reqs_unassigned, prev_assigned_edges, T,
                                osp_rids_assigned, osp_num_edges, osp_run_time):
        reqs_pool = sorted(reqs_picking.union(reqs_unassigned), key=lambda r: r.id) + queue

        print(f'T = {T}, {len(queue)}/{len(reqs_pool)} reqs')

        num_reqs_new = len(queue)
        num_reqs_pool = len(reqs_pool)
        self.append_numreqs_data_osp(num_reqs_new, len(osp_rids_assigned) - len(reqs_picking), num_reqs_pool,
                                     osp_num_edges, len(osp_rids_assigned), osp_run_time)

        # rtv1_time = time.time()
        # change_rtv_graph_param(1000, 5000, 5000)
        # rtv1_rids_assigned, rtv1_vids_assigned, rtv1_sches_assigned, rtv1_num_edges = \
        #     ridesharing_match_rtv(vehs, reqs_pool, reqs_picking, prev_assigned_edges, T)
        # rtv1_run_time = round((time.time() - rtv1_time), 2)
        # self.append_numreqs_data_rtv1(num_reqs_new, len(rtv1_rids_assigned) - len(reqs_picking), num_reqs_pool,
        #                               rtv1_num_edges, len(rtv1_rids_assigned), rtv1_run_time)

        rtv2_time = time.time()
        change_rtv_graph_param(0.2, 1750, 30)
        rtv2_rids_assigned, rtv2_vids_assigned, rtv2_sches_assigned2, rtv2_num_edges = \
            ridesharing_match_rtv(vehs, reqs_pool, reqs_picking, prev_assigned_edges, T)
        rtv2_run_time = round((time.time() - rtv2_time), 2)
        self.append_numreqs_data_rtv2(num_reqs_new, len(rtv2_rids_assigned) - len(reqs_picking), num_reqs_pool,
                                      rtv2_num_edges, len(rtv2_rids_assigned), rtv2_run_time)

        sba_time = time.time()
        sba_rids_assigned, sba_vids_assigned, sba_sches_assigned, sba_num_edges = ridesharing_match_sba(vehs, queue, T)
        sba_run_time = round((time.time() - sba_time), 2)

        self.append_numreqs_data_sba(num_reqs_new, sba_num_edges, len(sba_rids_assigned), sba_run_time)

        gi_time = time.time()
        gi_rids_assigned = ridesharing_match_gi(vehs, reqs, queue, T)
        gi_run_time = round((time.time() - gi_time), 2)
        gi_num_edges = 0
        for v in vehs:
            gi_num_edges += len(v.candidate_sches_gi)
        self.append_numreqs_data_gi(num_reqs_new, gi_num_edges, len(gi_rids_assigned), gi_run_time)

        self.add_anime_data(vehs)
        # compare_vt_data(reqs_pool, osp_num_edges, rtv1_num_edges, rtv2_num_edges, osp_rids_assigned, rtv1_rids_assigned,
        #                 rtv2_rids_assigned, queue, reqs_picking, sba_rids_assigned, gi_rids_assigned)

    def append_numreqs_data_osp(self, numreqs_new, num_matched_new, numreqs_pool, num_edges, num_matched, run_time):
        self.numreqs_data_osp.append((numreqs_new, num_matched_new, numreqs_pool, num_edges, num_matched, run_time))

        osp_numreqs_new = [e[0] for e in self.numreqs_data_osp]
        osp_numreqs_pool = [e[2] for e in self.numreqs_data_osp]
        print('OSP-Full reqs new', osp_numreqs_new)
        print('OSP-Full req pool', osp_numreqs_pool)

        osp_num_edge = [e[3] for e in self.numreqs_data_osp]
        osp_req_matc = [e[1] for e in self.numreqs_data_osp]
        osp_run_time = round(np.mean([e[5] for e in self.numreqs_data_osp]), 2)
        print('OSP-Full num edges', osp_num_edge)
        print('OSP-Full req match', osp_req_matc)
        print('OSP-Full mean time', osp_run_time)

    def append_numreqs_data_rtv1(self, numreqs_new, num_matched_new, numreqs_pool, num_edges, num_matched, run_time):
        self.numreqs_data_rtv1.append((numreqs_new, num_matched_new, numreqs_pool, num_edges, num_matched, run_time))

        rtv_num_edge = [e[3] for e in self.numreqs_data_rtv1]
        rtv_req_matc = [e[1] for e in self.numreqs_data_rtv1]
        rtv_run_time = round(np.mean([e[5] for e in self.numreqs_data_rtv1]), 2)
        print('RTV-Full num edges', rtv_num_edge)
        print('RTV-Full req match', rtv_req_matc)
        print('RTV-Full mean time', rtv_run_time)

    def append_numreqs_data_rtv2(self, numreqs_new, num_matched_new, numreqs_pool, num_edges, num_matched, run_time):
        self.numreqs_data_rtv2.append((numreqs_new, num_matched_new, numreqs_pool, num_edges, num_matched, run_time))

        rtv2_num_edge = [e[3] for e in self.numreqs_data_rtv2]
        rtv2_req_matc = [e[1] for e in self.numreqs_data_rtv2]
        rtv2_run_time = round(np.mean([e[5] for e in self.numreqs_data_rtv2]), 2)
        print('RTV num edges', rtv2_num_edge)
        print('RTV req match', rtv2_req_matc)
        print('RTV mean time', rtv2_run_time)

    def append_numreqs_data_sba(self, numreqs_new, num_edges, num_matched_new, run_time):
        self.numreqs_data_sba.append((numreqs_new, num_edges, num_matched_new, run_time))

        sba_num_edge = [e[1] for e in self.numreqs_data_sba]
        sba_req_matc = [e[2] for e in self.numreqs_data_sba]
        sba_run_time = round(np.mean([e[3] for e in self.numreqs_data_sba]), 2)
        print('SBA num edges', sba_num_edge)
        print('SBA req match', sba_req_matc)
        print('SBA mean time', sba_run_time)

    def append_numreqs_data_gi(self, numreqs_new, num_edges, num_matched_new, run_time):
        self.numreqs_data_gi.append((numreqs_new, num_edges, num_matched_new, run_time))

        gi_num_edge = [e[1] for e in self.numreqs_data_gi]
        gi_req_matc = [e[2] for e in self.numreqs_data_gi]
        gi_run_time = round(np.mean([e[3] for e in self.numreqs_data_gi]), 2)
        print('GI num edges', gi_num_edge)
        print('GI req match', gi_req_matc)
        print('GI mean time', gi_run_time)

    def add_anime_data(self, vehs):
        self.anime_data.append((copy.deepcopy(vehs)))

    def save_analysis_data(self, dispatcher, PS=''):
        with open(f'{numreqs_file_path}/numreqs_OSP_{TRIP_NUM}_{FLEET_SIZE}{PS}.pickle', 'wb') as f:
            pickle.dump(self.numreqs_data_osp, f)
        with open(f'{numreqs_file_path}/numreqs_RTV1_{TRIP_NUM}_{FLEET_SIZE}{PS}.pickle', 'wb') as f:
            pickle.dump(self.numreqs_data_rtv1, f)
        with open(f'{numreqs_file_path}/numreqs_RTV2_{TRIP_NUM}_{FLEET_SIZE}{PS}.pickle', 'wb') as f:
            pickle.dump(self.numreqs_data_rtv2, f)
        with open(f'{numreqs_file_path}/numreqs_SBA_{TRIP_NUM}_{FLEET_SIZE}{PS}.pickle', 'wb') as f:
            pickle.dump(self.numreqs_data_sba, f)
        with open(f'{numreqs_file_path}/numreqs_GI_{TRIP_NUM}_{FLEET_SIZE}{PS}.pickle', 'wb') as f:
            pickle.dump(self.numreqs_data_gi, f)
        if not self.is_replay:
            with open(f'{replay_file_path}/anime_data_{dispatcher}_{TRIP_NUM}_{FLEET_SIZE}{PS}.pickle', 'wb') as f:
                pickle.dump(self.anime_data, f)


# because we cannot import functions from rtv_main.py, so we just paste it here
def ridesharing_match_rtv(vehs, reqs_pool, reqs_picking, prev_assigned_edges, T):
    if IS_DEBUG:
        print('    -T = %d, building RTV graph ...' % T)
        a1 = time.time()
    veh_trip_edges = search_feasible_trips(vehs, reqs_pool, T)
    num_edges = len(veh_trip_edges)
    veh_trip_edges.extend(prev_assigned_edges)
    if IS_DEBUG:
        print('        a1 running time:', round((time.time() - a1), 2))
    if IS_DEBUG:
        print('    -T = %d, start ILP assign with %d edges...' % (T, len(veh_trip_edges)))
        a2 = time.time()
    rids_assigned, vids_assigned, sches_assigned = ILP_assign(veh_trip_edges, reqs_pool, reqs_picking)
    if IS_DEBUG:
        print('        a2 running time:', round((time.time() - a2), 2))
    return rids_assigned, vids_assigned, sches_assigned, num_edges


def ridesharing_match_gi(vehs, reqs, reqs_new, T):
    rids_assigned = []
    for req in reqs_new:
        req_params = [req.id, req.onid, req.dnid, req.Clp, req.Cld]
        best_veh, best_sche = heuristic_insertion(vehs, req_params, T)
        if best_veh:
            best_veh.build_route(best_sche, reqs, T)
            rids_assigned.append(req.id)
    return rids_assigned


def compare_vt_data(reqs_pool, osp_num_edges, rtv1_num_edges, rtv2_num_edges, osp_rids_assigned, rtv1_rids_assigned,
                    rtv2_rids_assigned, queue, reqs_picking, sba_rids_assigned, gi_rids_assigned):

    print(f'we have {len(reqs_pool)} reqs in pool')
    print(f'OSP finds {osp_num_edges} trips and assigns {len(osp_rids_assigned)} reqs')
    print(f'RTV1 finds {rtv1_num_edges} trips and assigns {len(rtv1_rids_assigned)} reqs')
    print(f'RTV2 finds {rtv2_num_edges} trips and assigns {len(rtv2_rids_assigned)} reqs')
    print(f'we have {len(queue)} reqs, they matched {len(osp_rids_assigned)- len(reqs_picking)} / '
          f'{len(rtv1_rids_assigned)- len(reqs_picking)} / {len(rtv2_rids_assigned)- len(reqs_picking)} / '
          f'{len(sba_rids_assigned)} / {len(gi_rids_assigned)} (OSP/RTV1/RTV2/SBA/GI)')


def compare_match_status_at_each_interval(PS=''):
    col_numreqs_new = 'numreqs_new'
    col_numreqs_matched_new = 'numreqs_matched_new'
    col_numreqs_pool = 'numreqs_pool'
    col_numedges = 'numedges'
    col_numreqs_matched = 'numreqs_matched'
    col_run_time = 'run_time'

    start_idx = 0
    end_idx = 240

    # numreqs_data
    with open(f'{numreqs_file_path}/numreqs_OSP_{TRIP_NUM}_{FLEET_SIZE}{PS}.pickle', 'rb') as f:
        numreqs_data = pickle.load(f)
    df0 = pd.DataFrame(numreqs_data, columns=[col_numreqs_new, col_numreqs_matched_new, col_numreqs_pool,
                                              col_numedges, col_numreqs_matched, col_run_time])
    with open(f'{numreqs_file_path}/numreqs_RTV1_{TRIP_NUM}_{FLEET_SIZE}{PS}.pickle', 'rb') as f:
        numreqs_data = pickle.load(f)
    df1 = pd.DataFrame(numreqs_data, columns=[col_numreqs_new, col_numreqs_matched_new, col_numreqs_pool,
                                              col_numedges, col_numreqs_matched, col_run_time])
    with open(f'{numreqs_file_path}/numreqs_RTV2_{TRIP_NUM}_{FLEET_SIZE}{PS}.pickle', 'rb') as f:
        numreqs_data = pickle.load(f)
    df2 = pd.DataFrame(numreqs_data, columns=[col_numreqs_new, col_numreqs_matched_new, col_numreqs_pool,
                                              col_numedges, col_numreqs_matched, col_run_time])
    with open(f'{numreqs_file_path}/numreqs_SBA_{TRIP_NUM}_{FLEET_SIZE}{PS}.pickle', 'rb') as f:
        numreqs_data = pickle.load(f)
    df3 = pd.DataFrame(numreqs_data, columns=[col_numreqs_new, col_numedges, col_numreqs_matched_new, col_run_time])
    with open(f'{numreqs_file_path}/numreqs_GI_{TRIP_NUM}_{FLEET_SIZE}{PS}.pickle', 'rb') as f:
        numreqs_data = pickle.load(f)
    df4 = pd.DataFrame(numreqs_data, columns=[col_numreqs_new, col_numedges, col_numreqs_matched_new, col_run_time])

    print(f'osp matched {df0[col_numreqs_matched_new].sum()} reqs, mean response time: {df0[col_run_time].mean():.2f}')
    print(f'rtv1 matched {df1[col_numreqs_matched_new].sum()} reqs, mean response time: {df1[col_run_time].mean():.2f}')
    print(f'rtv2 matched {df2[col_numreqs_matched_new].sum()} reqs, mean response time: {df2[col_run_time].mean():.2f}')
    print(f'sba matched {df3[col_numreqs_matched_new].sum()} reqs, mean response time: {df3[col_run_time].mean():.2f}')
    print(f'gi matched {df4[col_numreqs_matched_new].sum()} reqs, mean response time: {df4[col_run_time].mean():.2f}')
    improve = round((df0[col_numreqs_matched_new].sum() - df2[col_numreqs_matched_new].sum())/53081 * 100, 2)
    print(f'osp matched {improve}% more than rtv2')

    print(f'num of intervals: {df0.shape[0]}')
    # df0 = df0.iloc[1::2]

    df0 = df0.iloc[start_idx:end_idx]
    df1 = df1.iloc[start_idx:end_idx]
    df2 = df2.iloc[start_idx:end_idx]
    df3 = df3.iloc[start_idx:end_idx]
    df4 = df4.iloc[start_idx:end_idx]

    print(f'num of intervals: {df0.shape[0]}')

    df_newreqs = pd.concat([df0[[col_numreqs_new, col_numreqs_matched_new]], df1[col_numreqs_matched_new],
                            df2[col_numreqs_matched_new], df3[col_numreqs_matched_new], df4[col_numreqs_matched_new]],
                           axis=1)
    df_newreqs.columns = [col_numreqs_new, 'numreqs_matched_osp', 'numreqs_matched_rtv1',
                          'numreqs_matched_rtv2', 'numreqs_matched_sba', 'numreqs_matched_gi']

    df_reqspool = pd.concat([df0[[col_numreqs_pool, col_numreqs_matched]], df1[col_numreqs_matched],
                             df2[col_numreqs_matched]], axis=1)
    df_reqspool.columns = [col_numreqs_pool, 'numreqs_matched_osp', 'numreqs_matched_rtv1', 'numreqs_matched_rtv2']

    df_edges = pd.concat([df0[[col_numreqs_pool, col_numedges]], df1[col_numedges], df2[col_numedges],
                          df3[col_numedges], df4[col_numedges]], axis=1)
    df_edges.columns = [col_numreqs_pool, 'numedges_osp', 'numedges_rtv1', 'numedges_rtv2',
                        'numedges_rtv3', 'numedges_rtv4']

    df_newreqs.plot()
    df_reqspool.plot()
    df_edges.plot()
    plt.show()

    df_newreqs1 = df_newreqs.T
    df_edges1 = df_edges.T
    df_newreqs1.to_csv('newreqs.csv')
    df_edges1.to_csv('edges.csv')


def sample_from_anime_data():
    start_time = time.time()
    sample_step = 10
    file_name = f'anime_data_OSP_800k_3200.pickle'
    print('...loading file...')
    print(f'file name: {replay_file_path}/{file_name}')
    with open(f'{replay_file_path}/{file_name}', 'rb') as f:
        anime_data = pickle.load(f)
    print('...running time : %.05f seconds' % (time.time() - start_time))
    samepled_anime_data = []
    for frame_vehs in tqdm(anime_data, desc='frames'):
        sampled_vehs = []
        for veh in tqdm(frame_vehs, desc='vehs', leave=False):
            if veh.id % sample_step == 0:
                sampled_vehs.append(veh)
        samepled_anime_data.append(sampled_vehs)
    print('...dumping file...')
    with open(f'{replay_file_path}/one_tenth_{file_name}', 'wb') as f:
        pickle.dump(samepled_anime_data, f)
    print('...running time : %.05f seconds' % (time.time() - start_time))


def generate_anime_from_data():
    start_time = time.time()
    file_name = f'anime_data_OSP_800k_3200.pickle'
    print('...loading file...')
    print(f'file name: {replay_file_path}/{file_name}')
    with open(f'{replay_file_path}/{file_name}', 'rb') as f:
        anime_data = pickle.load(f)
    print('...running time : %.05f seconds' % (time.time() - start_time))
    print('...Outputing simulation video...')

    numreqs_data = pd.read_csv('newreqs.csv', index_col=0).values
    numedges_data = pd.read_csv('edges.csv', index_col=0).values
    anime_osp = anim(anime_data, numreqs_data, numedges_data)
    anime_rtv = anim_compare_sches_found(anime_data, numreqs_data, numedges_data, 'RTV')
    anime_sba = anim_compare_sches_found(anime_data, numreqs_data, numedges_data, 'SBA')
    anime_gi = anim_compare_sches_found(anime_data, numreqs_data, numedges_data, 'GI')
    print('...running time : %.05f seconds' % (time.time() - start_time))


if __name__ == '__main__':
    start_time = time.time()
    # compare_match_status_at_each_interval()

    # sample_from_anime_data()
    generate_anime_from_data()

    # with open('anime_sche_data_195.pickle', 'rb') as f:
    #     anime_data = pickle.load(f)
    # [veh, trip_k, sches_searched, sches_searched_rtv, best_sche] = anime_data
    # # a = anim_sche(copy.deepcopy(veh), trip_k, sches_searched, best_sche, 'OSP')
    # b = anim_sche(copy.deepcopy(veh), trip_k, sches_searched_rtv, best_sche, 'RTV')

    print('...running time : %.05f seconds' % (time.time() - start_time))


