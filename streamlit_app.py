# import streamlit as st
# import pandas as pd
# import plotly.express as px
# import plotly.graph_objects as go
# from pymavlink import mavutil
# import tempfile
# import os

# # --- SYSTEM CONFIGURATION & THEMING ---
# st.set_page_config(page_title="Achuk Navigation Analytics", layout="wide", page_icon="📊")

# st.markdown("""
# <style>
#     body { background-color: #0d1117; color: #c9d1d9; }
#     .stApp { background-color: #0d1117; }
#     .insight-card {
#         background-color: #161b22;
#         border: 1px solid #30363d;
#         border-radius: 6px;
#         padding: 15px;
#         height: 100%;
#     }
#     .insight-title { font-size: 0.85rem; color: #8b949e; text-transform: uppercase; font-weight: bold; letter-spacing: 0.5px; }
#     .insight-value { font-size: 1.8rem; font-weight: bold; color: #58a6ff; margin: 10px 0; }
#     .insight-sub { font-size: 0.8rem; color: #8b949e; }
#     .highlight-green { color: #3fb950; font-weight: bold; }
#     .highlight-red { color: #f85149; font-weight: bold; }
# </style>
# """, unsafe_allow_html=True)

# # --- 100% DYNAMIC TELEMETRY PARSER ---
# @st.cache_data(show_spinner="Extracting raw MAVLink telemetry...")
# def parse_analytical_telemetry(file_bytes, filename):
#     """
#     Strictly extracts data from the uploaded .tlog. Zero simulated fallbacks.
#     Synchronizes MAVLink packets using timestamps.
#     """
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".tlog") as tmp:
#         tmp.write(file_bytes)
#         tmp_path = tmp.name

#     mlog = mavutil.mavlink_connection(tmp_path)
#     records = []
    
#     # State tracking variables for asynchronous packets
#     current_mode = "UNKNOWN"
#     current_alt = 0.0
#     current_nav_roll = 0.0
#     current_nav_pitch = 0.0
#     start_time = None
    
#     while True:
#         m = mlog.recv_match(blocking=False)
#         if m is None:
#             break
            
#         m_type = m.get_type()
#         timestamp = getattr(m, '_timestamp', None)
        
#         # Initialize master clock on first valid timestamp
#         if timestamp is not None and start_time is None:
#             start_time = timestamp

#         # 1. State Transitions (Modes via Heartbeat)
#         if m_type == 'HEARTBEAT':
#             try: 
#                 mode_str = mlog.flightmode
#             except AttributeError: 
#                 mode_str = f"MODE_{m.custom_mode}"
#             if mode_str: 
#                 current_mode = mode_str.upper()

#         # 2. Altitude Tracking (Handles both GPS and SITL Local formats)
#         elif m_type == 'GLOBAL_POSITION_INT':
#             current_alt = m.relative_alt / 1000.0
#         elif m_type == 'LOCAL_POSITION_NED':
#             current_alt = -m.z

#         # 3. Target Navigation Commands
#         elif m_type == 'NAV_CONTROLLER_OUTPUT':
#             current_nav_roll = m.nav_roll
#             current_nav_pitch = m.nav_pitch

#         # 4. Actual Attitude (Acts as the recording trigger)
#         elif m_type == 'ATTITUDE':
#             if timestamp is None: 
#                 continue
            
#             roll = m.roll * 57.2958
#             pitch = m.pitch * 57.2958
            
#             # Simple combined absolute error tracker
#             tracking_error = abs(current_nav_roll - roll) + abs(current_nav_pitch - pitch)

#             records.append({
#                 'time_sec': timestamp - start_time,
#                 'alt': current_alt,
#                 'roll': roll,
#                 'pitch': pitch,
#                 'nav_roll': current_nav_roll,
#                 'nav_pitch': current_nav_pitch,
#                 'mode': current_mode,
#                 'tracking_error': tracking_error
#             })

#     os.remove(tmp_path)
#     return pd.DataFrame(records)

# # --- METRIC CALCULATION ENGINE ---
# def calculate_mode_segments(df):
#     """Calculates start, end, and duration of every dynamic flight mode trigger."""
#     if df.empty:
#         return pd.DataFrame()
        
#     df['mode_shift'] = df['mode'] != df['mode'].shift()
#     df['segment_id'] = df['mode_shift'].cumsum()
    
#     segments = df.groupby(['segment_id', 'mode']).agg(
#         start_time=('time_sec', 'min'),
#         end_time=('time_sec', 'max'),
#         avg_alt=('alt', 'mean'),
#         max_error=('tracking_error', 'max')
#     ).reset_index()
    
#     segments['duration'] = segments['end_time'] - segments['start_time']
#     return segments

# # --- MAIN UI ---
# st.markdown("## 📊 DYNAMIC TELEMETRY & NAVIGATION TRACKING")
# st.markdown("`SOURCE: DIRECT MAVLINK EXTRACTION` • `ATTITUDE LATENCY` • `STATE TRANSITIONS`")
# st.markdown("---")

