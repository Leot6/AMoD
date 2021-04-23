# `AMoD Simulation`
<img src="https://github.com/Leot6/AMoD/blob/master/demo.gif" width="1024">

(The illustration above shows an example instance using London map and [OSRM](https://github.com/Project-OSRM/osrm-backend). Now we have moved to Manhattan map and offline routing.) 

Based on amod-abm [[1]](https://github.com/Leot6/AMoD#references) and this paper [[4]](https://github.com/Leot6/AMoD#references). Simulation on Manhattan with 2,000 vehicles of capacity 4 and 394,695 requests (on 2 Mar, 2015) shows a service rate around 96.15%, when maximum wait time and maximum delay of each request are *MaxWait = min(300s, ShortestTravelTime * 0.7)* and *MaxDelay = min(600s, MaxWait + ShortestTravelTime * 0.3)*, respectively. If single-request assignment is considered instead of multi-request assignment (as proposed in paper [[3]](https://github.com/Leot6/AMoD#references)), the service rate goes down to around 94% along with significant reduce on computational time (from 12.57s to 2.65s), slight reduce on mean wait time (from 147.4s to 146.5s), slight increase on mean in-vehicle delay (from 125.91s to 137.88s) and mean vehicle travel distance (from 396.82km to 406.77km).


## Main Parts

- folder `simulator` for a free-floating AMoD system, with a fleet of vehicles
  - `model.py`: all other class are connected by it
  - `vehicle.py`: (shared) autonomous vehicles, the capacity of which can be set to 1 (no sharing), 2 (at most 2 travelers sharing at a time) or more
  - `request.py`: on-demand requests, loaded from NYC trip data (350,878 trips on 5 May, 2016)
  - `route.py`: definition of road segments
  - `config.py`: system parameters
- folder `routing` for routing planning
  - `routing_server.py`: offline path finding, the complete road network of Manhattan (4,091 nodes and 9,452 edges) are considered, with the travel time on each edge of the network given by the daily mean travel time estimation
- folder `analysis` for outputting results and evaluations
  - `result_printer.py`: evaluate the performance and print the results
  - `animation_generator.py`: make the movement of vehicles an animation.
  - `online_analysis.py`: compare different algorithms at the same simulation run
- folder `dispatcher` for central dispatchers that match available vehicles to requests 
  - folder `gi` for the simple first-in-first-out assignment method [[2]](https://github.com/Leot6/AMoD#references) (i.e., an exhaustive version of [[3]](https://github.com/Leot6/AMoD#references))
  - folder `sba` for the single-request batch assignment method [[4]](https://github.com/Leot6/AMoD#references)
  - folder `rtv` for the request-trip-vehicle batch assignment method proposed in [[5]](https://github.com/Leot6/AMoD#references)
  - folder `osp` for the optimal-schedule-pool batch assignment method, improved on 'rtv'
- folder `rebalancer` for repositioning idle vehicles
  - `naive_rebalancer.py`: assign the unserved request to its nearest idle vehicle

To run a samulation, download data files from [this onedrive link](https://1drv.ms/u/s!AsqflzzqZj9qg-85wlz4OGQ0nKbusA?e=axV2NS) or [this google drive link](https://drive.google.com/drive/folders/1ja6du-6hcxM3ooohTcoPuRvcgFfpu2La?usp=sharing), and put the downloaded folders in the root directory. Files in `data-gitignore` were generated using repository [Manhattan-Map](https://github.com/Leot6/Manhattan-Map).

```
|-- AMoD
   |-- data-gitignore
   |-- output-gitignore
```
The main function in `run.py` will simulate the system given input parameters from `config.py`. The results of simulations can be found in folder `output-gitignore`. System performance indicators for analysis include wait time, travel time, detour and service rate at the traveler side, as well as vehicle miles traveled and average load at the operator side. 

Note: running dispatcher `sba`/`rtv`/`osp` needs [mosek](https://www.mosek.com/) (an commerical ILP solver, free to academic users) installed.


## References

1. Jian Wen. amod-abm. https://github.com/wenjian0202/amod-abm, 2017
2. Tong, Y., Zeng, Y., Zhou, Z., Chen, L., Ye, J. and Xu, K., 2018. A unified approach to route planning for shared mobility. Proceedings of the VLDB Endowment, 11(11), p.1633.
3. Ma, S., Zheng, Y. and Wolfson, O., 2013, April. T-share: A large-scale dynamic taxi ridesharing service. In 2013 IEEE 29th International Conference on Data Engineering (ICDE) (pp. 410-421). IEEE.
4. Simonetto, A., Monteil, J. and Gambella, C., 2019. [Real-time city-scale ridesharing via linear assignment problems](https://www.sciencedirect.com/science/article/pii/S0968090X18302882). Transportation Research Part C: Emerging Technologies, 101, pp.208-232.
5. Alonso-Mora, J., Samaranayake, S., Wallar, A., Frazzoli, E. and Rus, D., 2017. [On-demand high-capacity ride-sharing via dynamic trip-vehicle assignment](https://www.pnas.org/content/114/3/462.short). Proceedings of the National Academy of Sciences, 114(3), pp.462-467



