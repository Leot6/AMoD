
import sys
import os

import pandas as pd

ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(ROOT_PATH)
from src.value_function.score_net import *
from src.value_function.replay_buffer import *


class ValueFunction(object):
    def __init__(self, num_locations: int = 4091):
        self.lr = 0.01                  # learning rate
        self.gamma = 0.90                # reward discount factor
        self.buffer_size = 1080         # replay buffer size
        self.batch_size_train = 32      # mini-batch size for training
        self.tau = 0.05                 # for soft update of target network parameters
        # self.target_update_iter = 10    # how often to update the target network
        self.max_iter_offline_train = 10000

        # self.eval_net_file_name = f"NET-{round(self.lr*100)}-{round(self.gamma*100)}" \
        #                           f"-{DISPATCHER}-F{FLEET_SIZE[0]}-C{VEH_CAPACITY[0]}-{len(SIMULATION_DAYs)}D"
        self.eval_net_file_path = f"{PARTIAL_PATH_TO_REPLAY_BUFFER_DATA}{EVAL_NET_FILE_NAME}.pickle"
        self.eval_net = ScoreNet(num_locations)
        self.target_net = ScoreNet(num_locations)
        self.target_net.load_state_dict(self.eval_net.state_dict())
        self.optimizer = torch.optim.Adam(self.eval_net.parameters(), lr=self.lr)
        self.loss_func = nn.MSELoss()

        self.replay_buffer = ReplayBuffer(self.buffer_size)
        self.replay_buffer_data_path = f"{PARTIAL_PATH_TO_REPLAY_BUFFER_DATA}" \
                                       f"RB-{DISPATCHER}-F{FLEET_SIZE[0]}-C{VEH_CAPACITY[0]}-{len(SIMULATION_DAYs)}D.pickle"

        self.learn_iter_count = 0

    # ("is_reoptimization" only influences the calculation of rewards in "compute_post_decision_state".)
    def compute_expected_values_for_veh_trip_pairs(self, num_of_new_reqs: int, vehs: list[Veh], veh_trip_pairs: list,
                                                   system_time_sec: int, is_reoptimization: bool = False):
        # 1. Compute the post-decision state (and the reward) resulting from each vehicle-trip pair.
        [normalized_system_time_at_next_state, vt_pairs_visiting_node_ids_at_next_state,
         vt_pairs_normalized_remaining_delays_at_next_state, vt_pairs_num_of_visiting_nodes_at_next_state,
         vt_pairs_reward_for_transition_from_current_to_next_state,
         assumed_vt_pairs_normalized_num_of_nearby_veh_at_next_state] = \
            compute_post_decision_state_for_vt_pairs(veh_trip_pairs, vehs, system_time_sec, is_reoptimization)
        assumed_normalized_num_of_new_reqs_at_next_state = num_of_new_reqs / FLEET_SIZE[0]

        # 2. Get the expected value of being in the post-decision state.
        post_state_values = use_a_net_to_get_scores_for_a_list_of_veh_states(
            self.eval_net,
            normalized_system_time_at_next_state,
            vt_pairs_visiting_node_ids_at_next_state,
            vt_pairs_normalized_remaining_delays_at_next_state,
            vt_pairs_num_of_visiting_nodes_at_next_state,
            assumed_vt_pairs_normalized_num_of_nearby_veh_at_next_state,
            assumed_normalized_num_of_new_reqs_at_next_state)

        # 3. Get the expected value for vt_pair, calculated as Q(s, a) = R + gamma * V(s').
        expected_vt_values = copy.copy(vt_pairs_reward_for_transition_from_current_to_next_state)
        for idx, post_state_value in enumerate(post_state_values):
            expected_vt_values[idx] += self.gamma * post_state_value

        return expected_vt_values

    def offline_batch_learn(self):
        t = timer_start()
        for i in range(self.max_iter_offline_train):
            sampled_exps = self.replay_buffer.sample(1)
            for exp in sampled_exps:
                self.batch_learn_from_an_experience(exp, show_process=True)
                if self.learn_iter_count % 2000 == 0:
                    self.save_eval_net_to_pickle_file()
                    print(f"[INFO] Net is saved to {self.eval_net_file_path}.")
        self.save_eval_net_to_pickle_file()
        print(f"[INFO] Offline Policy Evaluation is done and the net has been saved to {self.eval_net_file_path}. "
              f"(runtime = {str(timedelta(seconds=(datetime.now() - t).seconds))})")

    def online_batch_learn(self, num_of_new_reqs: int, vehs: list[Veh],
                           candidate_veh_trip_pairs: list, selected_veh_trip_pair_indices: list[int],
                           system_time_sec: int, is_reoptimization: bool = False):
        new_experience = \
            store_vehs_current_state_and_post_decision_state_as_an_experience(num_of_new_reqs, vehs,
                                                                              candidate_veh_trip_pairs,
                                                                              selected_veh_trip_pair_indices,
                                                                              system_time_sec, is_reoptimization)
        self.batch_learn_from_an_experience(new_experience)

    def batch_learn_from_an_experience(self, exp: Experience, show_process=False):
        # 1. Get the target value of being in the current state.
        post_state_values = use_a_net_to_get_scores_for_a_list_of_veh_states(
            self.target_net,
            exp.normalized_system_time_at_next_state,
            exp.vehs_visiting_node_ids_at_next_state,
            exp.vehs_normalized_remaining_delays_at_next_state,
            exp.vehs_num_of_visiting_nodes_at_next_state,
            exp.assumed_vehs_normalized_num_of_nearby_vehs_at_next_state,
            exp.assumed_normalized_num_of_new_reqs_at_next_state)
        rewards = exp.vehs_reward_for_transition_from_current_to_next_state
        target_values = [0] * len(rewards)
        for idx, reward in enumerate(rewards):
            target_values[idx] = reward + self.gamma * post_state_values[idx]

        # 2. Feed the data to the net for training.
        batch_x1, batch_x2, batch_x3, batch_x4, batch_x5, batch_x6 = \
            format_batch_input_data_to_tensor_type(exp.normalized_system_time_at_current_state,
                                                   exp.vehs_visiting_node_ids_at_current_state,
                                                   exp.vehs_normalized_remaining_delays_at_current_state,
                                                   exp.vehs_num_of_visiting_nodes_at_current_state,
                                                   exp.vehs_normalized_num_of_nearby_vehs_at_current_state,
                                                   exp.normalized_num_of_new_reqs_at_current_state)

        batch_y = torch.unsqueeze(torch.FloatTensor(target_values), 1)

        loss = self.loss_func(self.eval_net(batch_x1, batch_x2, batch_x3, batch_x4, batch_x5, batch_x6), batch_y)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        self.learn_iter_count += 1
        if show_process and self.learn_iter_count % 10 == 0:
            print(f"[DEBUG-T] ({DISPATCHER}-{self.gamma}) ({self.learn_iter_count}/{self.max_iter_offline_train}) "
                  f"loss {loss.item():.5f}, target_values: ({rewards[0]}, {post_state_values[0]:.2f}), "
                  f"({rewards[3]}, {post_state_values[3]:.2f})")
        if show_process and self.learn_iter_count % 100 == 0:
            print(f"[DEBUG-T] post_state_values {post_state_values[:5]}")

        # 3. Update target net.
        self.soft_update_target_net()

    # Soft update model parameters. θ_target = τ*θ_local + (1 - τ)*θ_target
    def soft_update_target_net(self):
        for target_param, eval_param in zip(self.target_net.parameters(), self.eval_net.parameters()):
            target_param.data.copy_(self.tau * eval_param.data + (1.0 - self.tau) * target_param.data)

    # Convert and store the vehicles' states at current epoch and their post-decision states as an experience.
    # ("is_reoptimization" only influences the calculation of rewards in "compute_post_decision_state".)
    def store_vehs_state_to_replay_buffer(self, num_of_new_reqs: int, vehs: list[Veh],
                                          candidate_veh_trip_pairs: list, selected_veh_trip_pair_indices: list[int],
                                          system_time_sec: int, is_reoptimization: bool = False):
        new_experience = \
            store_vehs_current_state_and_post_decision_state_as_an_experience(num_of_new_reqs, vehs,
                                                                              candidate_veh_trip_pairs,
                                                                              selected_veh_trip_pair_indices,
                                                                              system_time_sec, is_reoptimization)

        # Print the attributes of different vehicle in one experiences.
        exp = new_experience
        num_of_positive_reward = 0
        num_of_negative_reward = 0
        num_of_zero_reward = 0
        total_reward = 0
        for veh_id in range(0, 1500):
            if exp.vehs_reward_for_transition_from_current_to_next_state[veh_id] > 0:
                num_of_positive_reward += 1
            elif exp.vehs_reward_for_transition_from_current_to_next_state[veh_id] == 0:
                num_of_zero_reward += 1
            else:
                num_of_negative_reward += 1
            total_reward += exp.vehs_reward_for_transition_from_current_to_next_state[veh_id]
            # print(f"[DEBUG-T] time_now {round(exp.normalized_system_time_at_current_state, 3)}, "
            #       f"new_reqs {round(exp.normalized_num_of_new_reqs_at_current_state, 3)}, "
            #       f"nearby_vehs {round(exp.vehs_normalized_num_of_nearby_vehs_at_current_state[veh_id], 3)}, "
            #       f"next_nearby_vehs {round(exp.assumed_vehs_normalized_num_of_nearby_vehs_at_next_state[veh_id], 3)}, "
            #       f"reward {round(exp.vehs_reward_for_transition_from_current_to_next_state[veh_id], 3)}")
        print(f"num_of_new_reqs {num_of_new_reqs}, total_reward {total_reward}, "
              f"num_of_positive_reward {num_of_positive_reward}, num_of_negative_reward {num_of_negative_reward}, "
              f"num_of_zero_reward {num_of_zero_reward}")

        self.replay_buffer.add(new_experience)

    def save_replay_buffer_to_pickle_file(self):
        t = timer_start()
        with open(self.replay_buffer_data_path, 'wb') as f:
            pickle.dump(self.replay_buffer, f)
        print(f"[INFO] Replay Buffer is saved with {len(self.replay_buffer)} experiences. ({timer_end(t)})")

    def load_replay_buffer_from_pickle_file(self):
        t = timer_start()
        with open(self.replay_buffer_data_path, "rb") as f:
            self.replay_buffer = pickle.load(f)
        print(f"[INFO] Replay Buffer is loaded with {len(self.replay_buffer)} experiences. ({timer_end(t)})")

    def save_eval_net_to_pickle_file(self):
        save_net_to_file(self.eval_net, self.eval_net_file_path)

    def load_eval_net_from_pickle_file(self, file_path=None):
        if file_path:
            self.eval_net_file_path = file_path
        self.eval_net = restore_net_from_file(self.eval_net_file_path)
        self.target_net.load_state_dict(self.eval_net.state_dict())
        print(f"[INFO] Net is loaded from {self.eval_net_file_path}.")

    def test_get_the_mean_values(self):
        mean_values = []
        for i in range(120):
            exp = self.replay_buffer._storage[i]
            post_state_values = use_a_net_to_get_scores_for_a_list_of_veh_states(
                self.target_net,
                exp.normalized_system_time_at_next_state,
                exp.vehs_visiting_node_ids_at_next_state,
                exp.vehs_normalized_remaining_delays_at_next_state,
                exp.vehs_num_of_visiting_nodes_at_next_state,
                exp.assumed_vehs_normalized_num_of_nearby_vehs_at_next_state,
                exp.assumed_normalized_num_of_new_reqs_at_next_state)
            mean_values.append(np.mean(post_state_values))
            print(f"[DEBUG-T] Time = {exp.normalized_system_time_at_current_state}, "
                  f"mean value = {np.mean(post_state_values)}")
        dataframe = pd.DataFrame({"mean value": mean_values})
        dataframe.to_csv(f"{ROOT_PATH}/datalog-gitignore/values-{EVAL_NET_FILE_NAME}.csv")


