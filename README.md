# `AMoD Simulation`
<img src="https://github.com/Leot6/AMoD/blob/master/demo.gif" width="1024">

Based on amod-abm [[1]](https://github.com/Leot6/AMoD#references) and this paper [[2]](https://github.com/Leot6/AMoD#references). Simulation on Manhattan with 2,000 vehicles of capacity 4 and 394,695 requests (on 2 Mar, 2015) shows a service rate around 96.15%, when maximum wait time and maximum delay of each request are *MaxWait = min(300s, ShortestTravelTime * 0.7)* and *MaxDelay = min(600s, MaxWait + ShortestTravelTime * 0.3)*, respectively. If single-request assignment is considered instead of multi-request assignment (as proposed in paper [[3]](https://github.com/Leot6/AMoD#references)), the service rate goes down to around 94% along with significant reduce on computational time (from 12.57s to 2.65s), slight reduce on mean wait time (from 147.4s to 146.5s), slight increase on mean in-vehicle delay (from 125.91s to 137.88s) and mean vehicle travel distance (from 396.82km to 406.77km).


## Main Parts

- class `Main` for free-floating AMoD systems, with a fleet of vehicles
  - all other class are connected by it
- class `Vehicle` for (shared) autonomous vehicles
  - vehicle capacity can be set to 1 (no sharing), 2 (at most 2 travelers sharing at a time) or more
- class `Request` for requests
  - requests are loaded from NYC trip data (394,695 requests on 2 Mar, 2015)
  - requests are on-demand
- class `Route` for routing server
  - the complete road network of Manhattan (4,092 nodes and 9,453 edges, might not fine enough) are considered, with the travel time on each edge (road segment) of the network given by the daily mean travel time estimate
- class `VTtable`, `ScheduleFinder`, `AssignPlaner` for a central dispatcher
  - assigns requests to vehicles, based on the idea of [[2]](https://github.com/Leot6/AMoD#references)
- class `Rebalancer` for a naive rebalancer  
  - assigns idle vehicles to requests that can not be served by the central dispatcher, based on the idea of [[2]](https://github.com/Leot6/AMoD#references)

The main function in `run.py` will simulate the system given input parameters from `Configures.py`. The results of simulations can be found in folder `output`. System performance indicators for analysis include wait time, travel time, detour and service rate at the traveler side, as well as vehicle miles traveled and average load at the operator side.


## References

1. Jian Wen. amod-abm. https://github.com/wenjian0202/amod-abm, 2017
2. Alonso-Mora, J., Samaranayake, S., Wallar, A., Frazzoli, E. and Rus, D., 2017. [On-demand high-capacity ride-sharing via dynamic trip-vehicle assignment](https://www.pnas.org/content/114/3/462.short). Proceedings of the National Academy of Sciences, 114(3), pp.462-467
3. Simonetto, A., Monteil, J. and Gambella, C., 2019. [Real-time city-scale ridesharing via linear assignment problems](https://www.sciencedirect.com/science/article/pii/S0968090X18302882). Transportation Research Part C: Emerging Technologies, 101, pp.208-232.


