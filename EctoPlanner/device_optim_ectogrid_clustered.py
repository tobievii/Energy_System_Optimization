# -*- coding: utf-8 -*-
"""
Created on Thu Dec 20

@author: lkivi
"""

import numpy as np
import gurobipy as gp
import time
import os
import post_processing_clustered as post
import json  
        
        

#%%
def run_optim(nodes, param, devs, devs_dom, dir_results):
    
    days = range(param["n_clusters"])
    year = range(365)
    time_steps = range(24)
    
    t_air = param["t_air"]         # Air temperature °C           
    G_sol = param["G_sol"]         # Solar radiation W/m^2  
    t_soil = param["t_soil"]       # Soil temperature °C        

    # typeday assignment: sigma array contains corresponding type-day for each day of the year
    sigma = param["sigma"]    
    
    #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    start_time = time.time()

    # Create set for BU devices
    all_devs = ["BOI", "CHP", "AC", "CC", "TES", "CTES", "AIRC", "HP", "EH", "BAT", "PV"] 
        
    # Create set for building devices
    all_devs_dom = ["HP", "CC", "EH", "FRC", "AIRC", "BOI", "TES"]     
    
        
         
    #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    # Setting up the model
    
    # Create a new model
    model = gp.Model("Global_Optimization")
    
    #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    # Create new variables
    
    #%% BALANCING UNIT VARIABLES
    
    # Piece-wise linear function variables
    if param["switch_cost_functions"]:
        lin = {}
        for device in ["BOI", "CHP", "AC", "CC", "TES", "CTES", "HP"]:   
            lin[device] = {}
            for i in range(len(devs[device]["cap_i"])):
                lin[device][i] = model.addVar(vtype="C", name="lin_" + device + "_i" + str(i))
            
            
    # Device's capacity (i.e. nominal power)
    cap = {}
    for device in ["BOI", "CHP", "AC", "CC", "TES", "CTES", "AIRC", "HP", "EH", "BAT", "PV"]:
        cap[device] = model.addVar(vtype="C", name="nominal_capacity_" + str(device))
        
     # PV roof area
    area = {}
    for device in ["PV"]:
        area[device] = model.addVar(vtype = "C", name="roof_area_" + str(device))
    
#    # Storage volumes
#    vol = {}
#    for device in ["TES", "CTES"]:
#        vol[device] = model.addVar(vtype = "C", name="volume_" + str(device))
    
    
    # Gas flow to/from devices
    gas = {}
    for device in ["BOI", "CHP", "to_buildings"]:
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
                
    # feed-in
    feed_in = {}
    for device in ["CHP", "PV"]:
        feed_in[device] = {}
        for d in days:
            feed_in[device][d] = {}
            for t in time_steps:
                feed_in[device][d][t] = model.addVar(vtype="C", name="feed_in_" + device + "_d" + str(d) + "_t" + str(t))
                
    # thermal network losses
    loss = {}
    for dem in ["heat", "cool"]:
        loss[dem] = {}
        for d in days:
            loss[dem][d] = {}
            for t in time_steps:
                loss[dem][d][t] = model.addVar(vtype="C", lb=-gp.GRB.INFINITY, name="loss_" + dem + "_d" + str(d) + "_t" + str(t))
    
            
    # grid maximum transmission power
    grid_limit_el = model.addVar(vtype = "C", name="grid_limit_el")  
    grid_limit_gas = model.addVar(vtype = "C", name="grid_limit_gas")
    
    # total energy amounts taken from grid
    from_grid_total = model.addVar(vtype = "C", name="from_grid_total")
    # total power to grid
    to_grid_total = model.addVar(vtype = "C", name="to_grid_total")
    # Gas taken from grid
    gas_total = model.addVar(vtype = "C", name="gas_total")
    # total revenue for feed-in
    revenue_feed_in = {}
    for device in ["CHP", "PV"]:
        revenue_feed_in[device] = model.addVar(vtype="C", name="revenue_feed_in_"+str(device))
    # Electricity costs
    electricity_costs = model.addVar(vtype = "C", name="electricity_costs")
    
    

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
              
        
    # Investment costs
    inv = {}
    c_inv = {}
    c_om = {}
    c_total = {}    
    for device in all_devs:
        inv[device] = model.addVar(vtype = "C", name = "inv_costs_" + device)
    for device in all_devs:
        c_inv[device] = model.addVar(vtype = "C", name = "annual_inv_costs_" + device)
    for device in all_devs:
        c_om[device] = model.addVar(vtype = "C", name = "om_costs_" + device) 
    for device in all_devs:
        c_total[device] = model.addVar(vtype = "C", name = "total_annual_costs_" + device)

        
    
    
    
    #%% BUILDING VARIABLES
    
    # Device's capacity (i.e. nominal power)
    cap_dom = {}
    for device in ["HP", "CC", "EH", "FRC", "AIRC", "BOI", "TES"]:
        cap_dom[device] = {}
        for n in nodes:
            cap_dom[device][n] = model.addVar(vtype="C", name="nominal_capacity_" + str(device) + "_n" + str(n))
            