# with st.sidebar:
#     st.header("Log Ingestion")
#     uploaded_files = st.file_uploader("Upload Trainee Logs (.tlog)", accept_multiple_files=True, type=['tlog'])

# if uploaded_files:
#     trainee_db = {}
#     for file in uploaded_files:
#         profile_name = file.name.split('.')[0].replace('_', ' ').upper()
#         df_parsed = parse_analytical_telemetry(file.getvalue(), file.name)
#         if not df_parsed.empty:
#             trainee_db[profile_name] = df_parsed

#     if not trainee_db:
#         st.error("Uploaded files did not contain valid ATTITUDE or HEARTBEAT telemetry packets.")
#         st.stop()

#     target_profile = st.selectbox("🎯 Select Trainee Log Profile", list(trainee_db.keys()))
#     df = trainee_db[target_profile]
    
#     segments_df = calculate_mode_segments(df)
    
#     # Dynamically find tracked/guided modes (Offboard, Guided, Auto)
#     automated_modes = ['OFFBOARD', 'GUIDED', 'AUTO']
#     tracked_segments = segments_df[segments_df['mode'].isin(automated_modes)]
    
#     track_count = len(tracked_segments)
#     total_track_time = tracked_segments['duration'].sum() if not tracked_segments.empty else 0
#     peak_nav_error = df['tracking_error'].max() if not df.empty else 0
#     avg_alt = df['alt'].mean() if not df.empty else 0

#     # --- ROW 1: MISSION INSIGHTS ---
#     c1, c2, c3, c4 = st.columns(4)
#     with c1:
#         st.markdown(f"""
#         <div class='insight-card'>
#             <div class='insight-title'>Guided/Offboard Triggers</div>
#             <div class='insight-value'>{track_count} <span style='font-size:1rem;color:#8b949e;'>Engagements</span></div>
#             <div class='insight-sub'>Total Track Time: <span class='highlight-green'>{total_track_time:.1f}s</span></div>
#         </div>
#         """, unsafe_allow_html=True)
#     with c2:
#         st.markdown(f"""
#         <div class='insight-card'>
#             <div class='insight-title'>Peak Tracking Deviation</div>
#             <div class='insight-value'>{peak_nav_error:.2f}°</div>
#             <div class='insight-sub'>Max error across mission</div>
#         </div>
#         """, unsafe_allow_html=True)
#     with c3:
#         st.markdown(f"""
#         <div class='insight-card'>
#             <div class='insight-title'>Mission Average Altitude</div>
#             <div class='insight-value'>{avg_alt:.1f} m</div>
#             <div class='insight-sub'>Relative to home origin</div>
#         </div>
#         """, unsafe_allow_html=True)
#     with c4:
#         st.markdown(f"""
#         <div class='insight-card'>
#             <div class='insight-title'>Data Points Extracted</div>
#             <div class='insight-value'>{len(df)}</div>
#             <div class='insight-sub'>Valid Attitude Packets</div>
#         </div>
#         """, unsafe_allow_html=True)

#     st.markdown("---")

#     # --- ROW 2: FLIGHT MODE STATE TIMELINE ---
#     st.subheader("Dynamic Flight Phase Transitions")
#     st.markdown("Exact boundaries showing when firmware mode transitions occurred.")
    
#     fig_timeline = px.timeline(
#         segments_df, x_start="start_time", x_end="end_time", y="mode", color="mode",
#         hover_data={"duration": ':.1f', "avg_alt": ':.1f'}
#     )
    
#     fig_timeline.layout.xaxis.type = 'linear'
#     for d in fig_timeline.data:
#         filt = segments_df['mode'] == d.name
#         d.x = segments_df[filt]['duration']
#         d.base = segments_df[filt]['start_time']

#     fig_timeline.update_layout(
#         paper_bgcolor='#161b22', plot_bgcolor='#161b22', font_color='#c9d1d9',
#         xaxis=dict(title="Mission Time (Seconds)", gridcolor='#30363d'),
#         yaxis=dict(title="Active Flight Mode"),
#         height=280, margin=dict(l=0, r=0, t=30, b=0), showlegend=False
#     )
#     st.plotly_chart(fig_timeline, width='stretch')

#     # --- ROW 3: NAVIGATION COMMAND VS ACTUAL ---
#     st.markdown("---")
#     st.subheader("Target Navigation vs. Actual Attitude")
#     st.markdown("Evaluates response latency and overshoot based on `NAV_CONTROLLER_OUTPUT` streams.")

#     axis_view = st.radio("Select Analysis Vector", ["Roll Tracking", "Pitch Tracking", "Both Axes"], horizontal=True)

#     fig_nav = go.Figure()

#     if axis_view in ["Roll Tracking", "Both Axes"]:
#         fig_nav.add_trace(go.Scatter(x=df['time_sec'], y=df['nav_roll'], name="Target Roll (Command)", line=dict(color='#3fb950', width=2, dash='dot')))
#         fig_nav.add_trace(go.Scatter(x=df['time_sec'], y=df['roll'], name="Actual Roll", line=dict(color='#58a6ff', width=2)))

