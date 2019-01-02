# -*- coding: utf-8 -*-
"""
Created on Sat Jul 28 15:12:14 2018

@author: mwi
"""


from pyproj import Proj, transform
import math
import numpy as np
import networkx as nx
import os
import matplotlib.pyplot as plt
import matplotlib.patches as pat
import random


def load_params(use_case, path_file):
    
    assert (use_case != "FZJ" or use_case != "EON" or use_case != "simple_test"), "Use case '" + use_case + "' not known."
    path_input = path_file + "\\input_data\\" + use_case + "\\"
    print("Using data set: '" + use_case + "'")
    
    time_steps = range(8760)
    
    # Create dict with node information
    nodes = {}       
        
    if use_case == "FZJ":
        
        # load node data 
        path_nodes = path_input + "nodes.txt"
        path_demands = path_input + "demands\\"
        latitudes =  np.loadtxt(open(path_nodes, "rb"), delimiter = ",", usecols=(0))                       # °,        node latitudes
        longitudes =  np.loadtxt(open(path_nodes, "rb"), delimiter = ",", usecols=(1))                      # °,        node latitudes
        names = np.genfromtxt(open(path_nodes, "rb"),dtype = 'str', delimiter = ",", usecols=(3))       # --,            node names
        
        t_air = np.loadtxt(open("input_data/weather.csv", "rb"), delimiter = ",",skiprows = 1, usecols=(0))        # Air temperatur °C
                    
        
        # Select 5 random nodes
#        random_nodes = []
#        for x in range(5):
#            random_nodes.append(random.randint(0,16))

        for index in range(len(latitudes)):
#        for index in range(5):
            nodes[index] = {
                            "number": index,
                            "lat": latitudes[index],
                            "lon": longitudes[index],
                            "name": names[index],
                            "heat": np.loadtxt(open(path_demands + names[index] + "_heating.txt", "rb"),delimiter = ",", usecols=(0)),    # kW, heat demand
                            "cool": np.loadtxt(open(path_demands + names[index] + "_cooling.txt", "rb"),delimiter = ",", usecols=(0)),    # kW, cooling demand 
                            "T_heating_supply": 54.75 - 0.7471 * t_air,                       # °C, supply temperature for heating
                            "T_cooling_supply": 10 * np.ones(8760),                           # °C, supply temperature for cooling
                            "T_cooling_return": 15 * np.ones(8760)                            # °C, cooling return temperature
#                            "x": random.random()*100,
#                            "y": random.random()*100
                            }
            
        
        for n in nodes:
             if nodes[n]["name"] == "16.4" or nodes[n]["name"] == "16.3":
                 # nodes[n]["T_cooling_supply"] = 20 * np.ones(8760)
                 nodes[n]["T_cooling_return"] = 30 * np.ones(8760)
             
            
            
       
        
        nodes = transform_coordinates(nodes)
        
#        for k in range(len(nodes)):
#            plt.plot(nodes[k]["x"], nodes[k]["y"],".")
#        
#        plt.show()
        


