# `AMoD Simulation`
<img src="https://github.com/Leot6/AMoD/blob/master/demo.gif" width="1024">

(The illustration above shows an example instance using London map and [OSRM](https://github.com/Project-OSRM/osrm-backend). Now we have moved to Manhattan map and offline routing.)

This simulator and algorithms are written in python. A C++ version, which runs much faster, can be found in [AMoD2](https://github.com/Leot6/AMoD2).

## Main Parts
Based on amod-abm [[1]](https://github.com/Leot6/AMoD#references) and this paper [[3]](https://github.com/Leot6/AMoD#references). Simulation on Manhattan with 2,000 vehicles of capacity 4 and 394,695 requests (on 2 Mar, 2015) shows a service rate around 96.15%, when maximum wait time and maximum delay of each request are *MaxWait = min(300s, ShortestTravelTime * 0.7)* and *MaxDelay = min(600s, MaxWait + ShortestTravelTime * 0.3)*, respectively. If single-request assignment is considered instead of multi-request assignment (as proposed in paper [[2]](https://github.com/Leot6/AMoD#references)), the service rate goes down to around 94% along with significant reduce on computational time (from 12.57s to 2.65s), slight reduce on mean wait time (from 147.4s to 146.5s), slight increase on mean in-vehicle delay (from 125.91s to 137.88s) and mean vehicle travel distance (from 396.82km to 406.77km). P.S., the above results are generated with a very early version of the code and slightly different results are expected with the latest version of the code.

- Dispatcher
    - Single-Request Batch Assignment (SBA) [[2]](https://github.com/Leot6/AMoD#references): It takes the new orders for a batch period and assigns them together in a one-to-one match manner, where at most one new order is assigned to a single vehicle.
    - Optimal Schedule Pool (OSP) [[3]](https://github.com/Leot6/AMoD#references): It takes all picking and pending orders received so far and assigns them together in a multi-to-one match manner, where multiple orders (denoted by a trip) can be assigned to a single vehicle. Trips are also allowed to be reassigned to different vehicles for better system performance. OSP is an improved version of Request Trip Vehicle (RTV) assignment [[4]](https://github.com/Leot6/AMoD#references), it computes all possible vehicle-trip pairs along with the optimal schedule of each pair. The computation of the optimal schedule ensures that no feasible trip is mistakenly ignored. Based on this complete feasible solution space (called optimal schedule pool, each optimal schedule representing a vehicle-trip pair), the optimal assignment policy could be found by an ILP solver.
- Rebalancer
    - Nearest Pending Order (NPO): It repositions idle vehicles to the nearest locations of unassigned pending orders, under the assumption that it is likely that more requests occur in the same area where all requests cannot be satisfied.
  

To run a samulation, Download code and data files from the [releases](https://github.com/Leot6/AMoD/releases). Data files should be located in the root directory of the code. Files in `datalog-gitignore.zip` were generated using repository [Manhattan-Map](https://github.com/Leot6/Manhattan-Map).

```
|-- AMoD
   |-- datalog-gitignore
   |-- media-gitignore
   |-- src
```
Before running simulations, we need to run `data_serializer.py` to load taxi data and map data files in advance and store them in pickle files. This is to accelerate the initialization time of the simulator.
The main function in `main.py` will simulate the system given input parameters from `config.py`. System performance indicators for analysis include wait time, travel time, detour and service rate at the traveler side, as well as vehicle miles traveled and average load at the operator side.

Note: Running dispatcher `sba`/`osp` needs [gurobi](https://www.gurobi.com/) (an commerical optimization solver, free to academic users) installed. If `gurobi` is not installed, the code can be run by replacing the uses of function `ILP_assignment` to `greedy_assignment` (do not forget to comment the codes using gurobi in file `ilp_assign`), with expected worse performances. 


## Dependencies to Install
```
python 3.9 or above

gurobipy
matplotlib
numpy
pandas
scipy
tqdm
```

## Steps to Start
1. Download data files from [files](https://github.com/Leot6/AMoD/releases) and put them into the root directory of the code. Files in `datalog-gitignore.zip` were generated using repository [Manhattan-Map](https://github.com/Leot6/Manhattan-Map).

```
|-- simulation_system_lite
   |-- datalog-gitignore
   |-- media-gitignore
   |-- src
```

2. Run `data_serializer.py` to load taxi data and map data files in advance and store them in pickle files. This is to accelerate the initialization time of the simulator.
```
cd src/utility
python3 data_serializer.py
```

3. Run `main.py` to start the simulation. Set `DEBUG_PRINT = True` in `src/simulator/config.py` will print a detailed log in terminal.

```
cd ../..
python3 main.py
```

## An Example Simulation Result

```
Initializing the simulator ...
[INFO] Router_Func is ready. (0.371s)
[INFO] Demand Generator is ready. (0.743s)
[INFO] Platform is ready.
------------------------------------------------------------------------------------------
# Simulation Runtime
  - Start: 2023-06-05 10:14:52, End: 0000-00-00 00:00:00, Time: 0:00:00.
  - Main Simulation: init_time = 1.55 s, runtime = 0:00:00, avg_time = 0.00 s. 
# System Configurations
  - From 18:30:00 to 20:39:00. (main simulation between 19:00:00 and 20:00:00).
  - Fleet Config: size = 200, capacity = 6. (60 + 120 + 78 = 258 epochs).
  - Order Config: density = 0.05 (20160525-400k), max_wait = 300 s. (Δt = 30 s).
  - Dispatch Config: dispatcher = SBA, rebalancer = NPO.
------------------------------------------------------------------------------------------
AMoD: 100%|█████████████████████████████████████████████| 258/258 [00:18<00:00, 13.86it/s]
------------------------------------------------------------------------------------------
# Simulation Runtime
  - Start: 2023-06-05 10:14:52, End: 2023-06-05 10:15:10, Time: 0:00:18.
  - Main Simulation: init_time = 1.55 s, runtime = 0:00:08, avg_time = 0.07 s. 
# System Configurations
  - From 18:30:00 to 20:39:00. (main simulation between 19:00:00 and 20:00:00).
  - Fleet Config: size = 200, capacity = 6. (60 + 120 + 78 = 258 epochs).
  - Order Config: density = 0.05 (20160525-400k), max_wait = 300 s. (Δt = 30 s).
  - Dispatch Config: dispatcher = SBA, rebalancer = NPO.
# Orders (1053/1348)
  - complete = 1053 (78.12%), onboard = 0 (0.00%), total_service = 1053 (78.12%).
  - avg_shortest_travel = 0.64 s, avg_wait = 169.60 s, avg_delay = 274.37 s.
# Vehicles (200)
  - Travel Distance: total_dist = 3521.11 km, avg_dist = 17.61 km.
  - Travel Duration: avg_time = 3575.07 s (99.31% of the main simulation time).
  - Empty Travel: avg_time = 308.56 s (8.63%), avg_dist = 1.34 km (7.63%).
  - Rebl Travel: avg_time = 580.06 s (16.23%), avg_dist = 3.07 km (17.42%).
  - Travel Load: average_load_dist = 1.05, average_load_time = 1.06.
------------------------------------------------------------------------------------------


## References

1. Jian Wen. amod-abm. https://github.com/wenjian0202/amod-abm, 2017
2. Simonetto, A., Monteil, J. and Gambella, C., 2019. [Real-time city-scale ridesharing via linear assignment problems](https://www.sciencedirect.com/science/article/pii/S0968090X18302882). Transportation Research Part C: Emerging Technologies, 101, pp.208-232.
3. Li, C., Parker, D. and Hao, Q., 2021. [Optimal Online Dispatch for High-Capacity Shared Autonomous Mobility-on-Demand Systems](https://www.cs.bham.ac.uk/~parkerdx/papers/icra21samod.pdf). In Proc. IEEE International Conference on Robotics and Automation (ICRA'21).
4. Alonso-Mora, J., Samaranayake, S., Wallar, A., Frazzoli, E. and Rus, D., 2017. [On-demand high-capacity ride-sharing via dynamic trip-vehicle assignment](https://www.pnas.org/content/114/3/462.short). Proceedings of the National Academy of Sciences, 114(3), pp.462-467


