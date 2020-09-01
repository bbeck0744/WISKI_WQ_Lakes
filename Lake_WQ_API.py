# -*- coding: utf-8 -*-
"""
Created on Mon Aug 31 16:54:15 2020

@author: bbeck
"""

import requests
import pandas as pd
from datetime import datetime
import geopandas
from shapely.geometry import Point


#selects previous year to calculate annual water quality averages
currentYear = datetime.now().year-1
#Water quality calculation are typically calculated for the "summer average", which is defined as June through September by the MCPA
start_date = f"{currentYear}-06-01"
end_date = f"{currentYear}-09-30"
#select data from lake sites only
site_type = "LK_STATION"
#output data as json
output_type = f"objson"
#base WISKI API URL
base_url = f"http://gis.minnehahacreek.org/KiWIS/"
#site and water quality data API urls to get site lat/longs and water quality data
site_url = f"{base_url}/KiWIS?datasource=0&format={output_type}&from={start_date}&to={end_date}&request=getwqmstationlist&service=kisters&object_type_shortname={site_type}&type=queryServices"
wq_data_url = f"{base_url}/KiWIS?datasource=0&format={output_type}&from={start_date}&to={end_date}&request=getwqmsamplevalues&service=kisters&object_type_shortname={site_type}&type=queryServices"

#site API get request
site_response = requests.get(site_url)
sites = site_response.json()

#water quality API get request
data_response = requests.get(wq_data_url)
WQ = data_response.json()

#create dataframes from get requests
sites_df = pd.DataFrame(sites)
WQ_df = pd.DataFrame(WQ)

#merge dataframes 
data_merge = pd.merge(WQ_df, sites_df, on="station_no", how="left")

#data processing to obtain lake total phosphorus, clarity (SD), and algae (chl-a)
data_merge['station_no_parameter'] = data_merge['station_no'] + '-' + data_merge['parametertype_name']  
WQ_subset = data_merge[(data_merge["parametertype_name"] == "TP") | (data_merge["parametertype_name"] == "SD") | (data_merge["parametertype_name"] == "ChlA")]

#calculate annual averages
result = WQ_subset.groupby('station_no_parameter', as_index=False).mean()

#iterate through keys to find original lake names and lab analysis unit values
units = []
lake_name = []

for i in result.station_no_parameter:
    units.append(WQ_subset['unit_symbol'][WQ_subset['station_no_parameter'] == i].iloc[0])
    lake_name.append(WQ_subset['station_name_y'][WQ_subset['station_no_parameter'] == i].iloc[0])
result.insert(2, 'unit_symbol', units)
result.insert(1, 'station_name_y', lake_name)

#split the parameter and lake ID to create lake id and parameter columns
split_data = result.station_no_parameter.str.split('-', expand=True).rename({0: 'Site', 1: 'Parameter'}, axis=1)

#combine the split columns and result dataframe
wq_combined = pd.concat([split_data, result], axis=1)

#Convert coordinates  into point data for GIS processing
wq_combined['coordinates'] = wq_combined[['station_longitude', 'station_latitude']].values.tolist()
wq_combined['coordinates'] = wq_combined['coordinates'].apply(Point)
Lake_WQ_Data = geopandas.GeoDataFrame(wq_combined, geometry='coordinates')


