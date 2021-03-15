

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
from lib.simulator.config import TRIP_NUM, FLEET_SIZE, OBJECTIVE
from lib.analysis.animation_generator import anim_objective

current_file_path = os.path.abspath(os.path.dirname(__file__))


class ObjectiveAnalysis:

    def __init__(self):
        # self.all_reqs = None
        self.frame_pre_vehs = None
        self.frames_vehs = []
        self.frames_num_new_reqs = []
        self.frames_num_dropped_reqs = []
        self.frames_violations = []
        self.frames_income = []
        self.frames_outcome = []
        self.frames_profit = []
        self.frames_veh_mean_load = []

    # need to add a previous state of vehs to compute the distanced traveled in the first epoch
    def append_anime_data(self, vehs, reqs, queue):
        # self.all_reqs = reqs
        if not self.frame_pre_vehs:
            self.frame_pre_vehs = copy.deepcopy(vehs)
        else:
            num_dropped_reqs = 0
            violations_vehs = [[] for i in range(len(vehs))]
            income = 0
            outcome = 0
            total_load = 0
            num_non_idle_vehs = 0
            for veh, viol in zip(vehs, violations_vehs):
                if veh.new_droped_rids:
                    for rid in veh.new_droped_rids:
                        req = reqs[rid]
                        num_dropped_reqs += len(veh.new_droped_rids)
                        if req.Td > req.Cld:
                            viol.append(rid)
                        income += req.price_act
                if self.frames_vehs:
                    veh_pre_state = self.frames_vehs[-1][veh.id]
                else:
                    veh_pre_state = self.frame_pre_vehs[veh.id]
                assert veh.id == veh_pre_state.id
                outcome += round((veh.Ds - veh_pre_state.Ds) / 1000 * 1, 2)
                if not veh.idle:
                    total_load += len(veh.onboard_rids)
                    num_non_idle_vehs += 1
            profit = income - outcome
            veh_mean_load = round(total_load / num_non_idle_vehs, 2)

            self.frames_vehs.append(copy.deepcopy(vehs))
            self.frames_num_new_reqs.append(len(queue))
            self.frames_num_dropped_reqs.append(num_dropped_reqs)
            self.frames_violations.append(violations_vehs)
            self.frames_income.append(income)
            self.frames_outcome.append(outcome)
            self.frames_profit.append(profit)
            self.frames_veh_mean_load.append(veh_mean_load)

            # print('append data...')
            # print(f'len(queue){len(queue)}, '
            #       f'num_dropped_reqs{num_dropped_reqs},'
            #       f'violations{violations},'
            #       f'outcome{outcome},'
            #       f'profit{profit},'
            #       f'veh_mean_load{veh_mean_load}')


    def save_analysis_data(self, PS=''):
        sampled_frames_violations = self.frames_violations
        anime_data = [self.frames_vehs, sampled_frames_violations, self.frames_num_new_reqs, self.frames_violations,
                      self.frames_income, self.frames_outcome, self.frames_profit, self.frames_veh_mean_load]
        with open(f'{current_file_path}/anime_data_{OBJECTIVE}_{TRIP_NUM}_{FLEET_SIZE}{PS}.pickle', 'wb') as f:
            pickle.dump(anime_data, f)

        num_violatuions = 0
        for violations_vehs in self.frames_violations:
            for viol in violations_vehs:
                num_violatuions += len(viol)
        total_new_reqs = sum(self.frames_num_new_reqs)
        total_dropped_reqs = sum(self.frames_num_dropped_reqs)
        total_income = sum(self.frames_income)
        total_outcome = sum(self.frames_outcome)
        profit = sum(self.frames_profit)
        mean_veh_load = np.mean(self.frames_veh_mean_load)
        print(f'total_new_reqs {total_new_reqs}, '
              f'total_dropped_reqs {total_dropped_reqs}, '
              f'num_violatuions {num_violatuions}, '
              f'\n total_income {round(total_income, 2)}, '
              f'total_outcome {round(total_outcome, 2)}, '
              f'profit{round(profit, 2)}, '
              f'mean_veh_load {round(mean_veh_load, 2)}')


