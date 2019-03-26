
import time
from tqdm import tqdm
import pandas as pd
import numpy as np
import networkx as nx
import pickle
import matplotlib.pyplot as plt


if __name__ == "__main__":
    edges = pd.read_csv('edges.csv')
    nodes = pd.read_csv('nodes.csv')
    travel_time_edges = pd.read_csv('travel-time-week.csv', index_col=0).mean(1)

    G = nx.DiGraph()
    num_edges = edges.shape[0]
    rng = tqdm(edges.iterrows(), total=num_edges, ncols=100, desc='Loading Manhattan Graph')
    for i, edge in rng:
        src = edge['source']
        sink = edge['sink']
        travel_time = round(travel_time_edges.iloc[i], 2)
        G.add_edge(src, sink, weight=travel_time)

        src_pos = np.array([nodes.iloc[src - 1]["lng"], nodes.iloc[src - 1]["lat"]])
        sink_pos = np.array([nodes.iloc[sink - 1]["lng"], nodes.iloc[sink - 1]["lat"]])
        G.add_node(src, pos=src_pos)
        G.add_node(sink, pos=sink_pos)

    num_nodes = nodes.shape[0]
    nodes_id = list(range(1, num_nodes + 1))
    # travel_time_table = pd.DataFrame(-np.ones((num_nodes, num_nodes)), index=nodes_id, columns=nodes_id)
    # travel_time_table.to_csv('travel-time-table-sat.csv')

    travel_time_table = pd.read_csv('travel-time-table-sat.csv', index_col=0)
    # print(travel_time_table.head(2))
    # print(travel_time_table.shape[0])
    # print(travel_time_table.shape[1])

    # travel_time_table.iloc[0, 0] = 7.54
    # travel_time_table.iloc[0, 1] = 20.62
    # travel_time_table.iloc[1, 0] = 30.30
    # travel_time_table.iloc[1, 1] = 12.04
    # print(travel_time_table.head(2))

    for o in tqdm(nodes_id):
        for d in tqdm(nodes_id):
            duration, path = nx.bidirectional_dijkstra(G, o, d)
            try:
                travel_time_table.iloc[o - 1, d - 1] = duration
            except nx.NetworkXNoPath:
                print('no path between', o, d)

        if o == 2:
            break
            print('')
            print(travel_time_table.head(2))

    # travel_time_table.to_csv('travel-time-table-sat-1.csv')

    # time3 = time.time()
    # print(nx.bidirectional_dijkstra(G, o, d))
    # print('...running time : %.05f seconds' % (time.time() - time3))
    #
    # time3 = time.time()
    # print(nyc_week_times.iloc[4852][23])
    # print('...running time : %.05f seconds' % (time.time() - time3))

    # pos = nx.shell_layout(G)
    # nx.draw_networkx_nodes(G, pos, node_size=700)
    # nx.draw_networkx_edges(G, pos, width=6)
    # nx.draw_networkx_labels(G, pos, font_size=20, font_family='sans-serif')
    # plt.axis('off')
    # plt.show()




