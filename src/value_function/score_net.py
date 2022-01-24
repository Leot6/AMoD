
import torch
import torch.nn.functional as F
import torch.nn.utils.rnn as rnn_utils
import torch.utils.data as Data
from torch import nn
from torchinfo import summary


class ScoreNet(nn.Module):
    def __init__(self, num_locations: int):
        super(ScoreNet, self).__init__()
        # Layer 1: Schedule's visiting locations embedding (0 is used for padding).
        self.embedding_location = nn.Embedding(num_embeddings=num_locations + 1, embedding_dim=100, padding_idx=0)
        # Layer 2: LSTM
        self.lstm = nn.LSTM(input_size=101, hidden_size=200, bidirectional=True)
        # self.gru = nn.GRU(input_size=101, hidden_size=200, bidirectional=True)
        # Layer 3: System time processing (the normalized system time)
        self.fc1_time = nn.Linear(in_features=1, out_features=100)
        # Layer 4: Schedule state processing.
        self.fc2_state = nn.Linear(in_features=302, out_features=300)
        # Layer 5: Schedule state processing.
        self.fc3_state = nn.Linear(in_features=300, out_features=300)
        # Layer 6: Output dense layer with one output for the scoring task.
        self.out = nn.Linear(in_features=300, out_features=1)

    def forward(self,
                normalized_system_time_input: torch.FloatTensor,        # shape = [batch_size, 1, 1]
                visiting_node_ids_input: torch.LongTensor,              # shape = [batch_size, (capacity*2+1+3)]
                normalized_remaining_delays_input: torch.FloatTensor,    # shape = [batch_size, (capacity*2+1+3), 1]
                num_of_visiting_nodes_info: torch.LongTensor,           # shape = [batch_size,]
                normalized_num_of_nearby_vehs_input: torch.FloatTensor,  # shape = [batch_size, 1, 1]
                normalized_num_of_new_reqs_input: torch.FloatTensor,     # shape = [batch_size, 1, 1]
                ) -> torch.FloatTensor:                                 # shape = [batch_size, 1, 1]

        """
        Examples of input (batch_size = 3, vehicle_capacity = 1):
        -------
        normalized_system_time_input = torch.FloatTensor([[0.25],
                                                          [0.25],
                                                          [0.25]])
        visiting_node_ids_input = torch.LongTensor([[1, 2, 3],
                                                    [4, 5, 0],
                                                    [7, 0, 0]])  # 0 is used for padding
        normalized_remaining_delays_input = torch.LongTensor([[[1], [0.2], [0.3]],
                                                              [[1], [0.1], [-1]],
                                                              [[1], [-1], [-1]]])  # -1 is used for padding
        num_of_visiting_nodes_info = torch.LongTensor([3, 2, 1])
        normalized_num_of_nearby_vehs_input = torch.LongTensor([[0.33],
                                                                [0.67],
                                                                [0.67]])
        normalized_num_of_new_reqs_input = torch.LongTensor([[0.67],
                                                             [0.67],
                                                             [0.67]])


        Examples of output (batch_size = 3, vehicle_capacity = 1):
        -------
        output = torch.FloatTensor([[3.8047],
                                    [3.7808],
                                    [3.7767]])
        """

        # Schedule's visiting locations embedding.
        visiting_node_ids_embedded = self.embedding_location(visiting_node_ids_input)
        # Concatenate location features and remaining delays.
        sche_features = torch.cat((visiting_node_ids_embedded, normalized_remaining_delays_input), dim=2)
        # pack_padded_sequence
        packed_sche_features = rnn_utils.pack_padded_sequence(
            sche_features, lengths=num_of_visiting_nodes_info.cpu().numpy(), batch_first=True, enforce_sorted=False)
        # Lstm
        output, (final_hidden_state, final_cell_state) = self.lstm(packed_sche_features)
        # output, final_hidden_state = self.gru(packed_pos_feature_and_delay)
        # Time embedding.
        time_embedded = F.elu(self.fc1_time(normalized_system_time_input))
        # Concatenate state.
        schedule_state = torch.cat((final_hidden_state[1], normalized_num_of_nearby_vehs_input,
                                    normalized_num_of_new_reqs_input, time_embedded), dim=1)
        # Two hidden fully-connected layers.
        schedule_state = F.elu(self.fc2_state(schedule_state))
        schedule_state = F.elu(self.fc3_state(schedule_state))
        output = self.out(schedule_state)
        return output


