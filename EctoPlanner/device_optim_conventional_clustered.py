# -*- coding: utf-8 -*-
"""

Author: Marco Wirtz, Institute for Energy Efficient Buildings and Indoor Climate, RWTH Aachen University, Germany

Created: 01.09.2018

"""

from __future__ import division
import gurobipy as gp
import os
import json
import time
import numpy as np
import post_processing_clustered as post



def run_optim(obj_fn, obj_eps, eps_constr, nodes, param, devs, devs_dom, dir_results):

    assert (obj_eps == "" and eps_constr == "") or (obj_eps != "" and eps_constr != ""), "If there is a bounded objective function, an epsilon constraint should be given."
    
    #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    # Load model parameter
    start_time = time.time()   
          
    days = range(param["n_clusters"])
    time_steps = range(24)
    year = range(365)
    
    # Sum up building heat demands
    dem = {}
    for demand in ["heat", "cool"]:
        dem[demand] = sum(nodes[n][demand] for n in nodes) / 1000
        
    
    # Add thermal losses
    dem["heat"] = dem["heat"] + param["kA"]["heat"] * (param["T_supply"]["heat"] + param["T_return"]["heat"] - 2*param["t_soil"])/1000
    dem["cool"] = dem["cool"] + param["kA"]["cool"] * (2*param["t_soil"] - param["T_supply"]["cool"]- param["T_return"]["cool"])/1000
#    dem["heat"] = dem["heat"] + param["kA"]["heat"] * (80 - param["t_soil"])/1000
#    dem["cool"] = dem["cool"] + param["kA"]["cool"] * (param["t_soil"]- 9)/1000
    
    for demand in ["heat", "cool"]:
        for d in days:
            for t in time_steps:
                if dem[demand][d][t] < 0:
                    dem[demand][d][t] = 0
            

    param["dem_heat"] = dem["heat"]
    param["dem_cool"] = dem["cool"]
    
    
    # Create set for devices
    all_devs = ["BOI", "CHP", "AC", "CC", "SUB"]         # note: building substations are modeled as free coolers
    
    
    
    # Substation (= heat exchangers) parameters equal free-cooler parameters
    devs["SUB"] = devs_dom["FRC"]
         
    #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    # Setting up the model
    
    # Create a new model
    model = gp.Model("DHC_Benchmark")
    
    #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    # Create new variables

    # all variables that are used in post-processing are introduced, even if not needed in this model
    
    # Piece-wise linear function variables
    if param["switch_cost_functions"]:
        lin = {}
        for device in ["BOI", "CHP", "AC", "CC"]:   
            lin[device] = {}
            for i in range(len(devs[device]["cap_i"])):
                lin[device][i] = model.addVar(vtype="C", name="lin_" + device + "_i" + str(i))
            
    # Device's capacity (i.e. nominal power)
    cap = {}
    for device in ["SUB", "BOI", "CHP", "AC", "CC", "TES", "CTES", "AIRC", "HP", "EH", "BAT", "PV"]:
        cap[device] = model.addVar(vtype="C", name="nominal_capacity_" + str(device))
    
    # Gas flow to/from devices
    gas = {}
    for device in ["BOI", "CHP"]:
        gas[device] = {}
        for d in days:
            gas[device][d] = {}
            for t in time_steps:
                gas[device][d][t] = model.addVar(vtype="C", name="gas_" + device + "_d" + str(d) + "_t" + str(t))
        
    # Eletrical power to/from devices
    power = {}
    for device in ["CHP", "CC", "from_grid", "to_grid", "HP", "EH", "PV"]:
        power[device] = {}
        for d in days:
            power[device][d] = {}
            for t in time_steps:
                power[device][d][t] = model.addVar(vtype="C", name="power_" + device + "_d" + str(d) + "_t" + str(t))
       
    # Heat to/from devices
    heat = {}
    for device in ["BOI", "CHP", "AC", "HP", "EH"]:
        heat[device] = {}
        for d in days:
            heat[device][d] = {}
            for t in time_steps:
                heat[device][d][t] = model.addVar(vtype="C", name="heat_" + device + "_d" + str(d) + "_t" + str(t))
    
    # Cooling power to/from devices
    cool = {}
    for device in ["CC", "AC", "AIRC"]:
        cool[device] = {}
        for d in days:
            cool[device][d] = {}
            for t in time_steps:
                cool[device][d][t] = model.addVar(vtype="C", name="cool_" + device + "_d" + str(d) + "_t" + str(t))


    # Storage variables
    
    # initial state of charge which has to be followed at the beginning (and end) of every type-day
