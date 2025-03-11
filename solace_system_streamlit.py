import streamlit as st
import folium
from folium.plugins import TimestampedGeoJson
from streamlit_folium import folium_static
import pandas as pd
import numpy as np
import datetime
from shapely.geometry import Polygon
import branca.colormap as cm
from geopy.distance import geodesic

def app():
    st.title("Fire Prevention System Demo")
    st.subheader("Palisades Fire Simulation")
    
    # Palisades Village coordinates
    palisades_village = [34.0453, -118.5265]
    
    # Simulated fire origin point
    fire_origin = [34.0556, -118.5334]
    
    # Time control
    st.sidebar.header("Simulation Controls")
    days = st.sidebar.slider("Simulation Days", 1, 7, 3)
    hours_per_step = st.sidebar.slider("Hours per Step", 1, 12, 6)
    wind_direction = st.sidebar.slider("Wind Direction (degrees)", 0, 359, 225)
    wind_speed = st.sidebar.slider("Wind Speed (mph)", 0, 30, 15)
    
    # Fire spread parameters
    base_spread_rate = 0.2  # km/hour
    wind_factor = wind_speed / 10
    
    # -- Define a maximum spread radius (km)
    max_radius_km = 3.0
    
    # Create base map
    center_lat = (fire_origin[0] + palisades_village[0]) / 2
    center_lon = (fire_origin[1] + palisades_village[1]) / 2
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=14,
        tiles="CartoDB positron"
    )
    
    # Markers
    folium.Marker(
        location=palisades_village,
        popup="Palisades Village<br>15225 Palisades Village Ln",
        icon=folium.Icon(icon="home", prefix="fa", color="blue")
    ).add_to(m)
    
    folium.Marker(
        location=fire_origin,
        popup="Fire Origin",
        icon=folium.Icon(icon="fire", prefix="fa", color="red")
    ).add_to(m)
    
    # Fire polygons over time with layered danger zones
    features = []
    
    # Start date (updated to 2025-01-07)
    start_time = datetime.datetime(2025, 1, 7, 0, 0)
    
    # Number of zones and colors (from most dangerous to least)
    n_zones = 3
    zone_colors = ["red", "orange", "yellow"]
    
    for day in range(days + 1):
        for hour in range(0, 24, hours_per_step):
            if day == 0 and hour == 0:
                # Initial small fire
                radius = 0.05  # km
                wind_effect = 0
            else:
                elapsed_hours = day * 24 + hour
                radius = elapsed_hours * base_spread_rate
                wind_effect = wind_factor * elapsed_hours * 0.01
            
            # -- Clamp the radius to max_radius_km
            if radius > max_radius_km:
                radius = max_radius_km
            
            # Create concentric zones (draw outer first so inner red appears on top)
            for i in reversed(range(n_zones)):
                fraction = (i + 1) / n_zones  # e.g., 1/3, 2/3, 3/3
                zone_r = radius * fraction
                color = zone_colors[i]
                
                points = []
                for angle in range(0, 360, 10):
                    angle_rad = np.radians(angle)
                    factor = 1.0
                    if abs(angle - wind_direction) < 90 or abs(angle - wind_direction) > 270:
                        factor += wind_effect
                    dx = zone_r * factor * np.cos(angle_rad)
                    dy = zone_r * factor * np.sin(angle_rad)
                    lon = fire_origin[1] + dx / 111.32 / np.cos(np.radians(fire_origin[0]))
                    lat = fire_origin[0] + dy / 111.32
                    points.append([lon, lat])
                points.append(points[0])
                
                time = start_time + datetime.timedelta(days=day, hours=hour)
                time_str = time.strftime("%Y-%m-%d %H:%M:%S")
                
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
                            "fillOpacity": 0.4,
                            "stroke": True,
                            "radius": 5,
                            "weight": 1,
                            "opacity": 0.8,
                            "color": color
                        },
                        "style": {
                            "color": color,
                            "fillColor": color,
                            "fillOpacity": 0.4,
                            "weight": 1
                        },
                        "popup": f"Day {day}, Hour {hour} - Zone {i+1}"
                    }
                }
                features.append(feature)
    
    # Time-stamped GeoJSON with looping enabled
    timestamped_geojson = TimestampedGeoJson(
        {
            "type": "FeatureCollection",
            "features": features
        },
        period=f"PT{hours_per_step}H",
        duration="PT1H",
        add_last_point=True,
        auto_play=True,
        loop=True,  # Restart simulation automatically
        max_speed=5,
        loop_button=True,
        date_options="YYYY-MM-DD HH:mm:ss",
        time_slider_drag_update=True
    )
    timestamped_geojson.add_to(m)
    
    # Protected zone circle around Palisades Village
    folium.Circle(
        location=palisades_village,
        radius=300,
        color="blue",
        fill=True,
        fill_color="blue",
        fill_opacity=0.1,
        popup="Protected Zone"
    ).add_to(m)
    
    distance = geodesic(fire_origin, palisades_village).kilometers
    st.sidebar.subheader("Fire Information")
    st.sidebar.info(f"Distance from fire origin to Palisades Village: {distance:.2f} km")
    st.sidebar.info(
        f"Estimated time to reach Palisades Village: "
        f"{distance / (base_spread_rate * (1 + wind_factor)):.1f} hours at current conditions"
    )
    
    risk_level = "Low"
    if 180 < wind_direction < 270 and wind_speed > 10:
        risk_level = "High"
    elif wind_speed > 20:
        risk_level = "Moderate"
    st.sidebar.warning(f"Current Risk Assessment: {risk_level}")
    
    st.sidebar.subheader("Protection Strategies")
    strategies = [
        "Deploy fire breaks 0.5km north of property",
        "Establish water resources at key locations",
        "Pre-wet vegetation in approach path",
        "Set up early warning sensors in fire path"
    ]
    for s in strategies:
        st.sidebar.checkbox(s)
    
    st.write("This simulation shows concentric danger zones with a capped spread. The fire stops growing once it reaches the maximum area, and then the simulation loops.")
    folium_static(m)
    
    with st.expander("How to use this demo"):
        st.write("""
        - Use the time slider or play button to watch the fire expand over time.
        - The fire expands until it reaches a maximum radius, then stops growing.
        - Concentric zones indicate danger levels: red (highest), orange, yellow (lowest).
        - When the timeline ends, the simulation repeats.
        """)

if __name__ == "__main__":
    app()
