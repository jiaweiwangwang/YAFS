"""

    This example is an implementation of "VRGameFog.java [#f1]_  of EGG_GAME a latency-sensitive online game" presented in [#f2]_ (first case study).

    .. [#f1] https://github.com/wolfbrother/iFogSim/blob/master/src/org/fog/examples/VRGameFog.java
    .. [#f2] Gupta, H., Vahid Dastjerdi, A., Ghosh, S. K., & Buyya, R. (2017). iFogSim: A toolkit for modeling and simulation of resource management techniques in the Internet of Things, Edge and Fog computing environments. Software: Practice and Experience, 47(9), 1275-1296.

    Created on Wed Nov 22 15:03:21 2017

    @author: isaac

"""
import random

import argparse

from yafs.core import Sim
from yafs.application import Application,Message

from yafs.population import *
from yafs.topology import Topology

from selection_multipleDeploys import BroadPath
from placement_Cluster_Edge import CloudPlacement,FogPlacement
from yafs.utils import *
import time

RANDOM_SEED = 1

def create_application():
    # APLICATION
    a = Application(name="EGG_GAME")

    a.set_modules([{"EGG":{"Type":Application.TYPE_SOURCE}},
                   {"Display": {"Type": Application.TYPE_SINK}},
                   {"Client": {"RAM": 10, "Type": Application.TYPE_MODULE}},
                   {"Calculator": {"RAM": 10, "Type": Application.TYPE_MODULE}},
                   {"Coordinator": {"RAM": 10, "Type": Application.TYPE_MODULE}}
                   ])
    """
    Messages among MODULES (AppEdge in iFogSim)
    """
    m_egg = Message("M.EGG", "EGG", "Client", instructions=2000*10^6, bytes=500)
    m_sensor = Message("M.Sensor", "Client", "Calculator", instructions=3500*10^6, bytes=500)
    m_player_game_state = Message("M.Player_Game_State", "Calculator", "Coordinator", instructions=1000*10^6, bytes=1000)
    m_concentration = Message("M.Concentration", "Calculator", "Client", instructions=14*10^6, bytes=500, broadcasting=True)           # This message is sent to all client modules
    m_global_game_state = Message("M.Global_Game_State", "Coordinator", "Client", instructions=28*10^6, bytes=1000, broadcasting=True) # This message is sent to all client modules
    m_global_state_update = Message("M.Global_State_Update", "Client", "Display",instructions=1000*10^6,bytes=500)
    m_self_state_update = Message("M.Self_State_Update", "Client", "Display",instructions=1000*10^6,bytes=500)

    """
    Defining which messages will be dynamically generated # the generation is controlled by Population algorithm
    """
    a.add_source_messages(m_egg)

    """
    MODULES/SERVICES: Definition of Generators and Consumers (AppEdges and TupleMappings in iFogSim)
    """
    # MODULE SOURCES: only periodic messages
    a.add_service_source("Calculator", next_time_periodic, m_player_game_state, time_shift=100.0) #According with the comments on VRGameFog.java, the period is 100ms
    a.add_service_source("Coordinator", next_time_periodic, m_global_game_state, time_shift=100.0)
    # MODULE SERVICES
    a.add_service_module("Client", m_egg, m_sensor, fractional_selectivity, threshold=0.9)
    a.add_service_module("Client", m_concentration, m_self_state_update, fractional_selectivity, threshold=1.0)
    a.add_service_module("Client", m_global_game_state, m_global_state_update, fractional_selectivity, threshold=1.0)
    a.add_service_module("Calculator", m_sensor, m_concentration, fractional_selectivity, threshold=1.0)
    a.add_service_module("Coordinator", m_player_game_state)


    """
    The concept of "loop" (in iFogSim) is not necessary in YAFS, we can extract this information from raw-data
    """

    return a



