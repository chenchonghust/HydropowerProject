# -*- coding: utf-8 -*-
"""
Created on Wed Oct 12 10:50:15 2016
@author: msdogan
"""
# This code optimizes pump-storage hydropower facility operations. 
# Mustafa Dogan
### 02/22/2017
from __future__ import division
import numpy as np
import matplotlib.pyplot as plt
import scipy as sp
from scipy.optimize import differential_evolution
import pandas as pd
import seaborn as sns
sns.set_style('whitegrid')

# This part is all about data (hourly marginal price (wholesale) $/MWh)
##*****************************************************************************
# this function creates price-duration curves
def dur_curve(load, duration, time_period):
    data_raw, INTERVALSTARTTIME_GMT, INTERVALENDTIME_GMT, OPR_DT, OPR_HR = [],[],[],[],[]
    if duration == 'Monthly':
        c_month = months.index(time_period) + 1 # python starts from index 0
        for i in range(len(load)):
            if load.OPR_DT[i].split('-')[1] == c_month:
                data_raw.append(load.Price[i])
                INTERVALSTARTTIME_GMT.append(load.INTERVALSTARTTIME_GMT[i])
                INTERVALENDTIME_GMT.append(load.INTERVALENDTIME_GMT[i])
                OPR_DT.append(load.OPR_DT[i])
                OPR_HR.append(load.OPR_HR[i])
    elif duration == 'Annual':
        for i in range(len(load)):
            if load.OPR_DT[i].split('-')[0] == time_period: # Unit is $/MWh
                data_raw.append(load.Price[i])
                INTERVALSTARTTIME_GMT.append(load.INTERVALSTARTTIME_GMT[i])
                INTERVALENDTIME_GMT.append(load.INTERVALENDTIME_GMT[i])
                OPR_DT.append(load.OPR_DT[i])
                OPR_HR.append(load.OPR_HR[i]) 
    elif duration == 'Daily': # does not work for now     
        y,m,d = time_period.split("-") # year, month, day
        for i in range(len(load)):
            if load.OPR_DT[i].split('-')[0] == y:
                if load.OPR_DT[i].split('-')[1] == m:
                    if load.OPR_DT[i].split('-')[2] == d:
                       data_raw.append(load.Price[i])
                       INTERVALSTARTTIME_GMT.append(load.INTERVALSTARTTIME_GMT[i])
                       INTERVALENDTIME_GMT.append(load.INTERVALENDTIME_GMT[i])
                       OPR_DT.append(load.OPR_DT[i])
                       OPR_HR.append(load.OPR_HR[i])
                       
    else:
        print('please define correct duration and/or time period')
        return  
    prc_data = [[],[],[],[],[]]
    prc_data[0],prc_data[1],prc_data[2],prc_data[3],prc_data[4]=INTERVALSTARTTIME_GMT,INTERVALENDTIME_GMT,OPR_DT,OPR_HR,data_raw
    prc_ordered = pd.DataFrame(np.array(prc_data).T, columns = columns).sort_values(['INTERVALSTARTTIME_GMT'])
    s_name = 'price_ordered_' + str(time_period) + '.csv'    
    prc_ordered.to_csv(s_name, index=False, header=True)
    # after determining what duration and time period to use, create price-duration data
    data = np.sort(data_raw) # sort data
    rank = sp.stats.rankdata(data, method='average') # calculate the rank
    rank = rank[::-1] 
    prob = [100*(rank[i]/(len(data)+1)) for i in range(len(data))] # frequency data
    # save price-duration data
    col = ['Price', 'Frequency']
    pdur = [[],[]]
    pdur[0],pdur[1] = data, prob
    pdur = np.array(pdur)
    price_duration = pd.DataFrame(pdur.T, columns = col, dtype = 'float')
    s_name = 'price_duration_' + str(time_period) + '.csv'
    price_duration.to_csv(s_name)    
    return price_duration, prc_ordered