#%% GENERAL PARAMETERS
    param = {"interest_rate":  0.05,        # ---,          interest rate
             "observation_time": 20.0,      # a,            project lifetime
             
             "price_gas": 0.02824,          # kEUR/MWh,     natural gas price
             "price_cap_gas": 12.149,       # kEUR/(MW*a)   capacity charge for gas grid usage
             
             "price_el": 0.14506,           # kEUR/MWh,     electricity price
             "price_cap_el": 59.660,        # kEUR/(MW*a)   capacity charge for electricity grid usage
             
             "revenue_feed_in": 0.06442,    # kEUR/MWh,     feed-in revenue for CHP-generated power
             
             "gas_CO2_emission": 0.2,       # t_CO2/MWh,    specific CO2 emissions (natural gas)
             "grid_CO2_emission": 0.503,    # t_CO2/MWh,    specific CO2 emissions (grid)
             
             "MIPGap":      1e-5,           # ---,          MIP gap            
             
             "number_of_balancing_units": 1,
             
             "switch_building_optimization": 1,     # 0: heuristic buildlng balancing; 1: optimal building balancing
             "switch_nodewise": 0,                  # 1: seperate intra balancing for every building  0: intra balancing of all buildings at the same time
                                                      
             "weight_el": 0.12,                     # EUR/kWh, electricity costs for intra-building-balancing
             "weight_heat": 0.03,                   # EUR/kWh, heat costs for intra-building-balancing
             "weight_cool": 0.06,                   # EUR/kWh, cooling costs for intra-building-balancing

#             
#             "price_cool": 1000,            # kEUR/MWh,     price for cooling power from the district cooling grid
#             "price_heat": 1000,            # kEUR/MWh,     price for heating power from the district heating grid
             
             "use_eh_in_bldgs": 1,                 # ---,          should electric heaters be used in buildings?
             "use_boi_in_bldgs": 1,                # ---,          should boilers be used in buildings?
             "use_free_cooler_in_bldgs": 1,        # ---,  should free coolers be used in buildings?
             "use_air_cooler_in_bldgs": 1,         # ---,   should air coolers be used in buildings?
#             "direct_cooling": 0,
             "op_hours_el_heater": 500,    # h,            hours in which the eletric heater is operated
             
             "switch_combined_storage": 1,    # ---,        1: integrated hot and cold storage, 0: two seperated storages for heating and cooling  
             "n_storage_changes": 4,          # ---,        maximum number of storage function changes per year ( hot <-> cold)
                             
             "obj_weight_tac": 1,           # ---,          weight for objective function, co2 emission is then 1-obj_weight_tac
             "feasible_TES": 1,             # ---,          are thermal energy storages feasible for BU?
#             "feasible_BAT": 0,             # ---,          are batteries feasible for BU?
#             "feasible_CTES": 0,            # ---,          are cold thermal energy storages feasible for BU?
             "feasible_BOI": 1,             # ---,          are gas-fired boilers feasible for BU?
#             "feasible_from_DH": 0,         # ---,          is a connection to district heating network possible?
#             "feasible_from_DC": 0,         # ---,          is a connection to district cooling network possible?
             "feasible_CHP": 1,             # ---,          are CHP units feasible for BU?
             "feasible_EH": 1,              # ---,          are electric heater feasible for BU?
             "feasible_CC": 1,              # ---,          are compression chiller feasible for BU?
             "feasible_AC": 1,              # ---,          are absorbtion chiller feasible for BU?
             }


    #%% PIPE TEMPERATURES
    param_temperatures = {"T_hot": 12 * np.ones(8760),      # °C,   hot pipe temperature
                          "T_cold": 7 * np.ones(8760),     # °C,   cold pipe temperature
                          }
    
    param.update(param_temperatures)


    
    #%% SOIL PARAMETERS   
    param_soil = {"alpha_soil": 0.8,            #---,       soil surface absorptance
                  "epsilon_soil": 0.9,          #---,       soil surface emissivity
                  "evaprate_soil": 0.7,         #---,       soil surface evaporation rate
                  "lambda_soil": 1.9,           # W/(m*K),  soil heat conductivity
                  "heatcap_soil": 2.4e6,        # J/(m^3*K),soil volumetric heat capacity 
                  }
    param.update(param_soil)
    
    
    #%% ASPHALT LAYER PARAMETERS
    param_asphalt = {"asphaltlayer": 1,          #---,       consideration of asphalt layer? 1 = yes, 0 = no
                     "d_asph": 0.18,             # m,        asphalt layer thickness
                     "alpha_asph": 0.93,         #---,       asphalt surface absorptance
                     "epsilon_asph": 0.88,       #---,       asphalt surface emissivity
                     "evaprate_asph": 0.3,       #---,       asphalt surface evaporation rate
                     "lambda_asph": 0.7,         # W/(m*K),  asphalt heat conductivity
                     "heatcap_asph": 1950400}    # J/(m^3*K),asphalt volumetric heat capacity
    
    param.update(param_asphalt)   
      
    
    #%% PIPE PARAMETERS
    param_pipe = {"grid_depth": 1,                  # m,        installation depth beneath surface
                  "lambda_PE": 0.4,                 # W(m*K),   PE heat conductivity
                  "f_fric": 0.025,                  # ---,      pipe friction factor
                  "dp_pipe": 150,                   # Pa/m,     nominal pipe pressure gradient
                  "c_f": 4180,                      # J/(kg*K), fluid specific heat capacity
                  "rho_f": 1000,                    # kg/m^3,   fluid density                 
                  "conv_pipe": 3600,                # W/(m^2 K) convective heat transfer
                  "R_0": 0.0685,                    # m^2*K/W, pipe surface correction for thermal resitance (see DIN EN 13941)   
                  }                   
                  
    param.update(param_pipe)  
    
    param_pipe_eco = {"inv_earth_work": 250,                # EUR/m,           preparation costs for pipe installation
                       "inv_pipe_PE": 0.114671,             # EUR/(cm^2*m),    diameter price for PE pipe without insulation                     
                       "pipe_lifetime": 30,                 # a,               pipe life time (VDI 2067)
                       "cost_om_pipe": 0.005                 #---,             pipe operation and maintetance costs as share of investment (VDI 2067)
                       }
                
    param.update(param_pipe_eco)
    
    



    
    
    #%% LOAD BALANCING DEVICES PARAMETER
    
    devs = {}

    
    
    #%% BOILER
    devs["BOI"] = {
                   "eta_th": 0.9,       # ---,    thermal efficiency
                   "life_time": 20,     # a,      operation time (VDI 2067)
                   "cost_om": 0.03,     # ---,    annual operation and maintenance costs as share of investment (VDI 2067)
                   }
    
    
    devs["BOI"]["cap_i"] =  {  0: 0,        # MW_th 
                               1: 0.5,      # MW_th
                               2: 5         # MW_th
                               }
    
    devs["BOI"]["inv_i"] = {    0: 0,       # kEUR
                                1: 33.75,   # kEUR
                                2: 96.2     # kEUR
                                }
    

    #%% COMBINED HEAT AND POWER - INTERNAL COMBUSTION ENGINE POWERED BY NATURAL GAS
    devs["CHP"] = {
                   "eta_el": 0.419,     # ---,           electrical efficiency
                   "eta_th": 0.448,     # ---,           thermal efficiency
                   "life_time": 15,     # a,             operation time (VDI 2067)
                   "cost_om": 0.08,     # ---,           annual operation and maintenance costs as share of investment (VDI 2067)
                   }   
    
    devs["CHP"]["cap_i"] =  {  0: 0,        # MW_el
                               1: 0.25,     # MW_el
                               2: 1,        # MW_el
                               3: 3         # MW_el
                               }
    
    devs["CHP"]["inv_i"] = {    0: 0,           # kEUR
                                1: 211.15,      # kEUR
                                2: 410.7,       # kEUR
                                3: 707.6        # kEUR
                                } 
    

    
    #%% ABSORPTION CHILLER
    devs["AC"] = {
                  "eta_th": 0.68,       # ---,        nominal thermal efficiency (cooling power / heating power)
                  "life_time": 18,      # a,          operation time (VDI 2067)
                  "cost_om": 0.03,      # ---,        annual operation and maintenance costs as share of investment (VDI 2067)
                  }
    
    devs["AC"]["cap_i"] =   {  0: 0,        # MW_th
                               1: 0.25,     # MW_th
                               2: 1.535,    # MW_th
                               3: 5.115     # MW_th
                               }
    
    devs["AC"]["inv_i"] = {     0: 0,           # kEUR
                                1: 135.9,       # kEUR
                                2: 366.3,     # kEUR
                                3: 802        # kEUR
                                } 

    #%% COMPRESSION CHILLER
    devs["CC"] = {
                  "life_time": 15,      # a,               operation time (VDI 2067)
                  "cost_om": 0.035,     # ---,             annual operation and maintenance costs as share of investment (VDI 2067)
                  "dT_cond": 5,
                  "dT_evap": param["T_hot"] - param["T_cold"],
                  "dT_min_cooler": 10,
                  "dT_pinch": 2,
                  "eta_compr": 0.75,     # ---,            isentropic efficiency of compression
                  "heatloss_compr": 0.1,  # ---,           heat loss rate of compression 
                  "COP_max": 6
                  }
    
    devs["CC"]["COP"] = calc_COP(devs, param, "CC", devs["CC"]["dT_cond"])
    
    
    devs["CC"]["cap_i"] = { 0: 0,       # MW_th
                            1: 0.5,     # MW_th
                            2: 4        # MW_th
                            }
    
    
    devs["CC"]["inv_i"] = { 0: 0,         # kEUR
                            1: 95,     # kEUR
                            2: 501      # kEUR
                            } 

    
    #%% ELECTRICAL HEATER