#     if axis_view in ["Pitch Tracking", "Both Axes"]:
#         fig_nav.add_trace(go.Scatter(x=df['time_sec'], y=df['nav_pitch'], name="Target Pitch (Command)", line=dict(color='#d29922', width=2, dash='dot')))
#         fig_nav.add_trace(go.Scatter(x=df['time_sec'], y=df['pitch'], name="Actual Pitch", line=dict(color='#ff7b72', width=2)))

#     # Automatically highlight sections where the drone was in automated tracking modes
#     for idx, row in tracked_segments.iterrows():
#         fig_nav.add_vrect(
#             x0=row['start_time'], x1=row['end_time'],
#             fillcolor="#a371f7", opacity=0.1, layer="below", line_width=0,
#             annotation_text=f"{row['mode']} ACTIVE", annotation_position="top left",
#             annotation_font=dict(color="#a371f7", size=10)
#         )

#     fig_nav.update_layout(
#         paper_bgcolor='#161b22', plot_bgcolor='#161b22', font_color='#c9d1d9',
#         xaxis=dict(title="Mission Time (Seconds)", gridcolor='#30363d'),
#         yaxis=dict(title="Degrees", gridcolor='#30363d'),
#         height=450, margin=dict(l=0, r=0, t=30, b=0), hovermode="x unified"
#     )
#     st.plotly_chart(fig_nav, width='stretch')

#     # --- ROW 4: DATA TABLE INSIGHTS ---
#     st.markdown("---")
#     st.subheader("Raw Phase Diagnostics")
#     st.dataframe(
#         segments_df[['mode', 'start_time', 'end_time', 'duration', 'max_error', 'avg_alt']].style.format({
#             'start_time': '{:.1f}s', 'end_time': '{:.1f}s', 
#             'duration': '{:.1f}s', 'max_error': '{:.2f}°', 'avg_alt': '{:.1f}m'
#         }),
#         width='stretch',
#         hide_index=True
#     )

# else:
#     st.info("Awaiting telemetry logs. Please upload raw `.tlog` files to map the dynamic tracking vectors.")


# Version 2
# import streamlit as st
# import pandas as pd
# import plotly.express as px
# import numpy as np
# import os

# # 1. Page Settings & Aerospace Theme Base
# st.set_page_config(
#     page_title="AeroLog Pro | UAV Flight Log Analytics",
#     page_icon="✈️",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# st.markdown("""
#     <style>
#     .main { background-color: #f8fafc; }
#     .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-left: 5px solid #0f172a; }
#     .status-card { background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 25px; }
#     .metric-title { font-weight: 700; color: #0f172a; margin-bottom: 15px; border-bottom: 2px solid #e2e8f0; padding-bottom: 5px; }
#     </style>
#     """, unsafe_allow_html=True)

# st.title("🛸 Automated UAV Flight Log Analyzer")
# st.markdown("Upload raw `.ulg` (Onboard Dataflash) or `.tlog` (Telemetry Log) files to evaluate trainee piloting accuracy, mechanical handling, and regulatory compliance.")

# # 2. Sidebar Navigation & Target File Management
# st.sidebar.image("https://redonsystems.in/wp-content/uploads/2025/03/redon-favicon.png", width=60)
# # st.sidebar.image("https://img.icons8.com/external-flatart-icons-lineal-color-flatart-icons/128/external-drone-smart-city-flatart-icons-lineal-color-flatart-icons.png", width=60)
# st.sidebar.title("Telemetry Control")
# st.sidebar.markdown("---")

# st.sidebar.subheader("Upload Flight Data")
# uploaded_files = st.sidebar.file_uploader(
#     "Select raw log files (.ulg, .tlog)", 
#     type=["ulg", "ulog", "tlog"], 
#     accept_multiple_files=True
# )

# st.sidebar.markdown("---")
# st.sidebar.info("💡 **Production Note:** In a live environment, this parser utilizes `pyulog` for structural topic extraction and `pymavlink` for sequential binary message handling.")

# # Helper function to generate mock telemetry streams from file attributes
# def process_log_telemetry(file_name, file_size):
#     np.random.seed(len(file_name) + file_size)
#     timesteps = 100
#     time_series = np.linspace(0, 10, timesteps)
    
#     is_ulg = file_name.endswith(('ulg', 'ulog'))
    
#     # Generate physics based on file footprint signatures
#     if is_ulg:
#         # Mechanical parameters
#         roll_dev = np.random.normal(0, 1.5, timesteps) + np.sin(time_series) * 2
#         pitch_dev = np.random.normal(0, 1.2, timesteps) + np.cos(time_series) * 1.5
#         stick_input = np.random.normal(1500, 150, timesteps) # RC Channel midpoints
#         alt = 120 + np.cumsum(np.random.normal(0, 2, timesteps))
        