#    # TES volumes
#    vol_dom = {}
#    for device in ["TES"]:
#        vol_dom[device] = {}
#        for n in nodes:
#            vol_dom[device][n] = model.addVar(vtype = "C", name= "volume_" + str(device) + "_n" + str(n))
    
    # Eletrical power to/from devices
    power_dom = {}
    for device in ["HP", "CC", "EH"]:
        power_dom[device] = {}
        for n in nodes:
            power_dom[device][n] = {}
            for d in days:
                power_dom[device][n][d] = {}
                for t in time_steps:
                    power_dom[device][n][d][t] = model.addVar(vtype="C", name="power_" + device + "_n" + str(n) + "_d" + str(d) + "_t" + str(t))

     # Gas to devices
    gas_dom = {}
    for device in ["BOI"]:
        gas_dom[device] = {}
        for n in nodes:
            gas_dom[device][n] = {}
            for d in days:
                gas_dom[device][n][d] = {}
                for t in time_steps:
                    gas_dom[device][n][d][t] = model.addVar(vtype="C", name="gas_" + device + "_n" + str(n) + "_d" + str(d) + "_t" + str(t))
       
    # Heat to/from devices
    heat_dom = {}
    for device in ["HP", "EH", "BOI"]:
       heat_dom[device] = {}
       for n in nodes:
           heat_dom[device][n] = {}  
           for d in days:
               heat_dom[device][n][d] = {}
               for t in time_steps:
                   heat_dom[device][n][d][t] = model.addVar(vtype="C", name="heat_"  + device + "_n" + str(n) + "_d" + str(d) + "_t" + str(t))
    
    # Cooling power to/from devices
    cool_dom = {}
    for device in ["CC", "FRC", "AIRC"]:
        cool_dom[device] = {}
        for n in nodes:
            cool_dom[device][n] = {}
            for d in days:
                cool_dom[device][n][d] = {}
                for t in time_steps:
                    cool_dom[device][n][d][t] = model.addVar(vtype="C", name="cool_" + device + "_n" + str(n) + "_d" + str(d) + "_t" + str(t))
      
          
    # Storage variables 

    # initial soc of every type-day
    soc_dom_init = {}
    for device in ["TES"]: 
        soc_dom_init[device] = {}
        for n in nodes:
            soc_dom_init[device][n] = model.addVar(vtype="C", name="soc_initial_" + device + "_n" + str(n))
    
    ch_dom = {}                 # Energy flow to charge storage device
    dch_dom = {}                # Energy flow to discharge storage device
    soc_dom = {}                # State of charge
    for device in ["TES"]:
        ch_dom[device] = {}
        dch_dom[device] = {}
        soc_dom[device] = {}
        for n in nodes:
            ch_dom[device][n] = {}
            dch_dom[device][n] = {}
            soc_dom[device][n] = {} 
            for d in days:
                ch_dom[device][n][d] = {}
                for t in time_steps:
                    ch_dom[device][n][d][t] = model.addVar(vtype="C", name="ch_" + device + "_n" + str(n) + "_d" + str(d) + "_t" + str(t))
            for d in days:
                dch_dom[device][n][d] = {}
                for t in time_steps:
                    dch_dom[device][n][d][t] = model.addVar(vtype="C", name="dch_" + device + "_n" + str(n) + "_d" + str(d) + "_t" + str(t))
            for d in days:
                soc_dom[device][n][d] = {} 
                for t in time_steps:
                    soc_dom[device][n][d][t] = model.addVar(vtype="C", name="soc_" + device + "_n" + str(n) + "_d" + str(d) + "_t" + str(t))
                soc_dom[device][n][d][len(time_steps)] = model.addVar(vtype="C", name="soc_" + device + "_n" + str(n) + "_d" + str(d) + "_t" + str(len(time_steps)))
                
   