# Load Price data from OASIS (CAISO) http://oasis.caiso.com/mrioasis/logon.do
name = 'PRC_HASP_LMP.csv'
df = pd.read_csv(name, parse_dates=True) # read data and sort by time (gmt)
months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep','Oct', 'Nov', 'Dec']

P = [[],[],[],[],[]] # empty list to store required data
columns = ['INTERVALSTARTTIME_GMT', 'INTERVALENDTIME_GMT', 'OPR_DT', 'OPR_HR', 'Price'] # headers for data frame

# We are only interested in , start time, end time and LMP
for i in range(len(df)):
    if df.LMP_TYPE[i] == "LMP": # Unit is $/MWh
        P[0].append(df.INTERVALSTARTTIME_GMT[i]) # GMT start
        P[1].append(df.INTERVALENDTIME_GMT[i]) # GMT end
        P[2].append(df.OPR_DT[i]) # OPR Date
        P[3].append(df.OPR_HR[i]) # OPR hour
        P[4].append(df.MW[i]) # price $/MWh
 
P = np.array(P) # convert list to numpy array    
price = pd.DataFrame(P.T, columns = columns) # convert list to data frame

# Examples of 'dur_curve' function use
# Annual Duration and Time
#duration = 'Annual'
#time = '2016'

# Monthly Duration and Time
# duration = 'Monthly'
# time = 'Aug'

# Daily Duration and Time
duration = 'Daily'
time = '2016-09-01'

price_duration, prc_ordered = dur_curve(price, duration, time)

##*****************************************************************************
# Equations
# power_hydro (Watt) = e * g (m/s2) * rho (kg/m3) * Q (m3/s) * head (m)
# power_pump (Watt) = 1/e * g (m/s2) * rho (kg/m3) * Q (m3/s) * head (m)
# generation (Wh) = power (Watt) * hour (h) = 1/(10**6) (MWh)
# revenue ($) = generation (MWh) * price ($/MWh)

# parameters
e_g = 0.90 # generation efficiency
e_p = 0.85 # pumping efficiency
g = 9.81 # m/s2 - acceleration of gravity
rho = 1000 # kg/m3 - density of water
Q_g = 100 # m3/s - water flow for turbine
Q_p = 100 # m3/s - water flow for pumping
head_g = 100 # m - generating head    
head_p = 100 # m - pumping head

# objective function to maximize - continuous function
def obj_func_cont(xx, e_g, e_p, g, rho, Q_g, Q_p, head_g, head_p, optimizing = True):
    H_T = int(price_duration.Frequency.max()) # total duration (100%)
    x1 = np.arange(0,xx)
    y1 = f(x1)
    x2 = np.arange(H_T-xx,H_T)
    y2 = f(x2)
    Power_Revenue = np.trapz(y1, x1, dx=0.1, axis = -1)*e_g*rho*g*Q_g*head_g/(10**6)
    Pumping_Cost = np.trapz(y2, x2, dx=0.1, axis = -1)/e_p*rho*g*Q_p*head_p/(10**6)   
    z = Power_Revenue - Pumping_Cost # profit
    return -z if optimizing else z

# objective function to maximize - discrete
def obj_func_disc(xx, e_g, e_p, g, rho, Q_g, Q_p, head_g, head_p, optimizing = True):
    dH = 0.1 # discretization level
    H_T = int(price_duration.Frequency.max()) # total duration (100%)
    Power_Revenue = 0
    for gen_H in np.arange(0,xx,dH):
        Power_Revenue += f(gen_H)*e_g*rho*g*Q_g*head_g*dH/(10**6)
    Pumping_Cost = 0
    for pump_H in np.arange(H_T-xx,H_T,dH):
        Pumping_Cost += f(pump_H)/e_p*rho*g*Q_p*head_p*dH/(10**6)
    z = Power_Revenue - Pumping_Cost # profit
    return -z if optimizing else z
   
