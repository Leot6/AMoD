# An AMoD Simulator
Based on [amod-abm](https://github.com/wenjian0202/amod-abm).

## `Illustration`

<img src="https://github.com/Leot6/AMoD/blob/master/demo.gif" width="1024">


## Installation 

> This installation guideline targets MacOS.

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
Navigate to a good directory, and clone the project from GitHub using git:
```
git clone https://github.com/Leot6/AMoD-Simulation.git
```

Get into the project folder, and remove the compiled OSRM files:
```
cd amod-abm
rm -R osrm-backend-5.21.0
```

> OSRM, written in C++14, should be built from source beforehand. For more information please go to OSRM [Wiki](https://github.com/Project-OSRM/osrm-backend#open-source-routing-machine). 

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
The `osrm-routed` executable should be working now. The next step is to grab a `.osm.pbf` OpenStreetMap extract from [Geofabrik](http://download.geofabrik.de/index.html) or [BBBike](https://extract.bbbike.org/). Here, we use areas of London as a toy case:
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

A demo of the simulation platform has been prepared. Keep the routing server running, then run `python run.py` and see what's happening. 

## Requirements

- OS X >= 10.10
- XCode
- Python >= 3.6



## References

1. Jian Wen. amod-abm. https://github.com/wenjian0202/amod-abm, 2017


