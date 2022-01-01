
import torch
import torch.nn.functional as F
import torch.nn.utils.rnn as rnn_utils
import torch.utils.data as Data
from torch import nn
from torchinfo import summary

from src.value_network.replay_buffer import *
from src.utility.utility_functions import *


class ScoreNet(nn.Module):
    def __init__(self, num_locations: int):
        super(ScoreNet, self).__init__()
        # Layer 1: Schedule location embedding (0 is used for padding).
        self.embedding_location = nn.Embedding(num_embeddings=num_locations + 1, embedding_dim=100, padding_idx=0)
        # Layer 2: LSTM
        self.lstm = nn.LSTM(input_size=101, hidden_size=200, bidirectional=True)
        # self.gru = nn.GRU(input_size=101, hidden_size=200, bidirectional=True)
        # Layer 3: System time processing (the time scale in the real world)
        self.fc1_time = nn.Linear(in_features=1, out_features=100)
        # Layer 4: Schedule state processing.
        self.fc2_state = nn.Linear(in_features=302, out_features=300)
        # Layer 5: Schedule state processing.
        self.fc3_state = nn.Linear(in_features=300, out_features=300)
        # Layer 6: Output dense layer with one output for the schedule scoring task.
        self.out = nn.Linear(in_features=300, out_features=1)

    def forward(self,
                schedule_pos_input: torch.LongTensor,                # shape = [batch_size, (capacity*2+1)]
                pos_delay_input: torch.LongTensor,                   # shape = [batch_size, (capacity*2+1), 1]
                schedule_lengths: torch.LongTensor,                  # shape = [batch_size,]
                system_time_scaled_input: torch.FloatTensor,         # shape = [batch_size, 1, 1], 0 <= value <= 1
                num_of_new_orders_input: torch.LongTensor,           # shape = [batch_size, 1, 1]
                num_of_nearby_vehicles_input: torch.LongTensor       # shape = [batch_size, 1, 1]
                ) -> torch.FloatTensor:                              # shape = [batch_size, 1, 1]

        """
        Examples of input (batch_size = 3, vehicle_capacity = 1):
        #  (locations, delays, system_time(the time scale in the real world),
        #  the number of new requests and the number of other vehicles
        #  that will arrive in the MAX_PICKUP_DELAY area of this schedule's next location)
        -------
        schedule_pos_input = torch.LongTensor([[1, 2, 3],
                                                [4, 5, 0],
                                                [7, 0, 0]])
        pos_delay_input = torch.LongTensor([[[100], [20], [30]],
                                            [[100], [10], [-1]],
                                            [[100], [-1], [-1]]])
        schedule_lengths = torch.LongTensor([3, 2, 1])
        system_time_scaled_input = torch.FloatTensor([[0.5],
                                                      [0.5],
                                                      [0.5]])
        num_of_new_orders_input = torch.LongTensor([[200],
                                                    [200],
                                                    [200]])
        num_of_nearby_vehicles_input = torch.LongTensor([[9],
                                                         [12],
                                                         [15]])

        Examples of output (batch_size = 3, vehicle_capacity = 1):
        -------
        output = torch.FloatTensor([[3.8047],
                                    [3.7808],
                                    [3.7767]])
        """

        # Schedule location embedding.
        schedule_pos_embedded = self.embedding_location(schedule_pos_input)
        # Concatenate location features and delays.
        pos_feature_and_delay = torch.cat((schedule_pos_embedded, pos_delay_input), dim=2)
        # pack_padded_sequence
        packed_pos_feature_and_delay = rnn_utils.pack_padded_sequence(
            pos_feature_and_delay, lengths=schedule_lengths.cpu().numpy(), batch_first=True, enforce_sorted=False)
        # Lstm
        _, (final_hidden_state, _) = self.lstm(packed_pos_feature_and_delay)
        # _, final_hidden_state = self.gru(packed_pos_feature_and_delay)
        # Time embedding.
        time_embedded = F.elu(self.fc1_time(system_time_scaled_input))
        # Concatenate state.
        schedule_state = torch.cat((final_hidden_state[1], num_of_nearby_vehicles_input,
                                    num_of_new_orders_input, time_embedded), dim=1)
        # Two hidden fully-connected layers.
        schedule_state = F.elu(self.fc2_state(schedule_state))
        schedule_state = F.elu(self.fc3_state(schedule_state))
        output = self.out(schedule_state)
        return output