#    soc_init = {}
#    for device in ["TES", "CTES", "BAT"]:
#        soc_init[device] = model.addVar(vtype="C", name="initial_soc_" + device)
      
    ch = {}  # Energy flow to charge storage device
    dch = {} # Energy flow to discharge storage device
    soc = {} # State of charge

    for device in ["TES", "CTES", "BAT"]:
        ch[device] = {}
        dch[device] = {}
        soc[device] = {}
        for d in days:
            ch[device][d] = {}
            for t in time_steps:
                ch[device][d][t] = model.addVar(vtype="C", name="ch_" + device + "_d" + str(d) + "_t" + str(t))
        for d in days:
            dch[device][d] = {}
            for t in time_steps:
                dch[device][d][t] = model.addVar(vtype="C", name="dch_" + device + "_d" + str(d) + "_t" + str(t))
        for day in year:
            soc[device][day] = {}
            for t in time_steps:
                soc[device][day][t] = model.addVar(vtype="C", name="soc_" + device + "_d" + str(day) + "_t" + str(t))
#        soc[device][len(year)-1][len(time_steps)] = model.addVar(vtype="C", name="soc_" + device + "_" + str(len(year)-1) + "_t" + str(len(time_steps)))
              
        
    
    inv = {}
    c_inv = {}
    c_om = {}
    c_total = {}
    for device in all_devs:
        inv[device] = model.addVar(vtype = "C", name="investment_costs_" + device)
    for device in all_devs:
        c_inv[device] = model.addVar(vtype = "C", name="annual_investment_costs_" + device)
    for device in all_devs:
        c_om[device] = model.addVar(vtype = "C", name="om_costs_" + device)
    for device in ["SUB", "BOI", "CHP", "AC", "CC", "TES", "CTES", "AIRC", "HP", "EH", "BAT", "PV"]:
        c_total[device] = model.addVar(vtype = "C", name="total_annual_costs_" + device)            

  
    # grid maximum transmission power
    grid_limit_el = model.addVar(vtype = "C", name="grid_limit_el")  
    grid_limit_gas = model.addVar(vtype = "C", name="grid_limit_gas")
    
    # total energy amounts taken from grid and fed into grid
    from_grid_total = model.addVar(vtype = "C", name="from_grid_total")
    to_grid_total = model.addVar(vtype = "C", name="to_grid_total")
    gas_total = model.addVar(vtype = "C", name="gas_total")
    
    # total revenue for feed-in
    revenue_feed_in = {}
    for device in ["CHP", "PV"]:
        revenue_feed_in[device] = model.addVar(vtype="C", name="revenue_feed_in_"+str(device))
    # Electricity costs
    electricity_costs = model.addVar(vtype = "C", name="electricity_costs")    
    
    #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    # Objective functions
    obj = {}
    obj["tac"] = model.addVar(vtype="C", lb=-gp.GRB.INFINITY, name="total_annualized_costs") 
    obj["co2_gross"] = model.addVar(vtype="C", lb=-gp.GRB.INFINITY, name="total_CO2") 
      
    #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    # Define objective function

    model.update()
    model.setObjective(obj[obj_fn], gp.GRB.MINIMIZE)
    if obj_eps == "":
        print("-----------\nSingle-objective optimization with objective function: " + obj_fn)
    else:
        if eps_constr >= 0:
            model.addConstr(obj[obj_eps] <= eps_constr * (1 + param["MIPGap"]))
        elif eps_constr < 0:
            model.addConstr(obj[obj_eps] <= eps_constr * (1 - param["MIPGap"]))
        print("-----------\nRun optimization for '" + obj_fn + "'. Epsilon constraint for '" + obj_eps + "': " + str(eps_constr) + ".")


    #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    # Add constraints
 
    #%% DEVICE CAPACITIES
   
    # calculate from piece-wise linear function variables  
    
    if param["switch_cost_functions"]:
    
        for device in ["BOI", "CHP", "AC", "CC"]:
        
            model.addConstr(cap[device] == sum(lin[device][i] * devs[device]["cap_i"][i] for i in range(len(devs[device]["cap_i"]))))
            # lin: Special Ordered Sets of type 2 (SOS2 or S2): an ordered set of non-negative variables, of which at most two can be non-zero, and if 
            # two are non-zero these must be consecutive in their ordering. 
            model.addSOS(gp.GRB.SOS_TYPE2, [lin[device][i] for i in range(len(devs[device]["cap_i"]))])
            
            # Sum of linear function variables should be 1
            model.addConstr(1 == sum(lin[device][i] for i in range(len(devs[device]["cap_i"]))))
            
            

      

    
    #%% LOAD CONTRAINTS: minimal load < load < capacity
    
    for d in days:
        for t in time_steps:
            for device in ["BOI"]:
                model.addConstr(heat[device][d][t] <= cap[device])
                
            for device in ["CHP"]:
                model.addConstr(power[device][d][t] <= cap[device])
            
            for device in ["CC", "AC"]:
                model.addConstr(cool[device][d][t] <= cap[device])
                      
            # limitation of power from and to grid   
            model.addConstr(sum(gas[device][d][t] for device in ["BOI", "CHP"]) <= grid_limit_gas)       
            for device in ["from_grid", "to_grid"]:
                model.addConstr(power[device][d][t] <= grid_limit_el)
            
            
     # Assure that real building peak loads are met
    # heating
    model.addConstr(cap["CHP"] + cap["BOI"] >= param["peak_heat_sum"])        
    # cooling
    model.addConstr(cap["CC"] + cap["AC"] >= param["peak_cool_sum"])
            
    # Sum of substation capacities
    model.addConstr( cap["SUB"] == sum(sum( nodes[n]["peak"][demand] for demand in ["heat", "cool"]) for n in nodes) / 1000 )

    #%% INPUT / OUTPUT CONSTRAINTS
    for d in days:
        for t in time_steps:
            # Boiler
            model.addConstr(gas["BOI"][d][t] == heat["BOI"][d][t] / devs["BOI"]["eta_th"])
            
            # Combined heat and power
            model.addConstr(power["CHP"][d][t] == heat["CHP"][d][t] / devs["CHP"]["eta_th"] * devs["CHP"]["eta_el"])
            model.addConstr(gas["CHP"][d][t] == heat["CHP"][d][t] / devs["CHP"]["eta_th"])
            
            # Compression chiller
            model.addConstr(cool["CC"][d][t] == power["CC"][d][t] * devs["CC"]["COP"][d][t])  
    
            # Absorption chiller
            model.addConstr(cool["AC"][d][t] == heat["AC"][d][t] * devs["AC"]["eta_th"])
        


    #%% GLOBAL ENERGY BALANCES
    for d in days:
        for t in time_steps:
            # Heat balance
            model.addConstr(heat["BOI"][d][t] + heat["CHP"][d][t] == dem["heat"][d][t] + heat["AC"][d][t])
    
            # Electricity balance
            model.addConstr(power["CHP"][d][t] + power["from_grid"][d][t] == power["to_grid"][d][t] + power["CC"][d][t])
    
            # Cooling balance
            model.addConstr(cool["AC"][d][t] + cool["CC"][d][t] == dem["cool"][d][t])
        
    
    # Absorption chiller can only be supplied by Boiler and CHP
    for d in days:
        for t in time_steps:
            model.addConstr(heat["BOI"][d][t] + heat["CHP"][d][t] >= heat["AC"][d][t])    
        
    
            
        
    #%% SUM UP RESULTS
    model.addConstr(gas_total == sum(sum(sum(gas[device][d][t] for t in time_steps) * param["day_weights"][d] for d in days) for device in ["BOI", "CHP"]))
  
    model.addConstr(from_grid_total == sum(sum(power["from_grid"][d][t] for t in time_steps) * param["day_weights"][d] for d in days))
    model.addConstr(to_grid_total == sum(sum(power["to_grid"][d][t] for t in time_steps) * param["day_weights"][d] for d in days))

    model.addConstr(electricity_costs == sum(sum((power["from_grid"][d][t] * param["price_el"][d][t]) for t in time_steps) * param["day_weights"][d] for d in days))
    
    model.addConstr(revenue_feed_in["CHP"] == sum(sum((power["to_grid"][d][t] * param["revenue_feed_in"]["CHP"][d][t]) for t in time_steps) * param["day_weights"][d] for d in days))
    model.addConstr(revenue_feed_in["PV"] == 0)
    
    
    # total investment costs
    if param["switch_cost_functions"]:
        for device in ["BOI", "CHP", "CC", "AC"]:
            model.addConstr( inv[device] == sum(lin[device][i] * devs[device]["inv_i"][i] for i in range(len(devs[device]["cap_i"]))) )
        for device in ["SUB"]:
            model.addConstr(inv[device] == devs[device]["inv_var"] * cap[device])
    else:
        for device in all_devs:
            model.addConstr(inv[device] == devs[device]["inv_var"] * cap[device])        
        
    # Annual investment costs
    for device in all_devs:
        model.addConstr( c_inv[device] == inv[device] * devs[device]["ann_factor"] )
    
    # Operation and maintenance costs
    for device in all_devs:       
        model.addConstr( c_om[device] == devs[device]["cost_om"] * inv[device] )
    
    # Total annual costs
    for device in all_devs:
        model.addConstr( c_total[device] == c_inv[device] + c_om[device] )
        

    
    

    #%% OBJECTIVE FUNCTIONS
    # TOTAL ANNUALIZED COSTS
    model.addConstr(obj["tac"] == sum(c_total[dev] for dev in all_devs)                                           # annualized device investment costs   
                                  + param["c_network"]                                                            # annualized network costs           
                                  + gas_total * param["price_gas"] + grid_limit_gas * param["price_cap_gas"]      # gas costs
                                  + electricity_costs + grid_limit_el * param["price_cap_el"]                     # electricity costs
                                  - revenue_feed_in["CHP"]   	                                                  # revenue for grid feed-in
                                  , "sum_up_TAC")                                    
    
    # ANNUAL CO2 EMISSIONS: Implicit emissions by power supply from national grid is penalized, feed-in is ignored
    model.addConstr(obj["co2_gross"] == gas_total * param["gas_CO2_emission"] + (from_grid_total - to_grid_total) * param["grid_CO2_emission"], "sum_up_gross_CO2_emissions")

    
    
    #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    # Set model parameters and execute calculation
    
    print("Precalculation and model set up done in %f seconds." %(time.time() - start_time))
    
    # Set solver parameters
    model.Params.MIPGap     = param["MIPGap"]             # ---,  gap for branch-and-bound algorithm
    model.Params.method     = 2                           # ---, -1: default, 0: primal simplex, 1: dual simplex, 2: barrier, etc. (only affects root node)
    model.Params.Heuristics = 0                           # Percentage of time spent on heuristics (0 to 1)
    model.Params.MIPFocus   = 2                           # Can improve calculation time (values: 0 to 3)
    model.Params.Cuts       = 2                           # Cut aggressiveness (values: -1 to 3)
    model.Params.PrePasses  = 8                           # Number of passes performed by presolving (changing can improve presolving time) values: -1 to inf
    
    # Execute calculation
    start_time = time.time()

    model.optimize()

    print("Optimization done. (%f seconds.)" %(time.time() - start_time))
    
   
    #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    # Check and save results
    
    if not os.path.exists(dir_results):
        os.makedirs(dir_results)
    
    # Check if optimal solution was found
    if model.Status in (3,4) or model.SolCount == 0:  # "INFEASIBLE" or "INF_OR_UNBD"
        model.computeIIS()
        model.write(dir_results + "\\" + "model.ilp")
        print('Optimization result: No feasible solution found.')
    
    else:
        
        # Write Gurobi files
        model.write(dir_results + "\model.lp")
        model.write(dir_results + "\model.prm")
        model.write(dir_results + "\model.sol")


        # Print tac
        print("tac: " + str(obj[obj_fn].X))
        


        # Calculate mass flows for network optimization
        for n in nodes:
            nodes[n]["mass_flow"] = {}
            for demand in ["heat", "cool"]:
                nodes[n]["mass_flow"][demand] = nodes[n][demand] * 1000 / (param["c_f"] * abs((param["T_supply"][demand] - param["T_return"][demand])))     # kg/s




        # Store param and nodes as json
        
        # param
        for item in ["G_sol", "T_cold", "T_hot", "T_soil_deep", "day_matrix", "day_weights", "price_el", "sigma", "t_air", "t_soil", "dem_heat", "dem_cool"]:
            param[item] = param[item].tolist()
        for item in ["CHP", "PV"]:
            param["revenue_feed_in"][item] = param["revenue_feed_in"][item].tolist()                
        param["gas_buildings"] = [0]
        with open(dir_results + "\parameter.json", "w") as outfile:
            json.dump(param, outfile, indent=4, sort_keys=True)    
        
        # nodes
        for item in ["T_cooling_return", "T_cooling_supply", "T_heating_return", "T_heating_supply", "cool", "heat"]:
            for n in nodes:
                nodes[n][item] = nodes[n][item].tolist()
        for n in nodes:
            nodes[n]["mass_flow"]["heat"] = nodes[n]["mass_flow"]["heat"].tolist()
            nodes[n]["mass_flow"]["cool"] = nodes[n]["mass_flow"]["cool"].tolist()
        for item in ["power_dem", "res_heat_dem"]:
            for n in nodes:
                nodes[n][item] = [0]                
        with open(dir_results + "\data_nodes.json", "w") as outfile:
            json.dump(nodes, outfile, indent=4, sort_keys=True)         
        


#        # Run Post Processing
        if param["switch_post_processing"]:
            post.run(dir_results)
    
                
        
    
        # return nodes, param
        return nodes, param