def use_a_net_to_get_scores_for_a_list_of_veh_states(score_net: object,
                                                     normalized_system_time: object,
                                                     states_visiting_node_ids: object,
                                                     states_normalized_remaining_delays: object,
                                                     states_num_of_visiting_nodes: object,
                                                     states_normalized_num_of_nearby_vehs: object,
                                                     normalized_num_of_new_reqs: object) -> object:
    # Format the attributes of states into a tensor dataset.
    batch_x1, batch_x2, batch_x3, batch_x4, batch_x5, batch_x6 = \
        format_batch_input_data_to_tensor_type(normalized_system_time, states_visiting_node_ids,
                                               states_normalized_remaining_delays,
                                               states_num_of_visiting_nodes,
                                               states_normalized_num_of_nearby_vehs,
                                               normalized_num_of_new_reqs)

    score_net_output = score_net(batch_x1, batch_x2, batch_x3, batch_x4, batch_x5, batch_x6)
    estimated_scores = torch.squeeze(score_net_output, 1).detach().numpy().tolist()

    # torch_dataset_input = Data.TensorDataset(batch_x1, batch_x2, batch_x3, batch_x4, batch_x5, batch_x6)

    # # Input the data into the score net in batches and get the score.
    # estimated_scores = []
    # loader = Data.DataLoader(dataset=torch_dataset_input, batch_size=1000, shuffle=False, num_workers=0)
    # for step, (mb_x1, mb_x2, mb_x3, mb_x4, mb_x5, mb_x6) in enumerate(loader):
    #     score_net_output = score_net(mb_x1, mb_x2, mb_x3, mb_x4, mb_x5, mb_x6)
    #     score_net_output = torch.squeeze(score_net_output, 1).detach().numpy().tolist()
    #     estimated_scores.extend(score_net_output)
    return estimated_scores


def format_batch_input_data_to_tensor_type(normalized_system_time: float,
                                           states_visiting_node_ids: list[list[int]],
                                           states_normalized_remaining_delays: list[list[float]],
                                           states_num_of_visiting_nodes: list[int],
                                           states_normalized_num_of_nearby_vehs: list[float],
                                           normalized_num_of_new_reqs: float):
    num_of_states = len(states_visiting_node_ids)
    batch_x1 = torch.unsqueeze(torch.FloatTensor([normalized_system_time] * num_of_states), 1)
    # batch_x1 = torch.unsqueeze(torch.FloatTensor([1] * num_of_states), 1)
    batch_x2 = torch.LongTensor(states_visiting_node_ids)
    batch_x3 = torch.unsqueeze(torch.FloatTensor(states_normalized_remaining_delays), 2)
    batch_x4 = torch.LongTensor(states_num_of_visiting_nodes)
    batch_x5 = torch.unsqueeze(torch.FloatTensor(states_normalized_num_of_nearby_vehs), 1)
    batch_x6 = \
        torch.unsqueeze(torch.FloatTensor([normalized_num_of_new_reqs] * num_of_states), 1)
    return batch_x1, batch_x2, batch_x3, batch_x4, batch_x5, batch_x6


def save_net_to_file(net: nn.Module, file_path: str = "net.pickle"):
    torch.save(net, file_path)


def restore_net_from_file(file_path: str = "net.pickle"):
    return torch.load(file_path)


if __name__ == '__main__':
    # Example of a list of states:
    normalized_system_time_at_current_state = 0.25
    vehs_visiting_node_ids_at_current_state = [[1, 2, 3],
                                               [4, 5, 0],
                                               [7, 0, 0]]
    vehs_normalized_remaining_delays_at_current_state = [[1, 0.2, 0.3],
                                                         [1, 0.1, -1],
                                                         [1, -1, -1]]
    vehs_num_of_visiting_nodes_at_current_state = [3, 2, 1]

    vehs_normalized_num_of_nearby_vehs_at_current_state = [0.33, 0.67, 0.67]
    normalized_num_of_new_reqs_at_current_state = 0.67

    test_score_net = ScoreNet(4091)
    expected_scores = \
        use_a_net_to_get_scores_for_a_list_of_veh_states(test_score_net,
                                                         normalized_system_time_at_current_state,
                                                         vehs_visiting_node_ids_at_current_state,
                                                         vehs_normalized_remaining_delays_at_current_state,
                                                         vehs_num_of_visiting_nodes_at_current_state,
                                                         vehs_normalized_num_of_nearby_vehs_at_current_state,
                                                         normalized_num_of_new_reqs_at_current_state)
    print(f"\nexpected_scores {expected_scores}")
