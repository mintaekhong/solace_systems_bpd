import streamlit as st
import folium
from folium.plugins import TimestampedGeoJson
from streamlit_folium import folium_static
import pandas as pd
import numpy as np
import datetime
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
import geopandas as gpd
import json
import branca.colormap as cm

def app():
    st.title("Fire Prevention System Demo")
    st.subheader("Palisades Fire Simulation")
    
    # Palisades Village coordinates
    palisades_village = [34.0453, -118.5265]  # lat, lon
    
    # Simulated fire origin point (adjusted for Palisades fire)
    fire_origin = [34.0556, -118.5334]  # lat, lon for a point north of Palisades Village
    
    # Time control
    st.sidebar.header("Simulation Controls")
    days = st.sidebar.slider("Simulation Days", 1, 7, 3)
    hours_per_step = st.sidebar.slider("Hours per Step", 1, 12, 6)
    wind_direction = st.sidebar.slider("Wind Direction (degrees)", 0, 359, 225)  # 225 = southwest wind
    wind_speed = st.sidebar.slider("Wind Speed (mph)", 0, 30, 15)
    
    # Fire spread parameters
    base_spread_rate = 0.2  # km per hour
    wind_factor = wind_speed / 10  # normalize wind effect
    
    # Create base map centered between fire origin and target location
    center_lat = (fire_origin[0] + palisades_village[0]) / 2
    center_lon = (fire_origin[1] + palisades_village[1]) / 2
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=14, 
                   tiles="Stamen Terrain")
    
    # Add Palisades Village marker
    folium.Marker(
        location=palisades_village,
        popup="Palisades Village<br>15225 Palisades Village Ln",
        icon=folium.Icon(icon="home", prefix="fa", color="blue"),
    ).add_to(m)
    
    # Add fire origin marker
    folium.Marker(
        location=fire_origin,
        popup="Fire Origin",
        icon=folium.Icon(icon="fire", prefix="fa", color="red"),
    ).add_to(m)
    
    # Create fire spread polygons over time
    features = []
    
    start_time = datetime.datetime(2023, 5, 1, 0, 0)  # Example start date
    
    # Create a color map for the fire intensity
    colormap = cm.linear.YlOrRd_09.scale(0, days)
    
    for day in range(days + 1):
        for hour in range(0, 24, hours_per_step):
            if day == 0 and hour == 0:
                # Initial small fire
                radius = 0.05  # km
            else:
                # Calculate spread based on time and wind
                elapsed_hours = day * 24 + hour
                
                # Base spread calculation
                radius = elapsed_hours * base_spread_rate
                
                # Apply wind factor (simplified)
                wind_direction_rad = np.radians(wind_direction)
                wind_effect = wind_factor * elapsed_hours * 0.01
            
            # Create points for the fire polygon
            # Here we're creating an elliptical fire shape oriented based on wind direction
            points = []
            for angle in range(0, 360, 10):
                angle_rad = np.radians(angle)
                
                # Elongate in wind direction
                factor = 1.0
                if abs(angle - wind_direction) < 90 or abs(angle - wind_direction) > 270:
                    factor += wind_effect  # Elongate downwind
                
                dx = radius * factor * np.cos(angle_rad)
                dy = radius * factor * np.sin(angle_rad)
                
                # Convert km to approximate lat/lon
                lon = fire_origin[1] + dx / 111.32 / np.cos(np.radians(fire_origin[0]))
                lat = fire_origin[0] + dy / 111.32
                
                points.append([lon, lat])
            
            # Close the polygon
            points.append(points[0])
            
            # Calculate time for this step
            time = start_time + datetime.timedelta(days=day, hours=hour)
            time_str = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Calculate intensity (0-1) based on days passed
            intensity = day / days if days > 0 else 0
            color = colormap(intensity)
            
            # Add the fire polygon to features
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [points]
                },
                "properties": {
                    "time": time_str,
                    "icon": "circle",
                    "iconstyle": {
                        "fillColor": color,
                        "fillOpacity": 0.6,
                        "stroke": True,
                        "radius": 5,
                        "weight": 2,
                        "opacity": 0.8,
                        "color": "red"
                    },
                    "style": {
                        "color": color,
                        "fillColor": color,
                        "fillOpacity": 0.6,
                        "weight": 1
                    },
                    "popup": f"Day {day}, Hour {hour}<br>Fire Area"
                }
            }
            features.append(feature)
    
    # Create TimestampedGeoJson layer
    timestamped_geojson = TimestampedGeoJson(
        {
            "type": "FeatureCollection",
            "features": features,
        },
        period="PT{}H".format(hours_per_step),
        duration="PT1H",
        add_last_point=True,
        auto_play=True,
        loop=False,
        max_speed=5,
        loop_button=True,
        date_options="YYYY-MM-DD HH:mm:ss",
        time_slider_drag_update=True,
    )
    
    timestamped_geojson.add_to(m)
    
    # Add a buffer zone around Palisades Village
    folium.Circle(
        location=palisades_village,
        radius=300,  # meters
        color="blue",
        fill=True,
        fill_color="blue",
        fill_opacity=0.1,
        popup="Protected Zone",
    ).add_to(m)
    
    # Calculate distance between fire origin and Palisades Village
    from geopy.distance import geodesic
    distance = geodesic(fire_origin, palisades_village).kilometers
    
    # Add fire spread information
    st.sidebar.subheader("Fire Information")
    st.sidebar.info(f"Distance from fire origin to Palisades Village: {distance:.2f} km")
    st.sidebar.info(f"Estimated time to reach Palisades Village: {distance / (base_spread_rate * (1 + wind_factor)):.1f} hours at current conditions")
    
    # Risk assessment
    risk_level = "Low"
    if wind_direction > 180 and wind_direction < 270 and wind_speed > 10:
        risk_level = "High"
    elif wind_speed > 20:
        risk_level = "Moderate"
    
    st.sidebar.warning(f"Current Risk Assessment: {risk_level}")
    
    # Protection strategies
    st.sidebar.subheader("Protection Strategies")
    strategies = [
        "Deploy fire breaks 0.5km north of property",
        "Establish water resources at key locations",
        "Pre-wet vegetation in approach path",
        "Set up early warning sensors in fire path"
    ]
    for s in strategies:
        st.sidebar.checkbox(s)
    
    # Display the map in Streamlit
    st.write("The map below shows the simulated spread of the Palisades fire over time, approaching Palisades Village. The simulation takes into account wind direction and speed.")
    folium_static(m)
    
    # Additional information
    with st.expander("How to use this demo"):
        st.write("""
        - Use the slider in the time-lapse control to see fire progression over time
        - Adjust wind and simulation parameters in the sidebar
        - Select protection strategies to visualize their effect
        - The color intensity of the fire area indicates the fire intensity
        """)
    
    with st.expander("Fire Prevention System Details"):
        st.write("""
        Our fire prevention system offers:
        - Real-time fire spread prediction based on weather conditions
        - Automated alerts based on proximity thresholds
        - Integration with property defense systems
        - Evacuation route planning based on fire behavior
        - Coordination with local fire departments
        """)

if __name__ == "__main__":
    app()