#    # PARAMETER PRÜFEN
#    devs["EH"] = {
#                  "eta_th": 0.9,        # ---,              thermal efficiency
#                  "life_time": 20,      # a,                operation time
#                  "cost_om": 0.01,      # ---,              annual operation and maintenance costs as share of investment
#                  }
#    
#    devs["EH"]["cap_i"] = { 0: 0,       # MW_th
#                            1: 5,       # MW_th
#                            }
#    
#    
#    devs["EH"]["inv_i"] = { 0: 0,         # kEUR
#                            1: 390,       # kEUR
#                            } 
    
    
    
    #%% LOAD DOMESCTIC TECHNICAL BUILDING EQUIPMENT (TBE) DEVICE PARAMETERS
    # PRÜFEN!

    devs_dom = {}

    devs_dom["BOI"] = {
                            "life_time": 20,       # a,    operation time (VDI 2067)
                            "inv_var": 70,        # EUR/kW, domestic heat pump investment costs
                            "inv_fix": 0,
                            "cost_om": 0.03,      #---,   annual operation and maintenance as share of investment (VDI 2067)
                            "eta_th": 0.9
                            }    
    
    
    devs_dom["HP"] = {
                            "life_time": 20,       # a,    operation time (VDI 2067)
                            "inv_var": 200,        # EUR/kW, domestic heat pump investment costs
                            "inv_fix": 0,
                            "cost_om": 0.025,      #---,   annual operation and maintenance as share of investment (VDI 2067)
                            "COP_max": 7
                            }
    
    devs_dom["CC"] = {
                           "life_time": 15,      # a,      operation time (VDI 2067)
                           "inv_var": 200,       # EUR/kW, domestic heat pump investment costs
                           "inv_fix": 0,
                           "cost_om": 0.035,     #---,     annual operation and maintenance as share of investment (VDI 2067)
                           "COP_max": 6
                            }
    
    
    devs_dom["EH"] = {
                            "eta_th": 0.98,        # ---, electric heater efficiency PRÜFEN
                            "life_time": 20,       # a,    operation time (VDI 2067)
                            "inv_var": 162.95,     # EUR/kW, domestic heat pump investment costs
                            "inv_fix": 0,          # EUR 
                            "cost_om": 0.02,       #---,   annual operation and maintenance as share of investment 
                            }  
    
    devs_dom["free_cooler"] = {
                            "dT_min": 3,
                            "life_time": 30,       # a,    operation time (VDI 2067)
                            "inv_var": 11.436,     # EUR/kW, domestic heat pump investment costs
                            "inv_fix": 3896,       # EUR
                            "cost_om": 0.03,       #---,   annual operation and maintenance as share of investment 
                            } 
    
    devs_dom["air_cooler"] = {
                            "dT_min": 10,
                            "life_time": 20,        # a,    operation time (VDI 2067)
                            "inv_var": 37.419,      # EUR/kW, domestic heat pump investment costs
                            "inv_fix": 312.93,      # EUR
                            "cost_om": 0.035,        #---,   annual operation and maintenance as share of investment (VDI)
                            } 
    
    # Calculate COP of domestic HPs and CCs
    devs_dom = calc_COP_buildings(param, devs_dom, nodes)



    
    
    
    #%% THERMAL ENERGY STORAGE
    
    for device in ["TES", "CTES"]:
    
        devs[device] = {
                       "max_cap": 50,      # MWh_th,            maximum thermal storage capacity
                       "min_cap": 0,        # MWh_th,           minimum thermal storage capacity              
                       "sto_loss": 0.005,   # 1/h,              standby losses over one time step
                       "eta_ch": 0.975,     # ---,              charging efficiency
                       "eta_dch": 0.975,    # ---,              discharging efficiency
                       "max_ch": 2,         # MW,               maximum charging power
                       "max_dch": 2,        # MW,               maximum discharging power
                       "soc_init": 1,     # ---,              maximum initial state of charge
                       "soc_max": 1,        # ---,              maximum state of charge
                       "soc_min": 0,        # ---,              minimum state of charge
                       "life_time": 20,     # a,                operation time (VDI 2067 Trinkwasserspeicher)
                       "cost_om": 0.02,     # ---,              annual operation and maintenance costs as share of investment (VDI 2067 Trinkwasserspeicher)
                       }
        
        devs["TES"]["cap_i"] =   { 0: 0,         # MWh_th,      depends on temperature difference! Q = V * c_p * rho * dT
                                   1: 8.128,     # MWh_th       PRÜFEN!!!!!
                                   2: 40.639,    # MWh_th
                                   3: 243.833    # MWh_th
                                   }
        
        devs["TES"]["inv_i"] = {    0: 0,              # kEUR
                                    1: 147.2,          # kEUR,    includes factor of 1.15 for pressure correction factor due to high temperatures; higher pressure is needed to prevent evaporation
                                    2: 410.55,         # kEUR       PRÜFEN!!!!
                                    3: 1083.3          # kEUR
                                    } 
    
    
    