if __name__ == '__main__':
    value_func = ValueFunction()
    value_func.load_eval_net_from_pickle_file()
    # summary(value_func.eval_net)
    value_func.load_replay_buffer_from_pickle_file()
    experiences = value_func.replay_buffer.sample(4)
    value_func.test_get_the_mean_values()
    # value_func.offline_batch_learn()

    # # Print the estimated post_state_values for different experiences.
    # for exp in experiences:
    #     post_state_values = use_a_net_to_get_scores_for_a_list_of_veh_states(
    #         value_func.eval_net,
    #         exp.normalized_system_time_at_next_state,
    #         exp.vehs_visiting_node_ids_at_next_state,
    #         exp.vehs_normalized_remaining_delays_at_next_state,
    #         exp.vehs_num_of_visiting_nodes_at_next_state,
    #         exp.assumed_vehs_normalized_num_of_nearby_vehs_at_next_state,
    #         exp.assumed_normalized_num_of_new_reqs_at_next_state)
    #     print(f"\n [DEBUG-T] time = {exp.normalized_system_time_at_next_state}, "
    #           f"post_state_values {post_state_values[:5]}")

    # # Print the attributes of one vehicle in different experiences.
    # exp = experiences[0]
    # veh_id = 80
    # for idx, exp in enumerate(value_func.replay_buffer._storage):
    #     print(f"[DEBUG-T] time_now {round(exp.normalized_system_time_at_current_state, 3)}, "
    #           f"new_reqs {round(exp.normalized_num_of_new_reqs_at_current_state, 3)}, "
    #           f"veh_nid {exp.vehs_visiting_node_ids_at_current_state[veh_id][0]}, "
    #           f"nearby_vehs {round(exp.vehs_normalized_num_of_nearby_vehs_at_current_state[veh_id], 3)}, "
    #           f"reward {round(exp.vehs_reward_for_transition_from_current_to_next_state[veh_id], 3)}")
    #     if idx > 120:
    #         break

    # Print the attributes of different vehicle in one experiences.
    # exp = experiences[0]
    # for veh_id in range(0, 100):
    #     print(f"[DEBUG-T] time_now {round(exp.normalized_system_time_at_current_state, 3)}, "
    #           f"new_reqs {round(exp.normalized_num_of_new_reqs_at_current_state, 3)}, "
    #           f"nearby_vehs {round(exp.vehs_normalized_num_of_nearby_vehs_at_current_state[veh_id], 3)}, "
    #           f"next_nearby_vehs {round(exp.assumed_vehs_normalized_num_of_nearby_vehs_at_next_state[veh_id], 3)}, "
    #           f"reward {round(exp.vehs_reward_for_transition_from_current_to_next_state[veh_id], 3)}")