#    # mass flows through free cooler / aircooler / bypass as share of total cooling cycle mass flow
#    x = {}
#    for device in ["FRC", "AIRC", "BYP"]:
#        x[device] = {}
#        for n in nodes:
#            x[device][n] = {}
#            for d in days:
#                x[device][n][d] = {}
#                for t in time_steps:
#                    x[device][n][d][t] = model.addVar(vtype = "C", name="x_" + device + "_" + str(n) + "_d" + str(d) + "_t" + str(t))
#
#
#    # cooling power of aircooler and freecooler are divided into direct and recycled proportion
#    for device in ["FRC"]:
#        for prop in ["dir", "rec"]:
#            cool_dom[device][prop] = {}
#            for n in nodes:
#                cool_dom[device][prop][n] = {}
#                for d in days:
#                    cool_dom[device][prop][n][d] = {}
#                    for t in time_steps:
#                        cool_dom[device][prop][n][d][t] = model.addVar(vtype="C", name="cool_" + device + "_" + prop + "_n" + str(n) + "_d" + str(d) + "_t" + str(t))

    # temperature between air cooler and free cooler
    T_inter = {}
    for n in nodes:
        T_inter[n] = {}
        for d in days:
            T_inter[n][d] = {}
            for t in time_steps:
                T_inter[n][d][t] = model.addVar(vtype="C", name="t_out_airc_n"+str(n)+"_d"+str(d)+"_t"+str(t))
    
    
    # Energy flows at peak time
    peak_dom = {}
    for device in ["HP", "EH", "BOI", "CC", "FRC"]:
        peak_dom[device] = {}
        for n in nodes:
            peak_dom[device][n] = model.addVar(vtype="C", name="peak_load_"+device+"_n"+str(n))

                    
    
    # Node residual loads
    res_el = {}
    res_thermal= {}
    for n in nodes:
        res_el[n] = {}
        for d in days:
            res_el[n][d] = {}
            for t in time_steps:
                res_el[n][d][t] = model.addVar(vtype="C", name="residual_power_n" + str(n) + "_d" + str(d) + "_t" + str(t))
        res_thermal[n] = {}
        for d in days:
            res_thermal[n][d] = {}
            for t in time_steps:
                res_thermal[n][d][t] = model.addVar(vtype="C", lb=-gp.GRB.INFINITY, name="residual_thermal_n" + str(n) + "_d" + str(d) + "_t" + str(t))  

    
    # Total residual network load
    residual = {}  
    residual["power"] = {}
    residual["heat"] = {}
    residual["cool"] = {}
    residual["thermal"] = {}
    residual["thermal_abs"] = {}
    for d in days:
        residual["power"][d] = {}
        for t in time_steps:        
            residual["power"][d][t] = model.addVar(vtype = "C", name="residual_power_d" + str(d) + "_t" + str(t))
    for d in days:
        residual["heat"][d] = {}
        for t in time_steps:
            residual["heat"][d][t] = model.addVar(vtype = "C", name="residual_heating_d" + str(d) + "_t" + str(t))   
    for d in days:
        residual["cool"][d] = {}
        for t in time_steps:
            residual["cool"][d][t] = model.addVar(vtype = "C", name="residual_cooling_d" + str(d) + "_t" + str(t))
    for d in days:
        residual["thermal"][d] = {}
        for t in time_steps:
            residual["thermal"][d][t] = model.addVar(lb = -gp.GRB.INFINITY, vtype = "C", name="residual_thermal_d" + str(d) + "_t" + str(t))        
    for d in days:
        residual["thermal_abs"][d] = {}
        for t in time_steps:
            residual["thermal_abs"][d][t] = model.addVar(vtype = "C", name="residual_thermal_abs_d" + str(d) + "_t" + str(t))
        
        
    # Investment costs
    inv_dom = {}
    c_inv_dom = {}
    c_om_dom = {}
    c_total_dom = {}
    for device in all_devs_dom:
        inv_dom[device] = {}
        c_inv_dom[device] = {}
        c_om_dom[device] = {} 
        c_total_dom[device] = {}
        for n in nodes:
            inv_dom[device][n] = model.addVar(vtype="C", name="inv_costs_" + device + "_n" + str(n))
        for n in nodes:
            c_inv_dom[device][n] = model.addVar(vtype="C", name="annual_inv_costs_" + device + "_n" + str(n))
        for n in nodes:
            c_om_dom[device][n]  = model.addVar(vtype="C", name="om_costs_" + device + "_n" + str(n))             
        for n in nodes:
            c_total_dom[device][n]  = model.addVar(vtype="C", name="total_annual_costs_" + device + "_n" + str(n))    
            
    
    # Total annualized costs
    tac_total = model.addVar(vtype = "c", lb=-gp.GRB.INFINITY, name = "total_annualized_costs") 

    # Total gross CO2 emissions
    co2_total = model.addVar(vtype = "c", lb=-gp.GRB.INFINITY, name = "total_CO2")         
                
    # Objective function
    obj = model.addVar(vtype="C", lb=-gp.GRB.INFINITY, name="obj")    
        


#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    # Define objective function
    model.update()
    model.setObjective(obj, gp.GRB.MINIMIZE)
    
    
 
    # Add constraints 
    
    
    #%% BUILDING CONSTRAINTS
    
    #%% Capacity constraints
            
    # Thermal storage
    for n in nodes:
        for device in ["TES"]:
            model.addConstr(cap_dom[device][n] <= devs_dom[device]["max_cap"][n])
            model.addConstr(cap_dom[device][n] >= devs_dom[device]["min_cap"][n])
#            # Relation between capacity and volume
#            model.addConstr(cap_dom[device][n] == vol_dom[device][n] * param["rho_f"] *  param["c_f"] * (devs_dom[device]["T_max"] - devs_dom[device]["T_min"]) / (1000 * 3600))
            
            
    # Assure that real building peak loads are met
    for n in nodes:
        # heating
        model.addConstr(peak_dom["EH"][n] + peak_dom["HP"][n] + peak_dom["BOI"][n] == nodes[n]["peak"]["heat"])        
        # cooling
        model.addConstr(peak_dom["CC"][n] + peak_dom["FRC"][n] == nodes[n]["peak"]["cool"])
        
        # load constraints at peak time
        # peak loads <= device capacities
        for device in ["EH", "HP", "BOI", "CC", "FRC"]:
            model.addConstr(peak_dom[device][n] <= cap_dom[device][n])
        for device in ["FRC"]:
            model.addConstr(peak_dom[device][n] <= nodes[n]["peak"]["FRC_max"] * nodes[n]["peak"]["cool"])

        
        
    
    #%% LOAD CONSTRAINTS
    
    for n in nodes:
        for device in ["TES"]:
            for d in days:
                for t in time_steps:    
                        model.addConstr(soc_dom[device][n][d][t] <= cap_dom[device][n])