#%%        
#    #%% BATTERY
#    devs["BAT"] = {"inv_var": 520,      # kEUR/MWh_el,      variable investment
#                   "max_cap": 50,       # MWh_el,           maximum eletrical storage capacity
#                   "sto_loss": 0,       # 1/h,              standby losses over one time step
#                   "eta_ch": 0.9592,    # ---,              charging efficiency
#                   "eta_dch": 0.9592,   # ---,              discharging efficiency
#                   "soc_init": 0.8,     # ---,              maximum initial relative state of charge
#                   "soc_max": 0.8,        # ---,              maximum relative state of charge
#                   "soc_min": 0.2,        # ---,              minimum relative state of charge
#                   "life_time": 10,     # a,                operation time
#                   "cost_om": 0.02,     # ---,              annual operation and maintenance costs as share of investment
#                   }



#    #%% COLD THERMAL ENERGY STORAGE
#    devs["CTES"] = {"inv_var": 11.7,    # kEUR/MWh_th,      variable investment
#                    "max_cap": 5000,      # MWh_th,           maximum thermal storage capacity
#                    "sto_loss": 0.005,  # 1/h,              standby losses over one time step
#                    "eta_ch": 0.975,    # ---,              charging efficiency
#                    "eta_dch": 0.975,   # ---,              discharging efficiency
#                    "soc_init": 0.8,    # ---,              maximum initial state of charge
#                    "soc_max": 1,       # ---,              maximum state of charge
#                    "soc_min": 0,       # ---,              minimum state of charge
#                    "life_time": 20,    # a,                operation time
#                    "cost_om": 0.01,    # ---,              annual operation and maintenance costs as share of investment
#                    }
    
#    #%% CONNECTION TO DISTRICT COOLING NETWORK
#    devs["from_DC"] = {"inv_var": 11.7,    # kEUR/MW_th,      variable investment
#                       "max_cap": 5000,    # MW_th,           maximum thermal storage capacity
#                       "min_cap": 0,       # MW_th,           minimum thermal storage capacity              
#                       "eta_th": 0.99,     # ---,             discharging efficiency
#                       "life_time": 50,    # a,               operation time
#                       "cost_om": 0.01,    # ---,             annual operation and maintenance costs as share of investment
#                       }

#    #%% CONNECTION TO DISTRICT HEATING NETWORK
#    devs["from_DH"] = {"inv_var": 11.7,    # kEUR/MW_th,      variable investment
#                       "max_cap": 5000,    # MW_th,           maximum thermal storage capacity
#                       "min_cap": 0,       # MW_th,           minimum thermal storage capacity              
#                       "eta_th": 0.99,     # ---,             discharging efficiency
#                       "life_time": 50,    # a,               operation time
#                       "cost_om": 0.01,    # ---,             annual operation and maintenance costs as share of investment
#                       }

    # Calculate annualized investment of every device
    devs = calc_annual_investment(devs, devs_dom, param)

    return nodes, param, devs, devs_dom, time_steps

#def get_grid_temp_hot_pipe(mode, time_steps):
#    if mode == "two_point_control":
#        grid_temp_hot_pipe = np.zeros(len(time_steps))
#        grid_temp_summer = 16
#        grid_temp_winter = 22
#        grid_temp_hot_pipe[0:3754] = grid_temp_winter
#        grid_temp_hot_pipe[3754:7040] = grid_temp_summer
#        grid_temp_hot_pipe[7040:8760] = grid_temp_winter
#        
#        with open("D:\\mwi\\Gurobi_Modelle\EctoPlanner\\temp.txt", "w") as outfile:
#            for t in time_steps:
#                outfile.write(str(round(grid_temp_hot_pipe[t],3)) + "\n")   
#        
#    return grid_temp_hot_pipe

#%%
#def calc_pipe_costs(nodes, edges, edge_dict_rev, param):
#    """
#    Calculate variable and fix costs for every edge.
#    """
#    c_fix = {}
#    c_var = {}
#    for e in edges:
#        x1, y1 = nodes[edge_dict_rev[e][0]]["x"], nodes[edge_dict_rev[e][0]]["y"]
#        x2, y2 = nodes[edge_dict_rev[e][1]]["x"], nodes[edge_dict_rev[e][1]]["y"]
#        length = math.sqrt((x1-x2)**2 + (y1-y2)**2)
#        c_fix[e] = param["inv_earth_work"] * length
#        c_var[e] = param["inv_pipe_PE"] * length
#    
#    param["inv_pipe_fix"] = c_fix
#    param["inv_pipe_var"] = c_var
#    return param


