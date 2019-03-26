import time
from tqdm import tqdm
import pandas as pd
import numpy as np
import networkx as nx
import pickle
import matplotlib.pyplot as plt

if __name__ == "__main__":
    edges = pd.read_csv('data/Manhattan-graph/edges.csv')
    nodes = pd.read_csv('data/Manhattan-graph/nodes.csv')
    travel_time_edges = pd.read_csv('data/Manhattan-graph/travel-time-sat.csv', index_col=0).mean(1)

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

        if i == 10:
            break

    # pos = nx.shell_layout(G)
    # nx.draw_networkx_nodes(G, pos, node_size=700)
    # nx.draw_networkx_edges(G, pos, width=6)
    # nx.draw_networkx_labels(G, pos, font_size=20, font_family='sans-serif')
    # plt.axis('off')
    # plt.show()

    try:
        duration, path = nx.bidirectional_dijkstra(G, 1, 3)
    except nx.NetworkXNoPath:
        print("no path")