## objective function to maximize - discrete, no curve fitting
def obj_func_disc_nofit(xx, e_g, e_p, g, rho, Q_g, Q_p, head_g, head_p, optimizing = True):
    H_T = int(price_duration.Frequency.max()) # total duration (100%)
    prc_g, prc_p, freq_g, freq_p = [],[],[],[]       
    for i,x in enumerate(price_duration.Frequency):
        if x < xx: # Power Generation price and duration
            prc_g.append(price_duration.Price[i]), freq_g.append(x)
        if H_T - xx < x < H_T: # Pumping price and duration
            prc_p.append(price_duration.Price[i]), freq_p.append(x)  
    prc_g = np.array(prc_g) # generation price
    prc_p = np.array(prc_p) # pumping price
    freq_g = np.array(freq_g) # generation duration
    freq_p = np.array(freq_p) # pumping duration
    # Use numerical integration to integrate (Trapezoidal rule)
    Power_Revenue = np.trapz(prc_g, freq_g, dx=0.1, axis = -1)*e_g*rho*g*Q_g*head_g/(10**6)
    Pumping_Cost = np.trapz(prc_p, freq_p, dx=0.1, axis = -1)/e_p*rho*g*Q_p*head_p/(10**6)   
    z = Power_Revenue - Pumping_Cost # profit
    return z if optimizing else -z

# fit a curve
z = np.polyfit(price_duration.Frequency, price_duration.Price, 9)
f = np.poly1d(z)
x_new = np.linspace(0, price_duration.Frequency.max(), 50)
y_new = f(x_new)

# normal distribution (cumulative, exceedance)
y_norm = np.linspace(0, price_duration.Price.max(), 50)
x_norm = sp.stats.norm(price_duration.Price.mean(), price_duration.Price.std()).sf(y_norm)*100 # survival function

# Reduced Analytical solution without integration: e_g * e_p = P(1-H_G)/P(H_G) 
#for i,item in enumerate(price_duration.Frequency):
#    if (item + (price_duration.Frequency.max()-item)) <= 100: # total proability cannot exceed 1 (100%)
#        if round(f(price_duration.Frequency.max()-item)/f(item),2) == round(e_g * e_p,2):
#            H_G = item
#            print(H_G)

# differential evolution
result = differential_evolution(obj_func_disc_nofit, bounds=[(0,100)], args = (e_g, e_p, g, rho, Q_g, Q_p, head_g, head_p), maxiter=1000, seed = 1)
H_G = result.x

# print price-duration data and curve fitting
plt.scatter(price_duration.Frequency, price_duration.Price)
plt.xlim([0,price_duration.Frequency.max()])
plt.ylim([0,price_duration.Price.max()])
plt.plot(x_norm, y_norm, 'cyan', label = 'Normal Dist.', linewidth=2) # normal dist. plot
plt.plot(x_new, y_new, 'r', label = 'Curve fit') # curve fit plot
plt.ylabel('15 min price $/MWh', fontsize = 14)
plt.xlabel('duration %', fontsize = 14)
plt.title('Optimal Generating and Pumping Hours for ' + str(time), fontsize = 16)
plt.grid(False)    
plt.axvline(x=H_G, linewidth=2, color='k', label = 'Generate Power', linestyle = 'dashed')
plt.axvline(x=price_duration.Frequency.max()-H_G, linewidth=2, color='b', label = 'Pump', linestyle = 'dashed')
plt.legend(fontsize = 12, loc=9)
plt.text(H_G-3,price_duration.Price.min()+(price_duration.Price.max()+price_duration.Price.min())/4, 'Generating Hours, >= ' + str(round(f(H_G),2)) + ' $/MWh', color = 'k', rotation = 'vertical')
plt.text(price_duration.Frequency.max()-H_G+1,price_duration.Price.min()+(price_duration.Price.max()+price_duration.Price.min())/4, 'Pumping Hours, <= ' + str(round(f(price_duration.Frequency.max()-H_G),2)) + ' $/MWh', color = 'b', rotation = 'vertical')
plt.text(5,5,'Generate', fontsize = 15, color = 'k')
plt.text(45,5,'Stop', fontsize = 15, color = 'r')
plt.text(83,5,'Pump', fontsize = 15, color = 'b')
plt.savefig('figure_pd_'+str(time)+'.pdf', transparent=True)
plt.show()