def create_json_topology(numOfDepts,numOfMobilesPerDept):
    """
       TOPOLOGY DEFINITION

       Some attributes of fog entities (nodes) are approximate
       """

    # CLOUD Abstraction
    id = 0
    cloud_dev = {"id": id, "model": "Cluster", "IPT": 44800 * 10 ^ 6, "RAM": 40000,
                 "COST": 3,"WATT":20.0}
    id +=1
    # PROXY DEVICE
    proxy_dev = {"id":id, "model": "Proxy-server", "IPT": 2800* 10 ^ 6, "RAM": 4000,
                 "COST": 3,"WATT":40.0}

    topology_json = {"entity": [cloud_dev, proxy_dev], "link": [{"s": 0, "d": 1, "BW": 10000, "PR": 100}]}
    id += 1

    for idx in range(numOfDepts):
        #GATEWAY DEVICE
        gw = id
        topology_json["entity"].append(
            {"id": id, "model": "d-", "IPT": 2800 * 10 ^ 6, "RAM": 4000, "COST": 3,"WATT":40.0})
        topology_json["link"].append({"s": 1, "d": id, "BW": 100, "PR": 4})
        id += 1

        for idm in range(numOfMobilesPerDept):
            #MOBILE DEVICE
            topology_json["entity"].append(
                {"id": id, "model": "m-", "IPT": 1000 * 10 ^ 6, "RAM": 1000, "COST": 0,
                 "WATT": 40.0})
            topology_json["link"].append({"s": gw, "d": id, "BW": 100, "PR": 2})
            id += 1
            # SENSOR
            topology_json["entity"].append(
                {"id": id, "model": "s", "COST": 0,"WATT":0.0})
            topology_json["link"].append({"s": id - 1, "d": id, "BW": 100, "PR": 6})
            id += 1
            # ACTUATOR
            topology_json["entity"].append(
                {"id": id, "model": "a", "COST": 0,"WATT":0.0})
            topology_json["link"].append({"s": id - 2, "d": id, "BW": 100, "PR": 1})
            id += 1


    return topology_json

# @profile
def main(simulated_time,depth,police):

    random.seed(RANDOM_SEED)

    """
    TOPOLOGY from a json
    """
    numOfDepts = depth
    numOfMobilesPerDept = 4  # Thus, this variable is used in the population algorithm
    # In YAFS simulator, entities representing mobiles devices (sensors or actuactors) are not necessary because they are simple "abstract" links to the  access points
    # in any case, they can be implemented with node entities with no capacity to execute services.
    #

    t = Topology()
    t_json = create_json_topology(numOfDepts,numOfMobilesPerDept)
    t.load(t_json)

    t.write("network_%s.gexf"%depth)


    """
    APPLICATION
    """
    app = create_application()

    """
    PLACEMENT algorithm
    """
    #In this case: it will deploy all app.modules in the cloud
    if police == "cloud":
        print "cloud"
        placement = CloudPlacement("onCloud")
    else:
        print "EDGE"
        placement = FogPlacement("onProxies")

    placement.scaleService(
        {"Calculator": numOfMobilesPerDept, "Coordinator": numOfDepts * numOfMobilesPerDept})

    # placement = ClusterPlacement("onCluster", activation_dist=next_time_periodic, time_shift=600)
    """
    POPULATION algorithm
    """
    #In ifogsim, during the creation of the application, the Sensors are assigned to the topology, in this case no. As mentioned, YAFS differentiates the adaptive sensors and their topological assignment.
    #In their case, the use a statical assignment.
    pop = Statical("Statical")
    #For each type of sink modules we set a deployment on some type of devices
    #A control sink consists on:
    #  args:
    #     model (str): identifies the device or devices where the sink is linked
    #     number (int): quantity of sinks linked in each device
    #     module (str): identifies the module from the app who receives the messages
    pop.set_sink_control({"model": "a","number":1,"module":app.get_sink_modules()})

    #In addition, a source includes a distribution function:
    pop.set_src_control({"model": "s", "number":1,"message": app.get_message("M.EGG"), "distribution": deterministicDistribution,"param": {"time_shift": 40}})#5.1}})

    """--
    SELECTOR algorithm
    """
    #Their "selector" is actually the shortest way, there is not type of orchestration algorithm.
    #This implementation is already created in selector.class,called: First_ShortestPath
    selectorPath = BroadPath(numOfMobilesPerDept,police)

    """
    SIMULATION ENGINE
    """

    stop_time = simulated_time
    s = Sim(t, default_results_path="Results_%s_%i_%i" % (police, stop_time, depth))
    s.deploy_app(app, placement, pop, selectorPath)
    s.run(stop_time,test_initial_deploy=False,show_progress_monitor=False)
    # s.draw_allocated_topology() # for debugging

if __name__ == '__main__':
    import logging.config
    import os

    logging.config.fileConfig(os.getcwd()+'/logging.ini')

    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--time", help="Simulated time ")
    parser.add_argument("-d", "--depth", help="Depths ")
    parser.add_argument("-p", "--police", help="cloud or edge ")
    args = parser.parse_args()

    if not args.time:
        stop_time = 1000
    else:
        stop_time = int(args.time)

    start_time = time.time()
    if not args.depth:
        dep  = 4
    else:
        dep = int(args.depth)

    if not args.police:
        police = "edge"
    else:
        police = str(args.police)

    main(stop_time,dep,police)

    print("\n--- %s seconds ---" % (time.time() - start_time))