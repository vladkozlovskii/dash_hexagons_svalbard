#!/usr/bin/env python
# coding: utf-8

# In[7]:


import branca
import h3
import json
import pandas as pd
import plotly.express as px
import dash_leaflet as dl
from dash import Dash, dcc, html, Input, Output
from dash_extensions.javascript import arrow_function, assign

#path = 'C:/Users/v.kozlovskiy/Desktop/_dash_hex_new_test/_dash_hex_new_test_var_03/'
#path = '/Users/vladkozlovskiy/Downloads/DATAS/Kara_sea_test/Dash_hex_2_table/'
data3 = pd.read_csv('datafile.csv', sep=';')

# javascript function for return color of the hexagon (make choropleth from layer)
style_handle = assign("""function(feature) {
    return {
        fillColor: feature.properties.color,
        weight: 1,
        opacity: 0.5,
        color: 'white',
        fillOpacity: 0.5    
    };
}""")

# javascript function for make popup near the hexagons
on_each_feature = assign("""function(feature, layer, context){
    layer.bindTooltip(`${feature.properties.name_parameter} (${feature.properties.param})`)
}""")

app = Dash()

# lists for dropdowns
quant_list = ['chlorophуll', 'oxygen', 'net_primary_production', 'depth_gebco']
time_list = data3['time'].unique()[:13]

# start components for map
children = [dl.TileLayer(), 
             dl.MeasureControl(position="topleft", primaryLengthUnit="kilometers", primaryAreaUnit="hectares", 
                               activeColor="#214097", completedColor="#972158"),
             dl.ScaleControl(position="bottomleft")]

# start components for plot
figure = px.line(
            data3.dropna(),
            x=data3.dropna()['time'].unique(),
            y=data3.dropna().groupby('time')['chlorophуll'].agg('mean'),
    #        title = 'chl' + ' by month',
    )

# Sample data for dropdowns
dropdown_options = [{'label': 'Parameter', 'value': 'chlorophуll'},
                    {'label': 'Time', 'value': '2022-10-01'}]

# Create Plotly line plot
plot = dcc.Graph(
    id='graph',
    style={'width': '100%', 'height': '300px'} 
)

# Create Dash Leaflet map
map_component = dl.Map(
    id='map',
    style={'width': '100%', 'height': '350px'},
    center=[78, 10],
    zoom=4,
    children=children
)

# Define the layout using Bootstrap grid system
app.layout = html.Div([
    html.H1('Depth and some ecological parameters near Svalbard', style={"font-size": "20px"}),
    
    # Dropdowns above the graph and map
    html.Div([html.Div("Parameter", style={"font-size": "15px"}),
        dcc.Dropdown(id= 'dropdown_1', options=quant_list, value='chlorophуll'),  # Dropdown 1
        html.Div("Month", style={"font-size": "15px"}),
        dcc.Dropdown(id= 'dropdown_2', options=time_list, value='2022-10-01'),  # Dropdown 2
    ]),
    
    # Two columns using Bootstrap grid system
    html.Div([
        # down part for the graph
        html.Div([
            html.H3('Average value of the parameter in the hexagon on map', style={"font-size": "15px"}),
            map_component
              # Plotly line plot component
        ], className='six columns'), #style = {'float':'right'}),
        
        # upper part for the map
        html.Div([
            html.H3('Dynamics of the average value of the parameter during the year', style={"font-size": "15px"}),
            plot  # Dash Leaflet map component
        ], className='six columns'), #style = {'float':'left'}),
    ], className='row')
])


@app.callback(
    Output("map", "children"),
    Input("dropdown_1", "value"),
    Input("dropdown_2", "value"),    
)