#%%
def get_edge_dict(n, nodes):
    compl_graph = nx.complete_graph(n)                                                      # Creates graph with n nodes 0 to n-1 and edges between every pair of nodes
    edge_list = list(compl_graph.edges(data=False))                                         # get list of edges
    edge_dict = {(edge_list[k][0], edge_list[k][1]): k for k in range(len(edge_list))}      # dicts indcluding edge numbers
    edge_dict_rev = {k: (edge_list[k][0], edge_list[k][1]) for k in range(len(edge_list))}
    edges = range(len(edge_list))   # list containing edge indices
    
    # create dict containing edge lengths
    edge_lengths = {}
    for e in edges:
        x1, y1 = nodes[edge_dict_rev[e][0]]["x"], nodes[edge_dict_rev[e][0]]["y"]
        x2, y2 = nodes[edge_dict_rev[e][1]]["x"], nodes[edge_dict_rev[e][1]]["y"]
        length = math.sqrt((x1-x2)**2 + (y1-y2)**2)
        edge_lengths[e] = length
                                                           
    return edge_dict, edge_dict_rev, edges, compl_graph, edge_list, edge_lengths

#%%
def transform_coordinates(nodes):
    outProj = Proj(init='epsg:25832')   # ETRS89 / UTM zone 32N
    inProj = Proj(init='epsg:4258')     # Geographic coordinate system: EPSG 4258 (Europe)
    
    # get x- and y- coordinates and find minimal values of each
    min_x, min_y = transform(inProj,outProj,nodes[0]["lon"],nodes[0]["lat"])
    for n in range(len(nodes)):
        nodes[n]["x"],nodes[n]["y"] = transform(inProj,outProj,nodes[n]["lon"],nodes[n]["lat"])
        if nodes[n]["x"] < min_x:
            min_x = nodes[n]["x"]
        if nodes[n]["y"] < min_y:
            min_y = nodes[n]["y"]
    
    # Shift coordinate system by minimal x- and y- value        
    for n in range(len(nodes)):
        nodes[n]["x"] = nodes[n]["x"] - min_x
        nodes[n]["y"] = nodes[n]["y"] - min_y
        
    return nodes


    
#%%
def calc_annual_investment(devs, devs_dom, param):
    """
    Calculation of total investment costs including replacements (based on VDI 2067-1, pages 16-17).

    Parameters
    ----------
    dev : dictionary
        technology parameter
    param : dictionary
        economic parameters

    Returns
    -------
    annualized fix and variable investment
    """

    observation_time = param["observation_time"]
    interest_rate = param["interest_rate"]
    q = 1 + param["interest_rate"]

    
    # Balancing devices
    
    # Calculate capital recovery factor
    CRF = ((q**observation_time)*interest_rate)/((q**observation_time)-1)

    # Calculate annuity factor for each device
    for device in devs.keys():
        
        # Get device life time
        life_time = devs[device]["life_time"]

        # Number of required replacements
        n = int(math.floor(observation_time / life_time))
        
        # Inestment for replcaments
        invest_replacements = sum((q ** (-i * life_time)) for i in range(1, n+1))

        # Residual value of final replacement
        res_value = ((n+1) * life_time - observation_time) / life_time * (q ** (-observation_time))

        # Calculate annualized investments       
        if life_time > observation_time:
            devs[device]["ann_factor"] = (1 - res_value) * CRF 
        else:
            devs[device]["ann_factor"] = ( 1 + invest_replacements - res_value) * CRF 
       
    
    # Building devices
    
    for device in devs_dom.keys():
        
        # Get device life time
        life_time = devs_dom[device]["life_time"]
        inv_fix = devs_dom[device]["inv_fix"]
        inv_var = devs_dom[device]["inv_var"]

        # Number of required replacements
        n = int(math.floor(observation_time / life_time))
        
        # Inestment for replcaments
        invest_replacements = sum((q ** (-i * life_time)) for i in range(1, n+1))

        # Residual value of final replacement
        res_value = ((n+1) * life_time - observation_time) / life_time * (q ** (-observation_time))

        # Calculate annualized investments       
        if life_time > observation_time:
            devs_dom[device]["ann_inv_fix"] = inv_fix * (1 - res_value) * CRF
            devs_dom[device]["ann_inv_var"] = inv_var * (1 - res_value) * CRF
        else:
            devs_dom[device]["ann_inv_fix"] = inv_fix * ( 1 + invest_replacements - res_value) * CRF 
            devs_dom[device]["ann_inv_var"] = inv_var * ( 1 + invest_replacements - res_value) * CRF
            
    
    # Distribution devices (pipes, pumps)
    
    for dev in ["pipe"]: #PUmpe fehlt noch
        
        # Get device life time
        life_time = param[dev + "_lifetime"]
        
        # Number of required replacements
        n = int(math.floor(observation_time / life_time))
        
        # Inestment for replcaments
        invest_replacements = sum((q ** (-i * life_time)) for i in range(1, n+1))

        # Residual value of final replacement
        res_value = ((n+1) * life_time - observation_time) / life_time * (q ** (-observation_time))

        # Calculate annualized investments       
        if life_time > observation_time:
            param["ann_factor_" + dev] = (1 - res_value) * CRF 
        else:
            param["ann_factor_" + dev] = ( 1 + invest_replacements - res_value) * CRF 

    return devs