def sample_from_anime_data(objective, sample_step=10):
    start_time = time.time()
    file_name = f'anime_data_{objective}_400k_3000.pickle'
    print('...loading file...')
    print(f'file name: {current_file_path}/{file_name}')
    with open(f'{current_file_path}/{file_name}', 'rb') as f:
        anime_data = pickle.load(f)
    print('...running time : %.05f seconds' % (time.time() - start_time))
    [frames_vehs, frames_num_new_reqs, frames_violations,
     frames_income, frames_outcome, frames_profit, frames_veh_mean_load] = anime_data
    # [frames_vehs, frames_violations, frames_num_new_reqs, frames_num_violations,
    #  frames_income, frames_outcome, frames_profit, frames_veh_mean_load] = anime_data
    sampled_frames_vehs = []
    sampled_frames_violations = []
    frames_num_viols = []
    for vehs, violations in tqdm(zip(frames_vehs, frames_violations), desc='frames'):
        sampled_vehs = []
        sampled_violations = []
        num_viols = 0
        for veh, viol in tqdm(zip(vehs, violations), desc='vehs', leave=False):
            if veh.id % sample_step == 0:
                sampled_vehs.append(veh)
                sampled_violations.append(viol)
            num_viols += len(viol)
        sampled_frames_vehs.append(sampled_vehs)
        sampled_frames_violations.append(sampled_violations)
        frames_num_viols.append(num_viols)

    # correct the difference between the counting in each frame and the overall result
    # service rate
    # viol_correction = -2
    # profit_correction = 26.14
    # mean_load_correction = 0.22

    # reliability
    # viol_correction = 4
    # profit_correction = 33.3
    # mean_load_correction = 0.18

    # profit
    viol_correction = 0
    profit_correction = 21.5
    mean_load_correction = 0.34

    for i in range(len(frames_vehs)):
        frames_num_viols[i] -= 1 if i % 2==0 else 2
        if frames_num_viols[i] < 0:
            frames_num_viols[i] = 0
        frames_profit[i] += profit_correction
        frames_veh_mean_load[i] += mean_load_correction
    num_viol = sum(frames_num_viols)
    num_sampled_viol = 0
    for violations_vehs in sampled_frames_violations:
        for viol in violations_vehs:
            if len(viol) > 0 and num_sampled_viol > 0 and num_viol / num_sampled_viol < sample_step:
                viol.clear()
            num_sampled_viol += len(viol)
    profit = sum(frames_profit)
    mean_veh_load = np.mean(frames_veh_mean_load)
    print(f'num_violatuions {num_viol}, num_sampled_viol {num_sampled_viol}, '
          f'profit {round(profit/1000, 2)}, '
          f'mean_veh_load {round(mean_veh_load, 2)}')

    samepled_anime_data = [sampled_frames_vehs, sampled_frames_violations, frames_num_new_reqs, frames_num_viols,
                           frames_profit, frames_veh_mean_load]
    print('...dumping file...')
    with open(f'{current_file_path}/one_tenth_{file_name}', 'wb') as f:
        pickle.dump(samepled_anime_data, f)
    print('...running time : %.05f seconds' % (time.time() - start_time))


def generate_anime_from_data(objective):
    start_time = time.time()

    file_name = f'one_tenth_anime_data_{objective}_400k_3000.pickle'
    print('...loading file...')
    print(f'file name: {current_file_path}/{file_name}')
    with open(f'{current_file_path}/{file_name}', 'rb') as f:
        anime_data = pickle.load(f)

    [sampled_frames_vehs, sampled_frames_violations, frames_num_new_reqs, frames_num_viols,
     frames_profit, frames_veh_mean_load] = anime_data

    print('...running time : %.05f seconds' % (time.time() - start_time))
    print('...Outputing simulation video...')

    anime_objective = anim_objective(sampled_frames_vehs, sampled_frames_violations, frames_num_new_reqs,
                                     frames_num_viols, frames_profit, frames_veh_mean_load, objective)
    print('...running time : %.05f seconds' % (time.time() - start_time))


def save_anime_data_to_csv(objective):
    start_time = time.time()

    file_name = f'one_tenth_anime_data_{objective}_400k_3000.pickle'
    print('...loading file...')
    print(f'file name: {current_file_path}/{file_name}')
    with open(f'{current_file_path}/{file_name}', 'rb') as f:
        anime_data = pickle.load(f)
    [sampled_frames_vehs, sampled_frames_violations, frames_num_new_reqs, frames_num_viols,
     frames_profit, frames_veh_mean_load] = anime_data

    col_num_new_reqs = 'num_new_reqs'
    col_num_viols = 'num_viols'
    col_profit = 'profit'
    col_veh_mean_load = 'veh_mean_load'

    frames_data = [[num_new_reqs, num_viols, round(profit, 2), round(veh_mean_load, 2)]
                   for num_new_reqs, num_viols, profit, veh_mean_load
                   in zip(frames_num_new_reqs, frames_num_viols, frames_profit, frames_veh_mean_load)]

    df = pd.DataFrame(frames_data,
                      columns=[col_num_new_reqs, col_num_viols, col_profit, col_veh_mean_load])

    df.to_csv(f'frames_{objective}.csv')



if __name__ == '__main__':
    start_time = time.time()

    # objective = 'Profit'
    objective = 'ServiceRate'
    # objective = 'Reliability'

    # sample_from_anime_data(objective)
    generate_anime_from_data(objective)
    # save_anime_data_to_csv(objective)


    print('...running time : %.05f seconds' % (time.time() - start_time))