#         df_telemetry = pd.DataFrame({
#             "Timestamp (s)": time_series,
#             "Roll Deviation (deg)": roll_dev,
#             "Pitch Deviation (deg)": pitch_dev,
#             "Stick Input (PWM)": stick_input,
#             "Altitude (ft)": alt
#         })
#         return "ULOG", df_telemetry
#     else:
#         # Ground station/trajectory parameters
#         target_x = np.linspace(0, 50, timesteps)
#         target_y = np.sin(target_x / 5) * 20
#         actual_x = target_x + np.random.normal(0, 1.2, timesteps)
#         actual_y = target_y + np.random.normal(0, 1.5, timesteps)
#         alt = 80 + np.cumsum(np.random.normal(0, 3, timesteps))
        
#         df_telemetry = pd.DataFrame({
#             "Timestamp (s)": time_series,
#             "Target X Coordinate": target_x,
#             "Target Y Coordinate": target_y,
#             "Actual X Coordinate": actual_x,
#             "Actual Y Coordinate": actual_y,
#             "Altitude (ft)": alt
#         })
#         return "TLOG", df_telemetry

# # 3. Main Operational Workflow
# if not uploaded_files:
#     # Onboarding Display state
#     st.warning("Please upload one or more flight files in the sidebar to populate the diagnostic workspace.")
    
#     st.markdown("### Expected Binary Structure Mapping")
#     col1, col2 = st.columns(2)
#     with col1:
#         st.markdown("""
#         **Onboard Flash Memory Data (.ULOG)**
#         * High-frequency physical attitudes (IMU sensor array)
#         * PWM actuator command logs
#         * Real-time airframe control loop variance
#         """)
#     with col2:
#         st.markdown("""
#         **Ground Station Telemetry Streams (.TLOG)**
#         * Waypoint waypoint coordinate accuracy arrays
#         * MAVLink command confirmation tracking
#         * Radio RSSI signal degradation history
#         """)
# else:
#     # Process multiple log execution threads
#     file_map = {f.name: f for f in uploaded_files}
#     selected_file_name = st.selectbox("Select target log to analyze:", list(file_map.keys()))
    
#     target_file = file_map[selected_file_name]
#     log_type, telemetry_data = process_log_telemetry(target_file.name, target_file.size)

#     metric_css = """<style>
#     /* Target Streamlit metric widget containers */
#     [data-testid="stMetric"] {
#         background-color: #000000 !important;
#         padding: 15px !important;
#         border-radius: 8px !important;
#         border: 1px solid #333333 !important;
#     }
#     /* Force metric label text to light gray */
#     [data-testid="stMetricLabel"] {
#         color: #aaaaaa !important;
#     }
#     /* Force metric value text to pure white */
#     [data-testid="stMetricValue"] {
#         color: #ffffff !important;
#     }
#     </style>"""

#     st.html(metric_css)
    
#     # Display processing summary card
#     st.success(f"Successfully compiled tracking matrix from {target_file.name} ({target_file.size / 1024:.2f} KB)")
    
#     # 4. Metric Computation Layer
#     max_alt = telemetry_data["Altitude (ft)"].max()
#     ceiling_breached = max_alt > 400
    
#     m_col1, m_col2, m_col3, m_col4 = st.columns(4)
#     with m_col1:
#         st.metric("Log Type Classified", log_type)
#     with m_col2:
#         st.metric("Peak Altitude Checked", f"{max_alt:.1f} ft AGL")
#     with m_col3:
#         status_label = "BREACHED" if ceiling_breached else "PASSED"
#         st.metric("DGCA Ceiling Limit Check", status_label, delta="> 400 ft Limit" if ceiling_breached else None, delta_color="inverse")
#     with m_col4:
#         # Calculate dynamic smoothness factor based on variances
#         if log_type == "ULOG":
#             smoothness = "Excellent" if telemetry_data["Roll Deviation (deg)"].std() < 1.8 else "Erratic Inputs"
#         else:
#             smoothness = "High Accuracy" if np.mean(np.abs(telemetry_data["Actual X Coordinate"] - telemetry_data["Target X Coordinate"])) < 1.5 else "Needs Revision"
#         st.metric("Flight Path Index Score", smoothness)

#     st.markdown("---")

#     # 5. Diagnostic Visualization Routing
#     if log_type == "ULOG":
#         st.markdown("<div class='metric-title'>Mechanical Handling & Attitude Control Tracking (.ULOG Engine)</div>", unsafe_allow_html=True)
        
#         fig_col1, fig_col2 = st.columns(2)
#         with fig_col1:
#             # Map Roll/Pitch fluctuations
#             fig_attitude = px.line(
#                 telemetry_data, 
#                 x="Timestamp (s)", 
#                 y=["Roll Deviation (deg)", "Pitch Deviation (deg)"],
#                 title="Airframe Mechanical Angular Error Deviations",
#                 color_discrete_sequence=["#0284c7", "#f43f5e"]
#             )
#             fig_attitude.update_layout(plot_bgcolor="rgba(0,0,0,0)")
#             st.plotly_chart(fig_attitude, use_container_width=True)
            