#%% COP correlation for domestic heat pumps and compression chillers
    
def calc_COP_buildings(param, devs_dom, nodes):
    
    A = 0.67
    B = 12.90
    
    devs_dom["HP"]["COP"] = {}
    devs_dom["CC"]["COP"] = {}
    
    for n in nodes:
        
        T_sink_HP = nodes[n]["T_heating_supply"]
        T_source_HP = param["T_hot"]
        
        T_sink_CC = param["T_hot"]
        T_source_CC = nodes[n]["T_cooling_supply"] + 1e-5
        
        
        devs_dom["HP"]["COP"][n] = A * (T_sink_HP + 273.15)/(T_sink_HP - T_source_HP + B)
        devs_dom["CC"]["COP"][n] = A * (T_sink_CC + 273.15)/(T_sink_CC - T_source_CC + B) - 1
        
        for t in range(8760):
            if devs_dom["HP"]["COP"][n][t] > devs_dom["HP"]["COP_max"] or devs_dom["HP"]["COP"][n][t] < 0:
                devs_dom["HP"]["COP"][n][t] = devs_dom["HP"]["COP_max"]
            if devs_dom["CC"]["COP"][n][t] > devs_dom["CC"]["COP_max"] or devs_dom["CC"]["COP"][n][t] < 0:
                devs_dom["CC"]["COP"][n][t] = devs_dom["CC"]["COP_max"] 
    
    return devs_dom
        
        


#%% COP model for ammonia-heat pumps
# Heat pump COP, part 2: Generalized COP estimation of heat pump processes
# DOI: 10.18462/iir.gl.2018.1386
    
def calc_COP(devs, param, device, dt_h):
    
    # 0.6 * Carnot
    
#    t_h = 273.15 + param["T_heating_return"] + devs["HP"]["dT_cond"] + devs["HP"]["dT_pinch"]
#    t_c = 273.15 + param["T_cooling_return"] - devs["HP"]["dT_evap"] - devs["HP"]["dT_pinch"]
#    
#    COP = 0.6 * t_h / (t_h - t_c)
    
    
    

    # get temperature parameters
#    dt_h = devs[device]["dT_cond"]                  # heat sink temperature difference
    dt_c = devs[device]["dT_evap"]                   # heat source temperature difference
    
    t_air = np.loadtxt(open("input_data/weather.csv", "rb"), delimiter = ",",skiprows = 1, usecols=(0))        # Air temperatur °C
    t_h_in = t_air + devs["CC"]["dT_min_cooler"] + 273.15                                                      # cooling water inlet temperature °C
    
    t_c_in = param["T_hot"] + 273.15                # heat source inlet temperature
    
    # Modeling parameters
    dt_pp = devs[device]["dT_pinch"]                # pinch point temperature difference
    eta_is = devs[device]["eta_compr"]              # isentropic compression efficiency
    f_Q = devs[device]["heatloss_compr"]            # heat loss rate during compression
    
    # Entropic mean temperautures
    t_h_s = dt_h/np.log((t_h_in + dt_h)/t_h_in)
    t_c_s = dt_c/np.log(t_c_in/(t_c_in - dt_c))
    
    for t in range(8760):
        if t_h_s[t] == t_c_s[t]:
            t_h_s[t] += 1e-5
    
    #Lorentz-COP
    COP_Lor = t_h_s/(t_h_s - t_c_s)
    
    
    # linear model equations
    dt_r_H = 0.2*(t_h_in + dt_h - (t_c_in - dt_c) + 2*dt_pp) + 0.2*dt_h + 0.016        # mean entropic heat difference in condenser deducting dt_pp
    w_is = 0.0014*(t_h_in + dt_h - (t_c_in - dt_c) + 2*dt_pp) - 0.0015*dt_h + 0.039    # ratio of isentropic expansion work to isentropic compression work
    
    
    # help values
    num = 1 + (dt_r_H + dt_pp)/t_h_s
    denom = 1 + (dt_r_H + 0.5*dt_c + 2*dt_pp)/(t_h_s - t_c_s)
    
    # COP
    COP = COP_Lor * num/denom * eta_is * (1 - w_is) + 1 - eta_is - f_Q
    
    if device == "CC":
        COP = COP - 1   # consider COP definition for compression chillers (COP_CC = Q_0/P_el = (Q - P_el)/P_el = COP_HP - 1)
    
    # limit COP's
    COP_max = devs[device]["COP_max"]
    
    if device == "CC":
        for t in range(len(COP)):
            if COP[t] > COP_max:
                COP[t] = COP_max
                
#        plt.plot(t_air,COP,".")
#        plt.show()
#        
#        plt.xlabel("Lufttemperatur °C")
#        plt.ylabel("COP_CC")
    
    elif device == "HP":
        if COP > COP_max:
            COP = COP_max
#        print(COP)
    
#        print(COP)
    return COP
    






## CODE SNIPPETS for FZJ data
    