#            model.addConstr(soc_dom_init[device][n] <= cap_dom[device][n])  
    
    for n in nodes:
        for d in days:
            for t in time_steps:             
                
                for device in ["HP", "EH", "BOI"]:
                    model.addConstr(heat_dom[device][n][d][t] <= cap_dom[device][n])
                
                for device in ["CC", "FRC", "AIRC"]:
                    model.addConstr(cool_dom[device][n][d][t] <= cap_dom[device][n])
    
    
    #%% INPUT / OUTPUT CONSTRAINTS
    
    for n in nodes:
        for d in days:
            for t in time_steps:
        
                # Electric heater
                model.addConstr(heat_dom["EH"][n][d][t] == power_dom["EH"][n][d][t] * devs_dom["EH"]["eta_th"])
                
                # Compression chiller
                model.addConstr(cool_dom["CC"][n][d][t] == power_dom["CC"][n][d][t] * devs_dom["CC"]["COP"][n][d][t])  
        
                # Heat Pump
                model.addConstr(heat_dom["HP"][n][d][t] == power_dom["HP"][n][d][t] * devs_dom["HP"]["COP"][n][d][t])
                
                # Boiler
                model.addConstr(heat_dom["BOI"][n][d][t] == gas_dom["BOI"][n][d][t] * devs_dom["BOI"]["eta_th"])
                
           
                
        

    #%% ENERGY BALANCES
            
    for n in nodes:
        for d in days:
            for t in time_steps:
                
                # Heat balance
                model.addConstr(heat_dom["EH"][n][d][t] + heat_dom["HP"][n][d][t] + heat_dom["BOI"][n][d][t] + dch_dom["TES"][n][d][t]  == nodes[n]["heat"][d][t] + ch_dom["TES"][n][d][t] )  
        
                # Cooling balance
                model.addConstr(cool_dom["CC"][n][d][t] + cool_dom["FRC"][n][d][t] + cool_dom["AIRC"][n][d][t] == nodes[n]["cool"][d][t] ) 
                
                # Electricity demands
                model.addConstr(res_el[n][d][t] == power_dom["EH"][n][d][t] + power_dom["HP"][n][d][t] + power_dom["CC"][n][d][t])
                                
                # Thermal storage can only be supplied by Electric heater and boiler
                model.addConstr(heat_dom["EH"][n][d][t] + heat_dom["BOI"][n][d][t] >= ch_dom["TES"][n][d][t])
            
    
    #%% BUILDING THERMAL STORAGES

    for n in nodes:
    
        for device in ["TES"]:
            
            for d in days:
                            
                # Initial state of charge
                model.addConstr(soc_dom[device][n][d][0] == soc_dom_init[device][n])
#                model.addConstr(soc_dom_init[device][n] == 0)
                
                # Cyclic condition
                model.addConstr(soc_dom[device][n][d][0] == soc_dom[device][n][d][len(time_steps)-1] * (1-devs_dom[device]["sto_loss"])
                        + (ch_dom[device][n][d][23] * devs_dom[device]["eta_ch"] 
                        - dch_dom[device][n][d][23] / devs_dom[device]["eta_dch"]))
            
                for t in np.arange(1,len(time_steps)):
                    # Energy balance: soc(t) = soc(t-1) + charge - discharge
                    model.addConstr(soc_dom[device][n][d][t] == soc_dom[device][n][d][t-1] * (1-devs_dom[device]["sto_loss"])
                        + (ch_dom[device][n][d][t-1] * devs_dom[device]["eta_ch"] 
                        - dch_dom[device][n][d][t-1] / devs_dom[device]["eta_dch"]))
            

    #%% FREE COOLING AND AIR COOLING RESTRICTIONS
    
    for n in nodes:
        
        for d in days:
            
            for t in time_steps:                

                 # Reihenschaltung von Luftkühler und Freikühler
                 
                 # air cooling
                 if t_air[d][t] + devs_dom["AIRC"]["dT_min"] > nodes[n]["T_cooling_return"][d][t]:
                     model.addConstr(cool_dom["AIRC"][n][d][t] == 0)
                 else:
                     model.addConstr(cool_dom["AIRC"][n][d][t] <= nodes[n]["cool"][d][t] * (nodes[n]["T_cooling_return"][d][t] - (t_air[d][t] + devs_dom["AIRC"]["dT_min"]))/(nodes[n]["T_cooling_return"][d][t] - nodes[n]["T_cooling_supply"][d][t]))                        
       
                 # free cooler
                 if param["T_hot"][d][t] + devs_dom["FRC"]["dT_min"] > nodes[n]["T_cooling_return"][d][t]:
                     model.addConstr(cool_dom["FRC"][n][d][t] == 0)
                 else:
                     # Priorize free cooler by limitation of air cooler
                     model.addConstr(cool_dom["AIRC"][n][d][t] <= nodes[n]["cool"][d][t] * (nodes[n]["T_cooling_return"][d][t] - (param["T_hot"][d][t] + devs_dom["FRC"]["dT_min"]))/(nodes[n]["T_cooling_return"][d][t] - nodes[n]["T_cooling_supply"][d][t]))
                     # sum of free cooler and air cooler
                     model.addConstr(cool_dom["FRC"][n][d][t] <=  nodes[n]["cool"][d][t] * (nodes[n]["T_cooling_return"][d][t] - (param["T_cold"][d][t] + devs_dom["FRC"]["dT_min"]))/(nodes[n]["T_cooling_return"][d][t] - nodes[n]["T_cooling_supply"][d][t]) - cool_dom["AIRC"][n][d][t])
                
                
    #%% RESIDUAL THERMAL LOADS
    
    for n in nodes:
        for d in days:            
            for t in time_steps:
    
                if not param["switch_stand_alone"]:                
                    model.addConstr(res_thermal[n][d][t] == (heat_dom["HP"][n][d][t] - power_dom["HP"][n][d][t]) - (cool_dom["CC"][n][d][t] + power_dom["CC"][n][d][t] + cool_dom["FRC"][n][d][t] ))
                else:
                    # Stand-Alone solution: no network available
                    model.addConstr(res_thermal[n][d][t] == 0)
                    
    
    #%% DEVICE RESTRICTIONS

    if param["use_hp_in_bldgs"] == 0:       
        for n in nodes:  
            model.addConstr(cap_dom["HP"][n] == 0 )

    if param["use_cc_in_bldgs"] == 0:       
        for n in nodes:  
            model.addConstr(cap_dom["CC"][n] == 0 )
    
    if param["use_eh_in_bldgs"] == 0:       
        for n in nodes:  
            model.addConstr(cap_dom["EH"][n] == 0 )
            
    if param["use_boi_in_bldgs"] == 0:       
        for n in nodes:  
            model.addConstr(cap_dom["BOI"][n] == 0 )
            
    if param["use_frc_in_bldgs"] == 0:       
        for n in nodes:  
            model.addConstr(cap_dom["FRC"][n] == 0 )

    if param["use_airc_in_bldgs"] == 0:       
        for n in nodes:  
            model.addConstr(cap_dom["AIRC"][n] == 0 )
            
    if param["use_tes_in_bldgs"] == 0:       
        for n in nodes:  
            model.addConstr(cap_dom["TES"][n] == 0 )
            for d in days:
                for t in time_steps:
                    model.addConstr( ch_dom["TES"][n][d][t] == 0)
                    model.addConstr( dch_dom["TES"][n][d][t] == 0)
                    model.addConstr( soc_dom["TES"][n][d][t] == 0)
            
            
            
            
    #%% SUM UP

    # Investment costs
 
    for device in all_devs_dom:

        for n in nodes:
            
            # investment costs
            model.addConstr( inv_dom[device][n] == devs_dom[device]["inv_var"] * cap_dom[device][n] )
        
            # annualized investment
            model.addConstr( c_inv_dom[device][n] == devs_dom[device]["ann_factor"] * inv_dom[device][n] )
    
            # Operation and maintenance costs 
            model.addConstr( c_om_dom[device][n] == devs_dom[device]["cost_om"] * inv_dom[device][n] )
            
            # Tac for building device (kEUR)
            model.addConstr( c_total_dom[device][n] == (c_inv_dom[device][n] + c_om_dom[device][n]) / 1000)
            
    
    
    # Residual loads
    for d in days:    
        for t in time_steps:
            model.addConstr(residual["power"][d][t] == sum(res_el[n][d][t] for n in nodes) / 1000)
    for d in days:    
        for t in time_steps:
            model.addConstr(residual["thermal"][d][t] == sum(res_thermal[n][d][t] for n in nodes) / 1000 + loss["heat"][d][t] - loss["cool"][d][t])
            