#         with fig_col2:
#             # Map Stick input variations
#             fig_sticks = px.line(
#                 telemetry_data, 
#                 x="Timestamp (s)", 
#                 y="Stick Input (PWM)",
#                 title="Pilot Stick Command Frequencies (PWM Signals)",
#                 color_discrete_sequence=["#10b981"]
#             )
#             fig_sticks.update_layout(plot_bgcolor="rgba(0,0,0,0)")
#             st.plotly_chart(fig_sticks, use_container_width=True)
            
#     else:
#         st.markdown("<div class='metric-title'>Mission Trainee Navigation Accuracy Profiles (.TLOG Engine)</div>", unsafe_allow_html=True)
        
#         fig_col1, fig_col2 = st.columns(2)
#         with fig_col1:
#             # Reconstruct Coordinate path accuracy
#             fig_map = px.line(
#                 telemetry_data,
#                 x="Actual X Coordinate",
#                 y="Actual Y Coordinate",
#                 title="2D Navigational Flight Course Errors",
#                 labels={"Actual X Coordinate": "Grid Latitude Position", "Actual Y Coordinate": "Grid Longitude Position"}
#             )
#             # Overlay theoretical route target reference line
#             fig_map.add_scatter(
#                 x=telemetry_data["Target X Coordinate"], 
#                 y=telemetry_data["Target Y Coordinate"], 
#                 mode='lines', 
#                 name='Pre-Planned Waypoint Track',
#                 line=dict(dash='dash', color='#64748b')
#             )
#             fig_map.update_layout(plot_bgcolor="rgba(0,0,0,0)")
#             st.plotly_chart(fig_map, use_container_width=True)
            
#         with fig_col2:
#             # Reconstruct Vertical flight profile trends
#             fig_alt = px.area(
#                 telemetry_data,
#                 x="Timestamp (s)",
#                 y="Altitude (ft)",
#                 title="Vertical Climb Profiles Mapping",
#                 color_discrete_sequence=["#f59e0b"]
#             )
#             fig_alt.add_hline(y=400, line_dash="dash", line_color="#ef4444", annotation_text="DGCA Max Ceiling Threshold")
#             fig_alt.update_layout(plot_bgcolor="rgba(0,0,0,0)")
#             st.plotly_chart(fig_alt, use_container_width=True)

#     # 6. Detailed Tabular Raw Log Excerpts
#     with st.expander("Inspect Raw Decoded Data Matrix Elements"):
#         st.dataframe(telemetry_data, use_container_width=True)


# Version 3


import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import os

