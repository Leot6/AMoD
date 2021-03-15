

import time
import pickle
from tqdm import tqdm
import os
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
os.sys.path.append(root_path)
from lib.simulator.config import TRIP_NUM, FLEET_SIZE
from lib.dispatcher.osp.osp_main import get_prev_assigned_edges, ridesharing_match_osp
from lib.analysis.online_analysis import OnlineAnalysis, replay_file_path


def replay_simulation():
    print('loading pickle file....')
    start_time = time.time()
    with open(f'{replay_file_path}/replay_OSP_data_{TRIP_NUM}_{FLEET_SIZE}.pickle', 'rb') as f:
        replay_data = pickle.load(f)
    print('...running time : %.05f seconds' % (time.time() - start_time))
    print('start replaying....')

    # replay_start_data = replay_data[0]
    #
    # with open(f'{replay_file_path}/new_replay_OSP_data_{TRIP_NUM}_{FLEET_SIZE}.pickle', 'wb') as f:
    #     pickle.dump(replay_start_data, f)

    analysis = OnlineAnalysis(is_replay=True)
    for (vehs, reqs, queue, reqs_picking, reqs_unassigned, T) in tqdm(replay_data, desc='replay'):
        reqs_new = queue
        reqs_prev = sorted(reqs_picking.union(reqs_unassigned), key=lambda r: r.id)
        prev_assigned_edges = get_prev_assigned_edges(vehs, reqs)

        osp_time = time.time()
        osp_rids_assigned, osp_vids_assigned, osp_sches_assigned, osp_num_edges = \
            ridesharing_match_osp(vehs, reqs_new, reqs_prev, reqs_picking, prev_assigned_edges, T)
        osp_run_time = round((time.time() - osp_time), 2)

        analysis.run_comparison_analysis(vehs, reqs, queue, reqs_picking, reqs_unassigned, prev_assigned_edges, T,
                                         osp_rids_assigned, osp_num_edges, osp_run_time)
    analysis.save_analysis_data('OSP', 'test')


if __name__ == '__main__':
    start_time = time.time()
    replay_simulation()
    print('...running time : %.05f seconds' % (time.time() - start_time))