class ValueFunction(object):
    def __init__(self, num_locations):
        self.lr = 0.01               # learning rate
        self.gamma = 0.9             # reward discount factor
        self.buffer_size = 1000      # replay buffer size
        self.batch_size_train = 32   # minibatch size for training
        self.tau = 0.1               # for soft update of target parameters
        self.update_iter = 10        # how often to update the network

        self.net = ScoreNet(num_locations)
        self.target_net = ScoreNet(num_locations)
        self.replay_buffer = PrioritizedReplayBuffer(self.buffer_size)
        self.optimizer = torch.optim.Adam(self.net.parameters(), lr=self.lr)
        self.loss_func = nn.MSELoss()

    def store_experience(self, experience: Experience):
        self.replay_buffer.add(experience)

    # Soft update model parameters. θ_target = τ*θ_local + (1 - τ)*θ_target
    def soft_update_target_net(self):
        for target_param, local_param in zip(self.target_net.parameters(), self.net.parameters()):
            target_param.data.copy_(self.tau * local_param.data + (1.0 - self.tau) * target_param.data)

    def choose_action(self, experience: Experience):
        pass

    def learn(self):
        pass


def save_net_to_file(_net: nn.Module, file_path: str = "net.pkl"):
    torch.save(_net, file_path)


def restore_net_from_file(file_path: str = "net.pkl"):
    return torch.load(file_path)


def format_experience_to_tensor_dataset(experience: Experience, is_current: bool) -> Data.TensorDataset:
    schedule_pos_input: list[list[int]] = []
    pos_delay_input: list[list[[int]]] = []
    schedule_lengths: list[int] = []
    system_time_scaled_input: list[[float]] = []
    num_of_new_orders_input: list[[int]] = []
    num_of_nearby_vehicles_input: list[[int]] = []

    if is_current:
        schedule_pos_input.extend(experience.vehicles_current_schedule_pos)
        pos_delay_input.extend(experience.vehicles_current_schedule_delay)
        schedule_lengths.extend([veh_info[3] for veh_info in experience.vehicles_info])
        system_time_scaled_input.extend([experience.system_time_scaled for _ in experience.vehicles_info])
        num_of_new_orders_input.extend([experience.num_of_new_orders for _ in experience.vehicles_info])
        num_of_nearby_vehicles_input.extend([veh_info[2] for veh_info in experience.vehicles_info])
    else:
        schedule_pos_input.extend(experience.vehicles_candidate_schedules_pos_updated_to_next_epoch)
        pos_delay_input.extend(experience.vehicles_candidate_schedules_delay_updated_to_next_epoch)
        schedule_lengths.extend([candidate_schedule_info[1] for candidate_schedule_info
                                 in experience.vehicles_candidate_schedules_info_updated_to_next_epoch])
        system_time_scaled_input.extend([experience.system_time_scaled for _
                                         in experience.vehicles_candidate_schedules_info_updated_to_next_epoch])
        num_of_new_orders_input.extend([experience.num_of_new_orders for _
                                        in experience.vehicles_candidate_schedules_info_updated_to_next_epoch])
        num_of_nearby_vehicles_input.extend(
            [experience.vehicles_info[candidate_schedule_info[0]][2] for candidate_schedule_info
             in experience.vehicles_candidate_schedules_info_updated_to_next_epoch])

    torch_dataset = Data.TensorDataset(torch.LongTensor(schedule_pos_input),
                                       torch.unsqueeze(torch.LongTensor(pos_delay_input), 2),
                                       torch.LongTensor(schedule_lengths),
                                       torch.unsqueeze(torch.FloatTensor(system_time_scaled_input), 1),
                                       torch.unsqueeze(torch.LongTensor(num_of_new_orders_input), 1),
                                       torch.unsqueeze(torch.LongTensor(num_of_nearby_vehicles_input), 1))
    return torch_dataset