# enumeration
enum_h = np.arange(price_duration.Frequency.min(), price_duration.Frequency.max(), 1)
simulation =np.zeros(len(enum_h))
for i,item in enumerate(enum_h):
    simulation[i] = obj_func_cont(item, e_g, e_p, g, rho, Q_g, Q_p, head_g, head_p, optimizing = False)
index = np.where(simulation == simulation.max())[0]
plt.plot(enum_h, simulation, label = 'Net Profit (Gen-Pump)')
plt.axhline(y=0, linewidth=0.5, color='k')
plt.annotate('max', xy=(enum_h[index],simulation.max()), xytext=(enum_h[index],simulation.max()), arrowprops=dict(facecolor='black', shrink=0.5), fontsize = 12)
plt.title('Enumeration Line for ' + str(time), fontsize = 16)
plt.xlabel('duration %', fontsize = 14)
plt.ylabel('profit $/hour', fontsize = 14)
plt.legend(fontsize = 12, loc=1)
plt.grid(False)
plt.savefig('figure_enum_'+str(time)+'.pdf', transparent=True)
plt.show()

prc = np.array(prc_ordered.Price)
gen_prc = np.zeros(len(prc)) # generating price time-series
pump_prc = np.zeros(len(prc)) # pumping price time-series
plot_gen_prc = np.zeros(len(prc)) # this is only for plotting purposes
for i,item in enumerate(prc):
	if float(item) >= f(H_G):
		gen_prc[i] = item # store generating price
		plot_gen_prc[i] = float(max(prc))
	if float(item) <= f(price_duration.Frequency.max()-H_G):
		pump_prc[i] = item # store pumping price

# # plot time-series data
plot_prc = [prc[i] for i in range(len(prc_ordered.Price))]
plt.bar(range(len(pump_prc)), pump_prc, align='center', color='b', label = 'Pumping Price', alpha=0.25)
plt.bar(range(len(plot_gen_prc)), plot_gen_prc, align='center', color='k', label = 'Generating Price', alpha=0.25)
plt.bar(range(len(gen_prc)), gen_prc, align='center', linewidth=0, color='white', alpha=1)
plt.plot(plot_prc, linewidth=1.5, color='r', label = 'Hourly Price') # use "marker = 'o'" to see points
plt.axhline(y=f(H_G), linewidth=2, color='k', label = 'Generate Power', linestyle = 'dashed')
plt.axhline(y=f(price_duration.Frequency.max()-H_G), linewidth=2, color='b', label = 'Pump', linestyle = 'dashed')
plt.legend(fontsize = 12, loc=9)
plt.xlim([0,len(prc_ordered.Price)])
plt.ylim([0,float(max(prc))])
plt.grid(False)
plt.title('15 Min Price Time-series for ' + str(time), fontsize = 16)
plt.ylabel('15 Min price $/MWh', fontsize = 14)
plt.xlabel('15 min', fontsize = 14)
plt.text(5,f(H_G)+1,'Generate', fontsize = 15, color = 'k')
plt.text(5,(f(H_G)-f(price_duration.Frequency.max()-H_G))/2+f(price_duration.Frequency.max()-H_G),'Stop', fontsize = 15,color = 'r')
plt.text(5,f(price_duration.Frequency.max()-H_G)-3,'Pump', fontsize = 15, color = 'b')
plt.savefig('figure_ts_'+str(time)+'.pdf', transparent=True)
plt.show()

print(result) # show EA solver message
print('')
print('*******Optimal Operation at '+ str(round(H_G,2)) + ' % of Total 15 minutes*******')