#further parameters for topology optimization
#"inv_earth_work":              200,    # EUR/m, fix costs per meter length (earth work/construction)
#             "inv_material_var":            0.093,  # EUR/m/d # costs per meter length and diameter (pipe costs)
#             "inv_material_fix":            29.71,  # EUR/m # costs per meter length (pipe costs)
#             "number_of_balancing_units": 1,      # maximum number of nodes in which balancing units can be build
#    "T_supply_pipe": 18,           #
#             "T_return_pipe": 12,           # 
#             "c_P_water": 4.18,             # kJ/(kg K),    specific heat capacity for water
#             
             
      
#    nodes = transform_coordinates(nodes)
#    
#    # Load demands
#
#    ending = {"power": "_electricity.txt", "heat": "_heating.txt", "cool": "_cooling.txt"}
#    build = {}
#    path_load = {}
#    for n in range(len(nodes)):
#        build_name = nodes[n]["name"]
#        for com in nodes[n]["commodities"]:
#                path_load[com] = path_demand_files + build_name + ending[com]
#                build[com] = np.loadtxt(open(path_load[com], "rb"), delimiter=",", usecols=(0))
#            
#                # filter outlier (manually checked for the two buildings)
#                if build_name == "1520":
#                    for k in range(len(build[com])):
#                        if build[com][k] > 1000:
#                            build[com][k] = build[com][k-1] 
#                
#                if build_name == "1613":
#                    for k in range(len(build[com])):
#                        if build[com][k] > 1000:
#                            build[com][k] = build[com][k-1] 
#                            
#                nodes[n][com] = build[com]
#                print("Building " + build_name + " (" + com + ") loaded successfully. ")
        

    #%% Use case: FZJ (Forschungszentrum Juelich)
    
#    if use_case == "FZJ":
#        pass
        # path_weather_file = str(os.path.dirname(os.path.realpath(__file__)) + "\\input_data\\TRY2015_37335002675500_Jahr.csv")
#        path_demand_files = "input_data\\processed_data_2018-07-03_21-34-53\\"
        
#%% Use case: Simple test (Simple use case for experimenting based on data of FZJ)
    
#    if use_case == "simple_test":
#        
#        nodes[0] = {"lon":      1, # longitude
#                    "lat":      0, # latitude 
#                    "name":  "test_bldg_0",
#                    "commodities": ["heat", "cool", "power"],
#                    }
#        
#        nodes[1] = {"lon":      1, # longitude
#                    "lat":      1, # latitude 
#                    "name":  "test_bldg_1",
#                    "commodities": ["heat", "cool", "power"],
#                    }
#        
#        nodes[2] = {"lon":      0, # longitude
#                    "lat":      0, # latitude 
#                    "name":  "test_bldg_2",
#                    "commodities": ["heat", "cool", "power"],
#                    }
#        
#        nodes[3] = {"lon":      0, # longitude
#                    "lat":      1, # latitude 
#                    "name":  "test_bldg_3",
#                    "commodities": ["heat", "cool", "power"],
#                    } 
        
        #    else:
#            
#        nodes[0] = {"lon":      6.402940, # longitude
#                    "lat":      50.908491, # latitude 
#                    "bldg_id":  "1510",
#                    "commodities": ["heat", "cool", "power"],
#                    }
#                        
#        nodes[1] = {"lon":      6.403199, # longitude
#                    "lat":      50.909126, # latitude 
#                    "bldg_id":  "1560",
#                    "commodities": ["heat", "cool", "power"],
#                    }
#        
#        nodes[2] = {"lon":      6.402109, # longitude
#                    "lat":      50.908323, # latitude 
#                    "bldg_id":  "1570",
#                    "commodities": ["heat", "cool", "power"],
#                    }
#        
#        nodes[3] = {"lon":      6.401926, # longitude
#                    "lat":      50.908205, # latitude 
#                    "bldg_id":  "1580",
#                    "commodities": ["heat", "cool", "power"],
#                    }
        
    # 1513 auf 1580 drauf rechnen
        
#    nodes[4] = {"lon":      6.403670, # longitude
#                "lat":      50.907662, # latitude 
#                "bldg_id":  "1514",
#                "dem": {0: -1, 1: 2}
#                }
    