#    # thermal network losses
    for d in days:
        for t in time_steps:
            model.addConstr(loss["heat"][d][t] == param["kA"] * (param["T_hot"][d][t] - t_soil[d][t]) / 1000)
            model.addConstr(loss["cool"][d][t] == param["kA"] * (t_soil[d][t] - param["T_cold"][d][t]) / 1000)            
#            model.addConstr(loss["heat"][d][t] == 0)
#            model.addConstr(loss["cool"][d][t] == 0)     

    # if two heating and cooling balances are considered: seperate residual thermal load into heating and cooling load
    if not param["switch_single_balance"]:        
        for d in days:
            for t in time_steps: 
                                              
                model.addGenConstrAbs(residual["thermal_abs"][d][t], residual["thermal"][d][t])
                
                model.addConstr(residual["heat"][d][t] == (residual["thermal_abs"][d][t] + residual["thermal"][d][t]) / 2 )
                model.addConstr(residual["cool"][d][t] == (residual["thermal_abs"][d][t] - residual["thermal"][d][t]) / 2 )    
                
    # Gas supply for building boilers
    for d in days:
        for t in time_steps:
            model.addConstr(gas["to_buildings"][d][t] == sum(gas_dom["BOI"][n][d][t] for n in nodes) / 1000)

        
        
        
    #%% BALANCING UNIT CONSTRAINTS
        
   
    #%% CAPACITY CONSTRAINTS
    
    # PV
    for device in ["PV"]:            
        model.addConstr(area[device] <= devs[device]["max_area"])
        # conversion from area to peak power; cap["PV"] is only needed for investment costs
        model.addConstr(cap[device] == area[device] * devs[device]["G_stc"]/1e6 * devs[device]["eta_el_stc"])    
    
    # Storages    
    for device in ["TES", "CTES", "BAT"]:
        model.addConstr(cap[device] <= devs[device]["max_cap"])
        model.addConstr(cap[device] >= devs[device]["min_cap"])
        