# Evaluate the candidate schedules and return the scores in a list in the same order.
def get_scores_for_candidate_schedules_in_an_experience(experience: Experience, score_net: nn.Module) -> list[float]:
    scores_for_candidate_schedules = []
    score_net_input_dataset = format_experience_to_tensor_dataset(experience, is_current=False)
    loader = Data.DataLoader(dataset=score_net_input_dataset, batch_size=1000, shuffle=False, num_workers=2)
    for step, (batch_x1, batch_x2, batch_x3, batch_x4, batch_x5, batch_x6) in enumerate(loader):
        score_net_output = score_net(batch_x1, batch_x2, batch_x3, batch_x4, batch_x5, batch_x6)
        score_net_output = torch.squeeze(score_net_output, 1).detach().numpy().tolist()
        scores_for_candidate_schedules.extend(score_net_output)
    return scores_for_candidate_schedules


if __name__ == '__main__':
    value_function = ValueFunction(4091)

    # # input example
    # schedule_pos_input = torch.LongTensor([[1, 2, 3],
    #                                        [4, 5, 0],
    #                                        [7, 0, 0]])
    # pos_delay_input = torch.LongTensor([[[100], [20], [30]],
    #                                     [[100], [10], [-1]],
    #                                     [[100], [-1], [-1]]])
    # schedule_lengths = torch.LongTensor([3, 2, 1])
    # system_time_scaled_input = torch.FloatTensor([[0.5],
    #                                               [0.5],
    #                                               [0.5]])
    # num_of_new_orders_input = torch.LongTensor([[200],
    #                                             [200],
    #                                             [200]])
    # num_of_nearby_vehicles_input = torch.LongTensor([[9],
    #                                                  [12],
    #                                                  [15]])
    #
    # # test score net using input example
    # result = value_function.net(schedule_pos_input,
    #                             pos_delay_input,
    #                             schedule_lengths,
    #                             system_time_scaled_input,
    #                             num_of_new_orders_input,
    #                             num_of_nearby_vehicles_input)
    # print("Score result from input example", result)

    # experience example
    system_time_scaled = 0.5
    num_of_new_orders = 200
    vehicles_info = [[0, 1, 9, 3],
                     [1, 4, 12, 2],
                     [2, 7, 15, 1]]
    vehicles_current_schedule_pos = [[1, 2, 3],
                                     [4, 5, 0],
                                     [7, 0, 0]]
    vehicles_current_schedule_delay = [[100, 20, 30],
                                       [100, 10, -1],
                                       [100, -1, -1]]
    vehicles_candidate_schedules_info_updated_to_next_epoch = [[0, 2],
                                                               [1, 3],
                                                               [1, 2],
                                                               [2, 2]]
    vehicles_candidate_schedules_pos_updated_to_next_epoch = [[1, 5, 0],
                                                              [4, 3, 8],
                                                              [4, 6, 0],
                                                              [7, 2, 0]]
    vehicles_candidate_schedules_delay_updated_to_next_epoch = [[100, 30, -1],
                                                                [100, 20, 10],
                                                                [100, 10, -1],
                                                                [100, 40, -1]]

    test_experience = Experience(system_time_scaled, num_of_new_orders,
                                 vehicles_info,
                                 vehicles_current_schedule_pos,
                                 vehicles_current_schedule_delay,
                                 vehicles_candidate_schedules_info_updated_to_next_epoch,
                                 vehicles_candidate_schedules_pos_updated_to_next_epoch,
                                 vehicles_candidate_schedules_delay_updated_to_next_epoch)

    # #  test net using single input from experience
    # scores_for_candidate_schedules = []
    # test_dataset = format_experience_to_tensor_dataset(test_experience, is_current=False)
    # loader = Data.DataLoader(dataset=test_dataset, batch_size=1, shuffle=False, num_workers=2)
    # for step, (batch_x1, batch_x2, batch_x3, batch_x4, batch_x5, batch_x6) in enumerate(loader):
    #     score_net_output = \
    #         torch.squeeze(value_function.net(batch_x1, batch_x2, batch_x3, batch_x4, batch_x5, batch_x6), 1)
    #     score_net_output = score_net_output.detach().numpy().tolist()
    #     scores_for_candidate_schedules.extend(score_net_output)
    # print("score result using single input from experience example", scores_for_candidate_schedules)
    #
    # # test score net using batch input from experience
    # test_scores = get_scores_for_candidate_schedules_in_an_experience(test_experience, value_function.net)
    # print("score result using batch input from experience example", test_scores)



