
import pandas as pd
import sys
import os
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(ROOT_PATH)
from src.utility.utility_functions import *


def load_network_node_from_csv_file_and_save_it_to_pickle_file(path_to_csv: str):
    all_nodes = []
    nodes_csv = pd.read_csv(path_to_csv)
    num_of_nodes = nodes_csv.shape[0]
    print(f"[INFO] num_of_nodes {nodes_csv.shape}")
    print(nodes_csv.head(2))
    for idx in range(num_of_nodes):
        node = Pos()
        node.node_id = int(nodes_csv.iloc[idx]["id"])
        node.lng = nodes_csv.iloc[idx]["lng"]
        node.lat = nodes_csv.iloc[idx]["lat"]
        all_nodes.append(node)
    path_to_pickle = path_to_csv.replace(".csv", ".pickle")
    with open(path_to_pickle, 'wb') as f:
        pickle.dump(all_nodes, f)


def load_path_table_from_csv_file_and_save_it_to_pickle(path_to_csv: str):
    path_table_csv = pd.read_csv(path_to_csv, index_col=0).values
    path_to_pickle = path_to_csv.replace(".csv", ".pickle")
    with open(path_to_pickle, 'wb') as f:
        pickle.dump(path_table_csv, f)


def load_request_data_from_csv_file_and_save_it_to_pickle_file(path_to_csv: str):
    all_requests = []
    requests_csv = pd.read_csv(path_to_csv)
    num_of_requests = requests_csv.shape[0]
    print(f"[INFO] num_of_requests {requests_csv.shape}")
    print(requests_csv.head(2))
    for idx in tqdm(range(num_of_requests), "loading requests"):
        request = RawRequest()
        request.origin_node_id = int(requests_csv.iloc[idx]["onid"])
        request.destination_node_id = int(requests_csv.iloc[idx]["dnid"])
        request.request_time_date = requests_csv.iloc[idx]["ptime"]
        request.request_time_sec = compute_the_accumulated_seconds_from_0_clock(request.request_time_date)
        all_requests.append(request)
    path_to_pickle = path_to_csv.replace(".csv", ".pickle")
    with open(path_to_pickle, 'wb') as f:
        pickle.dump(all_requests, f)


if __name__ == '__main__':
    vehicle_stations = f"{ROOT_PATH}/datalog-gitignore/map-data/stations-101.csv"
    network_nodes = f"{ROOT_PATH}/datalog-gitignore/map-data/nodes.csv"
    mean_table = f"{ROOT_PATH}/datalog-gitignore/map-data/mean-table.csv"
    dist_table = f"{ROOT_PATH}/datalog-gitignore/map-data/dist-table.csv"
    path_table = f"{ROOT_PATH}/datalog-gitignore/map-data/path-table.csv"

    # for node_file in [vehicle_stations, network_nodes]:
    #     load_network_node_from_csv_file_and_save_it_to_pickle_file(node_file)

    # for table_file in [mean_table, dist_table, path_table]:
    #     load_path_table_from_csv_file_and_save_it_to_pickle(table_file)

    # for day in ["03", "04", "05", "10", "11", "12", "17", "19", "24", "25", "26"]:
    #     taxi_data = f"{ROOT_PATH}/datalog-gitignore/taxi-data/manhattan-taxi-201605{day}-peak.csv"
    #     load_request_data_from_csv_file_and_save_it_to_pickle_file(taxi_data)

    taxi_data = f"{ROOT_PATH}/datalog-gitignore/taxi-data/manhattan-taxi-20160406.csv"
    load_request_data_from_csv_file_and_save_it_to_pickle_file(taxi_data)