#    for device in ["TES", "CTES"]:
#        # Relation between volume and capacity
#        model.addConstr(cap[device] == vol[device] * param["rho_f"] *  param["c_f"] * (devs[device]["T_max"] - devs[device]["T_min"]) / (1e6 * 3600))
    

    if param["switch_cost_functions"]:    
        # calculate capacities from piece-wise linear function variables    
        for device in ["BOI", "CHP", "AC", "CC", "TES", "CTES", "HP"]:
        
            model.addConstr(cap[device] == sum(lin[device][i] * devs[device]["cap_i"][i] for i in range(len(devs[device]["cap_i"]))))
            # lin: Special Ordered Sets of type 2 (SOS2 or S2): an ordered set of non-negative variables, of which at most two can be non-zero, and if 
            # two are non-zero these must be consecutive in their ordering. 
            model.addSOS(gp.GRB.SOS_TYPE2, [lin[device][i] for i in range(len(devs[device]["cap_i"]))])
            
            # Sum of linear function variables should be 1
            model.addConstr(1 == sum(lin[device][i] for i in range(len(devs[device]["cap_i"]))))
          

    #%% LOAD CONSTRAINTS
    
    # Maximum and minimum storage soc
    for device in ["TES", "CTES", "BAT"]:
        for day in year:
            for t in time_steps:    
                model.addConstr(soc[device][day][t] <= devs[device]["max_soc"] * cap[device])
                model.addConstr(soc[device][day][t] >= devs[device]["min_soc"] * cap[device])

    # Maximum storage charge and discharge
    for device in ["TES", "CTES", "BAT"]:
        for d in days:
            for t in time_steps:   
                model.addConstr(ch[device][d][t] <= devs[device]["max_ch"] * cap[device])
                model.addConstr(dch[device][d][t] <= devs[device]["max_dch"] * cap[device])
                
   # load <= capacity
    for t in time_steps:
        for d in days:
            for device in ["BOI", "HP", "EH"]:
                model.addConstr(heat[device][d][t] <= cap[device])
                
            for device in ["CHP"]:
                model.addConstr(power[device][d][t] <= cap[device])
            
            for device in ["CC", "AC", "AIRC"]:
                model.addConstr(cool[device][d][t] <= cap[device])
    
            # limitation of power from and to grid   
            model.addConstr(sum(gas[device][d][t] for device in ["BOI", "CHP", "to_buildings"]) <= grid_limit_gas)       
            for device in ["from_grid", "to_grid"]:
                model.addConstr(power[device][d][t] <= grid_limit_el)
            
    # Air cooler temperature constraints
    for d in days:
        for t in time_steps:
            if t_air[d][t] + devs["AIRC"]["dT_min"] > param["T_hot"][d][t]:
                model.addConstr(cool["AIRC"][d][t] == 0)
            else:
                if param["switch_single_balance"]:
                    model.addConstr( cool["AIRC"][d][t] <= ( -residual["thermal"][d][t] + heat["BOI"][d][t] + heat["CHP"][d][t] + heat["HP"][d][t] + heat["EH"][d][t] + dch["TES"][d][t] - heat["AC"][d][t] - ch["TES"][d][t]) * (param["T_hot"][d][t] - (t_air[d][t] + devs["AIRC"]["dT_min"]))/ (param["T_hot"][d][t] - param["T_cold"][d][t] ))
                else:
                    model.addConstr( cool["AIRC"][d][t] <=  residual["cool"][d][t] * (param["T_hot"][d][t] - (t_air[d][t] + devs["AIRC"]["dT_min"]))/ (param["T_hot"][d][t] - param["T_cold"][d][t] ))
            
    #%% INPUT / OUTPUT CONSTRAINTS
    for t in time_steps:
        
        for d in days:
            
            # Boiler
            model.addConstr(gas["BOI"][d][t] == heat["BOI"][d][t] / devs["BOI"]["eta_th"])
            
            # Heat pump
            model.addConstr(heat["HP"][d][t] == power["HP"][d][t] * devs["HP"]["COP"][d][t])
            
            # Combined heat and power
            model.addConstr(power["CHP"][d][t] == heat["CHP"][d][t] / devs["CHP"]["eta_th"] * devs["CHP"]["eta_el"])
            model.addConstr(gas["CHP"][d][t] == heat["CHP"][d][t] / devs["CHP"]["eta_th"])
            
            # Electric heater
            model.addConstr(heat["EH"][d][t] == power["EH"][d][t] * devs["EH"]["eta_th"])
            
            # Compression chiller
            model.addConstr(cool["CC"][d][t] == power["CC"][d][t] * devs["CC"]["COP"][d][t])  
    
            # Absorption chiller
            model.addConstr(cool["AC"][d][t] == heat["AC"][d][t] * devs["AC"]["eta_th"])

            # PV
            model.addConstr(power["PV"][d][t] <= G_sol[d][t]/1e6 * devs["PV"]["eta_el"][d][t] * area["PV"])         
    
     #%% STORAGE DEVICES
    
    
    for device in ["TES", "CTES", "BAT"]:
        
        for day in year:        
            
            for t in np.arange(1, len(time_steps)):
                
                # Energy balance: soc(t) = soc(t-1) + charge - discharge
                model.addConstr(soc[device][day][t] == soc[device][day][t-1] * (1-devs[device]["sto_loss"])
                    + ch[device][sigma[day]][t] * devs[device]["eta_ch"] 
                    - dch[device][sigma[day]][t] / devs[device]["eta_dch"])
            
            # Calculate initial state of charge according to last soc of previous day
            if day > 0:
                model.addConstr(soc[device][day][0] == soc[device][day-1][len(time_steps)-1] * (1-devs[device]["sto_loss"])                      
                    + ch[device][sigma[day]][0] * devs[device]["eta_ch"] 
                    - dch[device][sigma[day]][0] / devs[device]["eta_dch"])
                
        # Cyclic year condition
        model.addConstr(soc[device][0][0] ==  soc[device][len(year)-1][len(time_steps)-1] * (1-devs[device]["sto_loss"]) 
                    + ch[device][sigma[0]][0] * devs[device]["eta_ch"] 
                    - dch[device][sigma[0]][0] / devs[device]["eta_dch"])
        
   
    
    #%% ENERGY BALANCES
    for d in days:
        
        for t in time_steps:
 
            if param["switch_single_balance"]:
                # Thermal balance (combined heating and cooling balance)
                model.addConstr(heat["BOI"][d][t] + heat["CHP"][d][t] + heat["HP"][d][t] + heat["EH"][d][t] + dch["TES"][d][t] - cool["AC"][d][t] - cool["CC"][d][t] - cool["AIRC"][d][t] - dch["CTES"][d][t] == residual["thermal"][d][t]  + heat["AC"][d][t] + ch["TES"][d][t] - ch["CTES"][d][t])
            
            else: # Seperated heating and cooling balance
            
                # Heat balance
                model.addConstr(heat["BOI"][d][t] + heat["CHP"][d][t] + heat["HP"][d][t] + heat["EH"][d][t] + dch["TES"][d][t] == residual["heat"][d][t] + heat["AC"][d][t] + ch["TES"][d][t] )
    
                # Cooling balance
                model.addConstr(cool["AC"][d][t] + cool["CC"][d][t] + cool["AIRC"][d][t] + dch["CTES"][d][t] == residual["cool"][d][t] + ch["CTES"][d][t] ) 
                
                
            
            # Electricity balance
            model.addConstr(power["CHP"][d][t] + power["PV"][d][t] + power["from_grid"][d][t] + dch["BAT"][d][t] == residual["power"][d][t] + power["to_grid"][d][t] + power["CC"][d][t] + power["HP"][d][t] + power["EH"][d][t] + ch["BAT"][d][t])
            
            # Absorption chiller and heat storage can only be supplied by Boiler, CHP and Electic Heater
            model.addConstr(heat["BOI"][d][t] + heat["CHP"][d][t] + heat["EH"][d][t] >= heat["AC"][d][t] + ch["TES"][d][t])
            
            
            # Cold thermal storage can only be suppled by compression chiller and absorption chiller
            model.addConstr(cool["CC"][d][t] + cool["AC"][d][t] >= ch["CTES"][d][t])    
        
        

    
    
    
    
    #%% GRID FEED-IN
    
    for d in days:
        
        for t in time_steps:
           
            # Allocate grid feed-in to CHP and PV
            model.addConstr( power["to_grid"][d][t] == feed_in["CHP"][d][t] + feed_in["PV"][d][t] )           

            model.addConstr( feed_in["CHP"][d][t] <= power["CHP"][d][t]  + dch["BAT"][d][t])
            model.addConstr( feed_in["PV"][d][t] <= power["PV"][d][t])
             

        
        
    #%% DEVICE RESTRICTIONS
    
    if not param["feasible_TES"]:
        model.addConstr(cap["TES"] == 0)
        for d in days:
            for t in time_steps:
                model.addConstr(ch["TES"][d][t] == 0)
                model.addConstr(dch["TES"][d][t] == 0)         

    if not param["feasible_CTES"]:
        model.addConstr(cap["CTES"] == 0)
        for d in days:
            for t in time_steps:
                model.addConstr(ch["CTES"][d][t] == 0)
                model.addConstr(dch["CTES"][d][t] == 0)
                
    if not param["feasible_BAT"]:
        model.addConstr(cap["BAT"] == 0)
        for d in days:
            for t in time_steps:
                model.addConstr(ch["BAT"][d][t] == 0)
                model.addConstr(dch["BAT"][d][t] == 0)   
        
    if not param["feasible_AIRC"]: 
        model.addConstr(cap["AIRC"] == 0)
    
    if not param["feasible_BOI"]: 
        model.addConstr(cap["BOI"] == 0)   
        
    if not param["feasible_CHP"]: 
        model.addConstr(cap["CHP"] == 0) 

    if not param["feasible_AC"]: 
        model.addConstr(cap["AC"] == 0)

    if not param["feasible_CC"]: 
        model.addConstr(cap["CC"] == 0) 

    if not param["feasible_HP"]: 
        model.addConstr(cap["HP"] == 0)  

    if not param["feasible_EH"]: 
        model.addConstr(cap["EH"] == 0)  
        
    if not param["feasible_PV"]: 
        model.addConstr(cap["PV"] == 0)         
        
        
    #%% STAND-ALONE SCNENARIO
    
    if param["switch_stand_alone"]:
        
        # deactivate all BU devices
        for dev in all_devs:
            model.addConstr( cap[dev] == 0 )
        for dev in ["TES", "CTES"]:
            for d in days:
                for t in time_steps:
                    model.addConstr( ch[dev][d][t] == 0 )
                    model.addConstr( dch[dev][d][t] == 0 )
                    
        # deactivate BOI and FRC in buildings
        for dev in ["BOI", "FRC"]:
            for n in nodes:
                model.addConstr( cap_dom[dev][n] == 0)
        for dev in ["TES"]:
            for n in nodes:
                for d in days:
                    for t in time_steps:
                        model.addConstr( ch_dom["TES"][n][d][t] == 0 )
                        model.addConstr( dch_dom["TES"][n][d][t] == 0 )
                        
        

    #%% SUM UP RESULTS
    
    model.addConstr(gas_total == sum(sum(sum(gas[device][d][t] for t in time_steps) * param["day_weights"][d] for d in days) for device in ["BOI", "CHP", "to_buildings"]))
  
    model.addConstr(from_grid_total == sum(sum(power["from_grid"][d][t] for t in time_steps) * param["day_weights"][d] for d in days))
    model.addConstr(to_grid_total == sum(sum(power["to_grid"][d][t] for t in time_steps) * param["day_weights"][d] for d in days))
    
    model.addConstr(electricity_costs == sum(sum((power["from_grid"][d][t] * param["price_el"][d][t] * param["day_weights"][d]) for t in time_steps) for d in days))
    
    for device in ["PV", "CHP"]:
        model.addConstr(revenue_feed_in[device] == sum(sum((feed_in[device][d][t] * param["revenue_feed_in"][device][d][t]) for t in time_steps) * param["day_weights"][d] for d in days))

    
    if param["switch_cost_functions"]:
        # Investment costs
        for device in ["BOI", "CHP", "AC", "CC", "TES", "CTES", "HP"]:
            model.addConstr( inv[device] == sum(lin[device][i] * devs[device]["inv_i"][i] for i in range(len(devs[device]["cap_i"]))) )
        for device in ["EH", "AIRC", "BAT", "PV"]:
            model.addConstr(inv[device] == devs[device]["inv_var"] * cap[device])            
    else:
        for device in all_devs:
            model.addConstr(inv[device] == devs[device]["inv_var"] * cap[device])
        
    # annualized investment
    for device in all_devs:
        model.addConstr( c_inv[device] == inv[device] * devs[device]["ann_factor"] )

    # Operation and maintenance costs
    for device in all_devs: 
        model.addConstr( c_om[device] == devs[device]["cost_om"] * inv[device] )
        
    # Annualized costs for device
    for device in all_devs:
        model.addConstr( c_total[device] == c_inv[device] + c_om[device])
    
    
            

    #%% OBJECTIVE
    
    
    model.addConstr(tac_total ==      sum(c_total[dev] for dev in all_devs)                                              # annual investment costs + o&m costs for BU devices
                                    + sum(sum(c_total_dom[dev][n] for n in nodes) for dev in all_devs_dom)                # annual investment costs + o&m costs for building devices
                                    + param["c_network"]
                                    + gas_total * param["price_gas"] + grid_limit_gas * param["price_cap_gas"]            # gas costs
                                    + electricity_costs + grid_limit_el * param["price_cap_el"]                           # electricity purchase costs + capacity price for grid usage
                                    - sum(revenue_feed_in[dev] for dev in ["CHP", "PV"])                                  # feed-in revenue
                                    , "sum_up_TAC")
    
    model.addConstr(co2_total == gas_total * param["gas_CO2_emission"] + (from_grid_total - to_grid_total) * param["grid_CO2_emission"])
    
    
    model.addConstr(obj == tac_total)
                                    
        
            
        