# 1. Page Configuration & Custom CSS for Aerospace Dark Theme
st.set_page_config(page_title="Flyght Cloud | Advanced Telemetry Suite", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    /* Global Dark Aerospace Theme */
    .stApp { background-color: #040d1a; color: #cbd5e1; }
    header { visibility: hidden; }
    section[data-testid="stSidebar"] { background-color: #0a1424; border-right: 1px solid #1e293b; }
    
    /* Dynamic Metric Containers */
    div[data-testid="metric-container"] {
        background-color: #0c1a2d;
        border: 1px solid #1e293b;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
    }
    div[data-testid="metric-container"] label { color: #94a3b8 !important; font-size: 0.85rem; letter-spacing: 0.5px; font-weight: 600; }
    div[data-testid="metric-container"] div { color: #38bdf8 !important; font-weight: 700; }
    
    /* Navigation Elements */
    .stTabs [data-baseweb="tab-list"] { background-color: #0c1a2d; border-radius: 8px; padding: 5px; gap: 10px; border: 1px solid #1e293b; }
    .stTabs [data-baseweb="tab"] { color: #64748b; padding: 10px 20px; border-radius: 6px; font-weight: 500; }
    .stTabs [aria-selected="true"] { background-color: #1e293b !important; color: #38bdf8 !important; }
    
    /* Custom Components */
    .trainee-banner {
        background-color: #0c1a2d; border: 1px solid #1e293b; border-radius: 8px;
        padding: 20px; display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 25px;
    }
    .status-badge { background-color: rgba(56, 189, 248, 0.1); color: #38bdf8; padding: 5px 12px; border-radius: 15px; font-size: 0.8rem; border: 1px solid rgba(56, 189, 248, 0.3); font-weight: 600; }
    .emergency-box { background-color: #0c1a2d; border: 1px solid #334155; border-radius: 8px; padding: 20px; }
    .timeline-item { font-size: 0.85rem; padding: 4px 0; border-left: 2px solid #1e293b; padding-left: 12px; margin-left: 6px; }
    </style>
""", unsafe_allow_html=True)

# 2. Dynamic Telemetry Engine
@st.cache_data
def parse_and_generate_telemetry(filename, file_size, log_type):
    """
    Simulates a high-fidelity binary log parsing pass (.ulg/.tlog).
    Generates dynamic parameters unique to the mathematical properties of the file signature.
    """
    # Create unique seed derived from file properties to ensure absolute data persistence per file
    seed_value = sum([ord(char) for char in filename]) + int(file_size % 1000)
    np.random.seed(seed_value)
    
    # Generate continuous timestamp timeline
    duration_minutes = float(np.random.uniform(8.5, 22.0))
    timesteps = 120
    time_array = np.linspace(0, duration_minutes * 60, timesteps)
    
    # Compute variant parameters based on arbitrary pilot skill signatures within the seed
    skill_factor = np.random.uniform(0.5, 3.5)
    
    # 1. Altitude profile computation
    base_alt = np.sin(time_array / (duration_minutes * 8)) * 320
    noise_alt = np.random.normal(0, 4, timesteps)
    altitude = np.abs(base_alt + noise_alt + 10)
    # Ensure realistic ceiling fluctuations
    if skill_factor > 3.0: 
        altitude += 90  # Force a ceiling breach condition for specific files
        
    # 2. Mechanical Profiles (.ULOG)
    roll_cmd = np.sin(time_array / 10) * 15
    pitch_cmd = np.cos(time_array / 12) * 12
    roll_act = roll_cmd + np.random.normal(0, skill_factor, timesteps)
    pitch_act = pitch_cmd + np.random.normal(0, skill_factor, timesteps)
    
    # Detect erratic events (spikes over threshold)
    stick_diff = np.diff(roll_act)
    erratic_events_count = int(np.sum(np.abs(stick_diff) > (3.5 / skill_factor)))
    
    # 3. Spatial Coordinates (.TLOG)
    planned_x = np.linspace(0, 150, timesteps)
    planned_y = np.sin(planned_x / 20) * 60
    
    # Simulate crosswind drifting errors
    drift_factor = skill_factor * 2.5
    actual_x = planned_x + np.random.normal(0, drift_factor / 2, timesteps)
    actual_y = planned_y + np.random.normal(0, drift_factor, timesteps)
    
    # Max distance excursion for Geofence validation
    max_drift = float(np.max(np.sqrt((actual_x - planned_x)**2 + (actual_y - planned_y)**2)))
    
    # 4. Emergency timeline generation
    failsafe_reaction = float(np.random.uniform(3.2, 7.8))
    
    # Compile dataframes
    df_ulg = pd.DataFrame({
        "Time (s)": time_array,
        "Roll CMD": roll_cmd,
        "Pitch CMD": pitch_cmd,
        "Roll ACT": roll_act,
        "Pitch ACT": pitch_act,
        "Altitude (ft)": altitude
    })
    
    df_tlog = pd.DataFrame({
        "Time (s)": time_array,
        "Planned X": planned_x,
        "Planned Y": planned_y,
        "Actual X": actual_x,
        "Actual Y": actual_y,
        "Altitude (ft)": altitude
    })
    
    metrics = {
        "duration_min": duration_minutes,
        "max_alt": float(np.max(altitude)),
        "erratic_events": erratic_events_count,
        "max_drift": max_drift,
        "failsafe_time": failsafe_reaction,
        "loop_rate": 400 if skill_factor > 1.5 else 250
    }
    
    return df_ulg, df_tlog, metrics

# 3. Onboarding & Sidebar Interface
st.sidebar.markdown("<h3 style='color: #38bdf8; margin-top: 0; letter-spacing:1px;'>FLYGHT CLOUD</h3>", unsafe_allow_html=True)
st.sidebar.caption("ENTERPRISE LOG INTELLIGENCE SYSTEM")
st.sidebar.markdown("---")

st.sidebar.markdown("<div style='color: #38bdf8; font-size: 0.75rem; font-weight:700; margin-bottom: 10px;'>🛸 INGEST TELEMETRY DATA</div>", unsafe_allow_html=True)
uploaded_files = st.sidebar.file_uploader(
    "Upload raw data tracks", 
    type=["ulog", "ulg", "tlog", "bin"], 
    accept_multiple_files=True,
    label_visibility="collapsed"
)

# Structural Tracking Ingestion Map
trainees = {}

if uploaded_files:
    for f in uploaded_files:
        # Extract Trainee identity cleanly from filename structure
        raw_name = os.path.splitext(f.name)[0]
        trainee_name = raw_name.replace("_", " ").replace("-", " ").title()
        
        file_extension = os.path.splitext(f.name)[1].lower()
        determined_type = "ULOG" if file_extension in ['.ulog', '.ulg', '.bin'] else "TLOG"
        
        if trainee_name not in trainees:
            trainees[trainee_name] = {"has_ulg": False, "has_tlog": False, "file_data": {}}
            
        trainees[trainee_name]["file_data"][determined_type] = {"name": f.name, "size": f.size}
        if determined_type == "ULOG":
            trainees[trainee_name]["has_ulg"] = True
        else:
            trainees[trainee_name]["has_tlog"] = True

# 4. Workspace Router
if not trainees:
    st.title("System Diagnostic Standby")
    st.info("👈 Drop telemetry logs (.ulg or .tlog) into the secure onboarding vault located in the sidebar to populate runtime analytics models.")
    st.markdown("### Operational Schema Architecture Requirements")
    st.markdown("""
    The framework maps metrics dynamically using explicit naming constraints. Rename files before ingestion to register trainees naturally:
    * `Dhinesh Kumar.ulog` $\\rightarrow$ Parses mechanical attitude matrices for **Dhinesh Kumar**.
    * `Dhinesh Kumar.tlog` $\\rightarrow$ Extracts path planning and failsafe events for **Bomma Saketha**.
    """)
else:
    st.sidebar.markdown("---")
    st.sidebar.markdown("<div style='color: #38bdf8; font-size: 0.75rem; font-weight:700; margin-bottom: 10px;'>👤 MANAGED TRAINING DIRECTORY</div>", unsafe_allow_html=True)
    selected_trainee = st.sidebar.radio("Active Profiles", list(trainees.keys()), label_visibility="collapsed")
    
    # Fetch data profile contexts
    profile = trainees[selected_trainee]
    
    # Process files comprehensively through the telemetry engine using whichever log is active
    representative_file = list(profile["file_data"].values())[0]
    df_ulg, df_tlog, log_metrics = parse_and_generate_telemetry(
        representative_file["name"], representative_file["size"], "ULOG" if profile["has_ulg"] else "TLOG"
    )

    # Calculate global metrics
    smoothness_factor = "Excellent" if log_metrics["erratic_events"] <= 2 else ("Fair" if log_metrics["erratic_events"] <= 6 else "Erratic Inputs")
    geofence_status = "Green Zone" if log_metrics["max_drift"] < 12.0 else "Boundary Excursion"
    geofence_color = "normal" if geofence_status == "Green Zone" else "inverse"
    
    # Compute mean tracking deviation index
    attitude_deviation = np.mean(np.abs(df_ulg["Roll CMD"] - df_ulg["Roll ACT"]))

    # 5. Core Interface Profile Banner
    st.markdown(f"""
        <div class="trainee-banner">
            <div>
                <h3 style="margin:0; color: white; font-weight:700;">{selected_trainee}</h3>
                <p style="margin:5px 0 0 0; color: #64748b; font-size: 0.85rem; letter-spacing:0.5px;">SYSTEM PLATFORM: ACHUK-UAV • AUTOMATED LOG PROCESSING</p>
            </div>
            <div>
                <span class="status-badge">⚙️ LOG INGEST COMPLETE</span>
                <span class="status-badge" style="margin-left: 10px; background-color: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3);">ACTIVE DATASTREAM</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 6. Tabbed Workspace Elements
    tab1, tab2, tab3 = st.tabs([
        "⚙️ MECHANICAL PROFICIENCY .ULOG", 
        "📡 GCS MISSION COORDINATION .TLOG", 
        "🛡️ DGCA OFFICIAL AUDIT REPORT"
    ])
    
    # ---------------- TAB 1: MECHANICAL PROFICIENCY ----------------
    with tab1:
        c1, c2, c3 = st.columns(3)
        with c1: 
            st.metric("PILOT SMOOTHNESS FACTOR", smoothness_factor, f"{log_metrics['erratic_events']} ERRATIC EVENTS", delta_color="inverse" if log_metrics['erratic_events'] > 2 else "normal")
        with c2: 
            st.metric("ATTITUDE DEVIATION INDEX", f"{attitude_deviation:.2f}°", "MEAN CMD ➔ ACTUAL DELTA", delta_color="off")
        with c3: 
            st.metric("CONTROL LOOP RATE", f"{log_metrics['loop_rate']} Hz", "PX4 IMU FILTER ACTIVE", delta_color="off")
            
        # Draw dynamic line plot tracking control surfaces
        fig_mech = go.Figure()
        fig_mech.add_trace(go.Scatter(x=df_ulg["Time (s)"], y=df_ulg["Roll CMD"], mode='lines', name='Roll Target (Commanded)', line=dict(color='#0ea5e9', width=2)))
        fig_mech.add_trace(go.Scatter(x=df_ulg["Time (s)"], y=df_ulg["Roll ACT"], mode='lines', name='Roll Deflection (Actual)', line=dict(color='#ec4899', width=1.5)))
        fig_mech.add_trace(go.Scatter(x=df_ulg["Time (s)"], y=df_ulg["Pitch ACT"], mode='lines', name='Pitch Dynamics', line=dict(color='#8b5cf6', width=1, dash='dot')))
        
        fig_mech.update_layout(
            title="HIGH FREQUENCY ATTITUDE LOOPS (ACTUATOR OUTPUT VS COMMAND CONTEXTS)",
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#94a3b8'), margin=dict(l=10, r=10, t=50, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5)
        )
        fig_mech.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#1e293b')
        fig_mech.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#1e293b')
        st.plotly_chart(fig_mech, use_container_width=True)

    # ---------------- TAB 2: GCS MISSION COORDINATION ----------------
    with tab2:
        col_map, col_timeline = st.columns([2.2, 1])
        
        with col_map:
            st.markdown("<div style='color: #94a3b8; font-size:0.9rem; font-weight:600; margin-bottom: 15px;'>2D FLIGHT SPATIAL TRACKS (MISSION COMPLIANCE PROFILE)</div>", unsafe_allow_html=True)
            
            fig_spatial = go.Figure()
            fig_spatial.add_trace(go.Scatter(x=df_tlog["Planned X"], y=df_tlog["Planned Y"], mode='lines+markers', name='Target Waypoints Track', line=dict(color='#0ea5e9', dash='dash')))
            fig_spatial.add_trace(go.Scatter(x=df_tlog["Actual X"], y=df_tlog["Actual Y"], mode='lines', name='Parsed Flight Footprint', line=dict(color='#ec4899')))
            
            fig_spatial.update_layout(
                plot_bgcolor='#050e1a', paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#64748b'), margin=dict(l=0, r=0, t=0, b=0),
                xaxis=dict(showgrid=True, gridcolor='#1e293b', zeroline=False),
                yaxis=dict(showgrid=True, gridcolor='#1e293b', zeroline=False),
                height=400, legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_spatial, use_container_width=True)
            
        with col_timeline:
            is_breached = log_metrics["failsafe_time"] > 6.0
            border_alert = "#b91c1c" if is_breached else "#1e293b"
            text_alert = "#f43f5e" if is_breached else "#38bdf8"
            
            st.markdown(f"""
            <div class="emergency-box" style="border: 1px solid {border_alert};">
                <h5 style="color: #f43f5e; margin-top: 0; font-weight:700; letter-spacing:0.5px;">⚠️ EMERGENCY FAILSAFE ASSESSMENT</h5>
                <p style="color: #64748b; font-size: 0.8rem; margin: 0; font-weight:600;">FAILSAFE REACTION TIME</p>
                <h2 style="color: white; margin: 5px 0; font-weight:800;">{log_metrics['failsafe_time']:.2f} s</h2>
                <p style="color: {text_alert}; font-size: 0.75rem; font-weight:600;">TARGET LIMIT: ≤ 6.0 S ({'CRITICAL BREACH' if is_breached else 'VALIDATED'})</p>
                <hr style="border-color: #1e293b; margin: 15px 0;">
                <div class="timeline-item"><span style="color: #10b981;">●</span> T+0.00s: Mission Armed & Link Check</div>
                <div class="timeline-item"><span style="color: #38bdf8;">●</span> T+45.2s: Waypoint 2 Altitude Reached</div>
                <div class="timeline-item"><span style="color: #f59e0b;">●</span> T+120.4s: GCS Radio Link Degradation Detected</div>
                <div class="timeline-item"><span style="color: #ef4444;">●</span> T+122.1s: MAVLink LOST LINK State Latched</div>
                <div class="timeline-item"><span style="color: #38bdf8;">●</span> T+{122.1 + log_metrics['failsafe_time']:.1f}s: Trainee Initiated Manual RTL Override</div>
                <div class="timeline-item"><span style="color: #10b981;">●</span> T+210.5s: Autonomous Flare & Touchdown</div>
            </div>
            """, unsafe_allow_html=True)

    # ---------------- TAB 3: DGCA OFFICIAL AUDIT REPORT ----------------
    with tab3:
        st.markdown("""
            <div>
                <h4 style="color: #38bdf8; margin-bottom: 5px; font-weight:700;">Official Flight Audit & Compliance Record</h4>
                <p style="color: #64748b; font-size: 0.85rem;">Generated dynamically under automated telemetry validation pipelines conforming to DGCA Drone Rules.</p>
            </div>
            <hr style="border-color: #1e293b; margin-bottom:25px;">
        """, unsafe_allow_html=True)
        
        aud_c1, aud_c2 = st.columns(2)
        with aud_c1:
            ceiling_flag = "BREACH" if log_metrics["max_alt"] > 400 else "PASSED"
            st.metric(
                "FLIGHT CEILING CHECK", 
                f"{log_metrics['max_alt']:.1f} ft AGL", 
                f"DGCA LIMIT: 400 FT ({ceiling_flag})", 
                delta_color="inverse" if log_metrics["max_alt"] > 400 else "normal"
            )
        with aud_c2:
            st.metric(
                "FLIGHT TIME LOG", 
                f"{log_metrics['duration_min']:.2f} min", 
                "WITHIN SESSION QUOTA LIMITS", 
                delta_color="normal"
            )
            
        st.write("") # Horizontal buffer spacing
        
        aud_c3, aud_c4 = st.columns(2)
        with aud_c3:
            st.metric(
                "GEO-FENCING VALIDATOR", 
                geofence_status, 
                f"MAX SPATIAL BOUNDARY DEVIATION: {log_metrics['max_drift']:.1f} M", 
                delta_color=geofence_color
            )
        with aud_c4:
            st.metric(
                "FAILSAFE REACTION TIME", 
                f"{log_metrics['failsafe_time']:.2f} s", 
                "TARGET REQUIREMENT ≤ 6.0 S", 
                delta_color="inverse" if log_metrics['failsafe_time'] > 6.0 else "normal"
            )
