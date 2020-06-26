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
  - the map data should be preprocessed beforehand using `ComputeTravelTimeTable`
- class `VTtable`, `ScheduleFinder`, `AssignPlaner` for a central dispatcher
  - assigns requests to vehicles, based on the idea of [[2]](https://github.com/Leot6/AMoD#references)
- class `Rebalancer` for a naive rebalancer  
  - assigns idle vehicles to requests that can not be served by the central dispatcher, based on the idea of [[2]](https://github.com/Leot6/AMoD#references)

The main function in `run.py` will simulate the system given input parameters from `Configures.py`. The results of simulations can be found in folder `output`. System performance indicators for analysis include wait time, travel time, detour and service rate at the traveler side, as well as vehicle miles traveled and average load at the operator side.


<!--

## Installation of OSRM (not used at now)

> This installation guideline targets MacOS.

> OSRM, written in C++14, should be built from source beforehand. For more information please go to OSRM [Wiki](https://github.com/Project-OSRM/osrm-backend#open-source-routing-machine).

> The route returned by OSRM is not consistant in some situation when using the built-in vehicle status updating code. (e.g. After a vehicle movies along a route (A->B), which duration is 90s, for 20s and stops at a midpoint between A and B, the route returned by OSRM from the midpoint to B might be 75s instead of 70s as expected.)

Install HomeBrew if not available:
```
/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
```
Install wget if not available:
```
brew install wget
```
Similarly, install all other necessary dependencies:
```
brew install boost git cmake libzip libstxxl libxml2 lua tbb ccache
brew install GDAL
``` 

Get new OSRM source files and extract:
```
wget https://github.com/Project-OSRM/osrm-backend/archive/v5.21.0.tar.gz
tar -xzf v5.21.0.tar.gz
```
> v5.21.0 is the [latest release](https://github.com/Project-OSRM/osrm-backend/releases) for the time being (26 Dec, 2018).

Get into the folder:
```
cd osrm-backend-5.21.0
```
Make files:
```
mkdir build
cd build
cmake ../
make -j
cd ..
```
The `osrm-routed` executable should be working now. The next step is to grab a `.osm.pbf` OpenStreetMap extract from [Geofabrik](http://download.geofabrik.de/index.html) or [BBBike](https://extract.bbbike.org/) (recommended). Here, we use areas of London as a toy case:
```
wget http://download.geofabrik.de/europe/great-britain/england/greater-london-latest.osm.pbf
```
Extract the road network:
```
./build/osrm-extract greater-london-latest.osm.pbf -p profiles/car.lua
```
Create the hierarchy:
```
./build/osrm-contract greater-london-latest.osm.pbf  
```
> The Open Source Routing Machine is a C++ implementation of a high-performance routing engine for shortest paths in OpenStreetMap road networks. It uses an implementation of Contraction Hierarchies and is able to compute and output a shortest path between any origin and destination within a few milliseconds.

The installation is done. Run the OSRM engine and establish an routing server:
```
./build/osrm-routed greater-london-latest.osrm
```
[General Options](https://github.com/Project-OSRM/osrm-backend/blob/master/docs/http.md) gives syntax for all possible services that OSRM is providing. 

-->


## References

1. Jian Wen. amod-abm. https://github.com/wenjian0202/amod-abm, 2017
2. Alonso-Mora, J., Samaranayake, S., Wallar, A., Frazzoli, E. and Rus, D., 2017. [On-demand high-capacity ride-sharing via dynamic trip-vehicle assignment](https://www.pnas.org/content/114/3/462.short). Proceedings of the National Academy of Sciences, 114(3), pp.462-467
3. Simonetto, A., Monteil, J. and Gambella, C., 2019. [Real-time city-scale ridesharing via linear assignment problems](https://www.sciencedirect.com/science/article/pii/S0968090X18302882). Transportation Research Part C: Emerging Technologies, 101, pp.208-232.