#%%
 # Set model parameters and execute calculation
    
    print("Precalculation and model set up done in %f seconds." %(time.time() - start_time))
    
    # Set solver parameters
    model.Params.MIPGap     = param["MIPGap"]           # ---,         gap for branch-and-bound algorithm
    model.Params.method     = 2                         # ---,         -1: default, 0: primal simplex, 1: dual simplex, 2: barrier, etc.
    model.Params.Heuristics = 0
    model.Params.MIPFocus   = 2
    model.Params.Cuts       = 3
    model.Params.PrePasses  = 8
#    model.Params.Crossover  = 0
#    model.Params.Presolve = 0
    
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
        model.write(dir_results + "\model.lp")
        model.computeIIS()
        model.write(dir_results + "\\" + "model.ilp")
        print('Optimization result: No feasible solution found.')

    
    else:
    

            
        # Write Gurobi files
        model.write(dir_results + "\model.lp")
        model.write(dir_results + "\model.prm")
        model.write(dir_results + "\model.sol")
        
        # Save device capacities in nodes 
        for n in nodes:
            nodes[n]["hp_capacity"] = cap_dom["HP"][n].X
            nodes[n]["cc_capacity"] = cap_dom["CC"][n].X
            nodes[n]["eh_capacity"] = cap_dom["EH"][n].X
            nodes[n]["boi_capacity"] = cap_dom["BOI"][n].X
            nodes[n]["tes_capacity"] = cap_dom["TES"][n].X
            nodes[n]["air_capacity"] = cap_dom["AIRC"][n].X
            nodes[n]["frc_capacity"] = cap_dom["FRC"][n].X
            
            # save residual loads in nodes
            nodes[n]["res_heat_dem"] = np.zeros((param["n_clusters"], 24))
            nodes[n]["power_dem"] = np.zeros((param["n_clusters"], 24))
            for d in days:
                for t in time_steps:
                    nodes[n]["res_heat_dem"][d][t] = res_thermal[n][d][t].X
                    nodes[n]["power_dem"][d][t] = res_el[n][d][t].X       
        
            # Mass flow from hot to cold pipe
            mass_flow = nodes[n]["res_heat_dem"] * 1000 / (param["c_f"] * (param["T_hot"] - param["T_cold"]))     # kg/s
            nodes[n]["mass_flow"] = mass_flow
            
        
            nodes[n]["tac_building"] = sum(c_total_dom[dev][n].X  for dev in all_devs_dom)
        
        
        # save annualized costs for devices and gas demand for buildings
        param["tac_buildings"] = sum(nodes[n]["tac_building"] for n in nodes)                                       # kEUR/a, annualized costs for building devices
        param["gas_buildings"] = np.zeros((param["n_clusters"],24))
        for d in days:
            for t in time_steps:
                param["gas_buildings"][d][t] = gas["to_buildings"][d][t].X 
        param["gas_buildings_total"] = sum(sum(param["gas_buildings"][d][t] for t in time_steps) * param["day_weights"][d] for d in days)
        
        
        # Print tac
        print("tac: " + str(obj.X))
        

        # Store param and nodes as json

        # param
        for item in ["G_sol", "T_cold", "T_hot", "T_soil_deep", "day_matrix", "day_weights", "gas_buildings", "price_el", "sigma", "t_air", "t_soil"]:
            param[item] = param[item].tolist()
        for item in ["CHP", "PV"]:
            param["revenue_feed_in"][item] = param["revenue_feed_in"][item].tolist()                
        with open(dir_results + "\parameter.json", "w") as outfile:
            json.dump(param, outfile, indent=4, sort_keys=True)    
        
        # nodes
        for item in ["T_cooling_return", "T_cooling_supply", "T_heating_return", "T_heating_supply", "cool", "heat", "mass_flow", "power_dem", "res_heat_dem"]:
            for n in nodes:
                nodes[n][item] = nodes[n][item].tolist()
        with open(dir_results + "\data_nodes.json", "w") as outfile:
            json.dump(nodes, outfile, indent=4, sort_keys=True)         


        # Run Post Processing
        if param["switch_post_processing"]:
            post.run(dir_results)
                
        
    
        return nodes, param
        
#        return tac_total.X





          
                
    
    