def hexagons_map(dd1, dd2):
    
    to_compare = abs(data3.loc[data3['time'] == dd2].dropna(subset=dd1)[dd1].sum()) # this is for check 0 values to prevent
                                                                                    # bug with colorbar  
    
    data2 = data3.copy()
    data2['geometry'] = data2['h3'].apply(lambda x: h3.h3_to_geo_boundary(x))  # take boundarys of the hexagons
    data2 = data2.dropna(subset=dd1)        
    if dd1 != 'depth_gebco':                                 # filtration - parameter depth_gebco differ because other parameters has NaN in df
        data2 = data2.loc[data2['time'] == dd2]
        data2 = data2[['h3', 'geometry', dd1]]
    
    if dd1 == 'depth_gebco':
        data2 = data2[['h3', 'geometry', 'depth_gebco']].drop_duplicates()
        data2 = data2.drop_duplicates()

    if to_compare < 1:
        colormap = branca.colormap.LinearColormap(colors=['cyan', 'green', 'orange','red'],          
                            vmin=0, vmax=10)    # this varinat to prevent bags showing 0 values in net_primary production
    else:
        colormap = branca.colormap.LinearColormap(colors=['cyan', 'green', 'orange','red'],
                            vmin=round(data2[dd1].min(), 2), vmax=round(data2[dd1].max(), 2))
    

    
    # making geojson (i tried to use another approaches using folium, or draw polygons but only using geojson map start working)
    features = []
    for i in range(len(data2)):
        h3_ind = data2['h3'].iloc[i]
        geometry = data2['geometry'].iloc[i]           
        param = round(float(data2[dd1].iloc[i]), 2)  
        # Create a GeoJSON feature
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [geometry]
            },
            "properties": {
                "name": h3_ind,
                "name_parameter": dd1,
                 "param": param,
                "color": colormap(param)
                # Add other properties as needed
            }
        }
       
        # Append the feature to the features list
        features.append(feature)

    # Create a GeoJSON object
    geojson_data = {
        "type": "FeatureCollection",
        "features": features
    }
    
    with open('data.geojson', 'w') as fp:     # dump geojson
        json.dump(geojson_data, fp)
    
    with open('data.geojson', 'r') as fp:     # open geojson for correct geometry
        geojson_data = json.load(fp)
    
    # Reorder coordinates in each polygon
    for feature in geojson_data['features']:
        if feature['geometry']['type'] == 'Polygon':
        # Assuming coordinates are [longitude, latitude]
            for coords in feature['geometry']['coordinates']:
                coords[0][0], coords[0][1] = coords[0][1], coords[0][0]
                coords[1][0], coords[1][1] = coords[1][1], coords[1][0]
                coords[2][0], coords[2][1] = coords[2][1], coords[2][0]
                coords[3][0], coords[3][1] = coords[3][1], coords[3][0]
                coords[4][0], coords[4][1] = coords[4][1], coords[4][0]
                coords[5][0], coords[5][1] = coords[5][1], coords[5][0]            
    
    with open('data.geojson', 'w') as fp:      # dump again
        json.dump(geojson_data, fp)
 
    with open('data.geojson', 'r') as fp:      # open again for show in map
        geojson_data = json.load(fp)
    
    # here adding components of map - main component is GeoJSON
    main_list = []    
    main_list.append(dl.GeoJSON(data=geojson_data, style=style_handle, id='geojson', onEachFeature=on_each_feature)) 
    main_list.append(dl.TileLayer())
    main_list.append(dl.MeasureControl(position="topleft", primaryLengthUnit="kilometers", primaryAreaUnit="hectares", activeColor="#214097", completedColor="#972158"))
    main_list.append(dl.FullScreenControl())
    main_list.append(dl.ScaleControl(position="bottomleft"))
    
    # add colorbar
    if to_compare < 1:
        main_list.append(dl.Colorbar(colorscale=['cyan', 'green', 'orange','red'], min=0, max=10))                     
    else:
        main_list.append(dl.Colorbar(colorscale=['cyan', 'green', 'orange','red'], min=round(data2[dd1].min(), 2), max=round(data2[dd1].max(), 2)))   
    

    children = main_list
    return children 

# i made variant with only one callback for both structures and functions but here left two 
@app.callback(
    Output("graph", "figure"),
    Input("dropdown_1", "value")  
)

# function for drawing plot
def function_2(dd1):
    figure = px.line(
            data3.dropna(),
            x=data3.dropna()['time'].unique(),
            y=data3.dropna().groupby('time')[dd1].agg('mean'),
     #       title = dd1 + ' by month',
            labels={
                     "x" : "month",
                     "y": dd1
            },
)
    
    return figure

if __name__ == '__main__':
    app.run_server(debug=False, host='0.0.0.0', port=8080)