#    nodes[5] = {"lon":      6.403767, # longitude
#                "lat":      50.908444, # latitude 
#                "bldg_id":  "1522",
#                }
#    
#    nodes[6] = {"lon":      6.404016, # longitude
#                "lat":      50.908603, # latitude 
#                "bldg_id":  "1590",
#                }
#    
#    nodes[7] = {"lon":      6.404968, # longitude
#                "lat":      50.908360, # latitude 
#                "bldg_id":  "1520",
#                }
#    
#    nodes[8] = {"lon":      6.405162, # longitude
#                "lat":      50.908781, # latitude 
#                "bldg_id":  "1615",
#                }
#    
#    nodes[9] = {"lon":      6.406938, # longitude
#                "lat":      50.908541, # latitude 
#                "bldg_id":  "0410",
#                }
#    
#    nodes[10] = {"lon":     6.406624, # longitude
#                "lat":      50.909455, # latitude 
#                "bldg_id":  "1630",
#                }
#    
#    nodes[11] = {"lon":     6.405187, # longitude
#                "lat":      50.910320, # latitude 
#                "bldg_id":  "1613",
#                }
#    
#    nodes[12] = {"lon":     6.404774, # longitude
#                "lat":      50.910150, # latitude 
#                "bldg_id":  "1690",
#                }
#    
#    nodes[13] = {"lon":     6.404428, # longitude
#                "lat":      50.909751, # latitude 
#                "bldg_id":  "1660",
#                }
#nodes, param, devs, time_steps = load_params("FZJ", str(os.path.dirname(os.path.realpath(__file__))))
    
    
#%%
#    # get list of banned edges; each node is only allowed to connect with its closest neighbour
#def ban_edges(param, nodes, compl_graph, edge_dict, edge_dict_rev, edges):
#    
#    allowed_edges = []
#    
#    for node in range(len(nodes)):
#        
#        # find all edges which start or end at this node and calculate their length
#        all_edges = []
#        all_lengths = []
#        adjacent_edges = list(compl_graph.edges(node, data=False))        
#        for e in adjacent_edges:
#            if e[0] > e[1]:
#                e = (e[1], e[0])
#            edge_id = edge_dict[e]
#            
#            x1, y1 = nodes[edge_dict_rev[edge_id][0]]["x"], nodes[edge_dict_rev[edge_id][0]]["y"]
#            x2, y2 = nodes[edge_dict_rev[edge_id][1]]["x"], nodes[edge_dict_rev[edge_id][1]]["y"]
#            length = math.sqrt((x1-x2)**2 + (y1-y2)**2) 
#            all_edges.append(edge_id)
#            all_lengths.append(length)
#        
#        # collect allowed connections
#        n_allowed = param["n_neighbours"]      
#        # list of allowed connections [(length 1, edge_id 1), ... , (length n_allowed, edge_id n_allowed)]
#        allowed_zipped =  sorted(zip(all_lengths, all_edges))[:n_allowed]
#        
#        for item in allowed_zipped:
#            #check if edge is already allowed
#            already_allowed = 0
#            for edge in allowed_edges:
#                if edge == item[1]:
#                    already_allowed = 1
#            if already_allowed == 0:
#                allowed_edges.append(item[1])
#                
#    # remove allowed edges from edgeID-list to get banned edges
#    banned_edges = list(edges)
#    for edge in allowed_edges:
#        banned_edges.remove(edge)
#            
#    return allowed_edges, banned_edges
            
    
#%% Aggregate building nodes to clusters    
#def cluster_nodes(nodes, param):
#    
#    # get length of the whole area
#    len_total_X = max(nodes[k]["x"] for k in range(len(nodes)))
#    len_total_Y = max(nodes[k]["y"] for k in range(len(nodes)))
#    
#    # cluster lengths
#    len_cluster_X = len_total_X / param["n_clusters_x"]
#    len_cluster_Y = len_total_Y / param["n_clusters_y"]
#    
#    # get cluster borders
#    dict_clusters = {}
#    for n_y in range(param["n_clusters_y"]):
#        dict_clusters[n_y] = {}
#        for n_x in range(param["n_clusters_x"]):
#            dict_clusters[n_y][n_x] = {}
#            dict_clusters[n_y][n_x]["ID"] = str(n_y) + str(n_x)
#            dict_clusters[n_y][n_x]["dy"] = [(param["n_clusters_y"]-n_y-1)*len_cluster_Y, (param["n_clusters_y"]-n_y)*len_cluster_Y]
#            dict_clusters[n_y][n_x]["dx"] = [n_x*len_cluster_X, (n_x+1)*len_cluster_X]
#     
#    # Assign nodes to clusters
#    for row in dict_clusters:
#        for col in dict_clusters[row]:
#            dict_clusters[row][col]["nodes"] = []
#            for n in nodes:
#                if dict_clusters[row][col]["dx"][0] <= nodes[n]["x"] and nodes[n]["x"] <= dict_clusters[row][col]["dx"][1] and dict_clusters[row][col]["dy"][0] <= nodes[n]["y"] and nodes[n]["y"] <= dict_clusters[row][col]["dy"][1]:
#                    dict_clusters[row][col]["nodes"].append(n)
#    
#    # find empty clusters
#    for row in dict_clusters:
#        for col in dict_clusters[row]:
#            if len(dict_clusters[row][col]["nodes"]) == 0:
#                dict_clusters[row][col]["is_empty"] = True
#            else:
#                dict_clusters[row][col]["is_empty"] = False
#    
#    # plot cluster borders and nodes
#    # vertical borders
#    for k in range(param["n_clusters_x"] + 1):
#        x = k*len_cluster_X
#        plt.plot([x,x], [0,len_total_Y], 'k--')
#    # horizontal borders
#    for k in range(param["n_clusters_y"] + 1):
#        y = k*len_cluster_Y
#        plt.plot([0,len_total_X], [y,y], 'k--')
#    # plot nodes as dots
#    for n in nodes:
#        plt.plot(nodes[n]["x"], nodes[n]["y"], 'r.')
#    
#    plt.show()
#    
#    return dict_clusters


#def cluster_connections(dict_clusters, edge_dict):
#        
#    # find possible node connections between clusters
#    dict_connections = {}
#    for row in dict_clusters:
#        for col in dict_clusters[row]:
#            dict_connections[con] = []
#            nodes_from = dict_clusters[con[0]]["nodes"]
#            nodes_to = dict_clusters[con[1]]["nodes"]
#            # Find each possible edge between the two clusters
#            for n1 in nodes_from:
#                for n2 in nodes_to:
#                    if n2 > n1:
#                        edge = (n1,n2)
#                    else:
#                        edge = (n2,n1)
#                    dict_connections[con].append(edge_dict[edge])
#    
#    return dict_connections
    
#%% generate pseudo demands
#def generate_demands(edge_list, edge_dict, nodes):
#    
#    # initialize demands
#    dem = {}
#    for node in nodes:
#        dem[node] = np.zeros(len(edge_list))
#    
#    for edge in edge_list:
#        index = edge_dict[edge]
#        n0 = edge[0]
#        n1 = edge[1]
#        dem[n0][index] = 1
#        dem[n1][index] = -1
#    
#    return dem