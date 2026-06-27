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

import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Page Configuration & Theme Styling
st.set_page_config(
    page_title="AeroTrain | Drone Pilot Performance & RPC Tracking",
    page_icon="🛸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for an aerospace-inspired look (Slate/Blue theme)
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-left: 5px solid #0284c7; }
    .report-box { background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px; }
    .section-header { color: #0f172a; font-weight: 700; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# 2. Mock Data Generation (DGCA & Test Pilot Context)
@st.cache_data
def load_mock_data():
    data = [
        {"Trainee ID": "TR-001", "Name": "Amit Sharma", "Program": "DGCA 5-Day RPC", "Location": "Bengaluru, India", "Status": "Certified", "Flight Hours": 12.5, "Take-offs": 45, "Landings": 45, "Test Card Dev": 92, "Test Exec": 88, "Data Rep": 90, "Airspace": 95, "DGCA Regs": 94, "Emergency": 100},
        {"Trainee ID": "TR-002", "Name": "Vikram Malhotra", "Program": "Specialized SWITCH UAV", "Location": "Pune, India", "Status": "In-Progress", "Flight Hours": 28.0, "Take-offs": 62, "Landings": 60, "Test Card Dev": 85, "Test Exec": 80, "Data Rep": 78, "Airspace": 88, "DGCA Regs": 85, "Emergency": 90},
        {"Trainee ID": "TR-003", "Name": "Captain Priya Nair", "Program": "Advanced Test-Pilot", "Location": "NTPS, USA", "Status": "Certified", "Flight Hours": 45.2, "Take-offs": 110, "Landings": 110, "Test Card Dev": 96, "Test Exec": 95, "Data Rep": 98, "Airspace": 98, "DGCA Regs": 96, "Emergency": 98},
        {"Trainee ID": "TR-004", "Name": "Rohan Verma", "Program": "DGCA 5-Day RPC", "Location": "Delhi NCR, India", "Status": "Action Required", "Flight Hours": 4.2, "Take-offs": 15, "Landings": 12, "Test Card Dev": 60, "Test Exec": 55, "Data Rep": 62, "Airspace": 72, "DGCA Regs": 68, "Emergency": 50},
        {"Trainee ID": "TR-005", "Name": "Ananya Joshi", "Program": "Specialized SWITCH UAV", "Location": "Bengaluru, India", "Status": "In-Progress", "Flight Hours": 18.5, "Take-offs": 38, "Landings": 38, "Test Card Dev": 78, "Test Exec": 82, "Data Rep": 80, "Airspace": 84, "DGCA Regs": 82, "Emergency": 85},
        {"Trainee ID": "TR-006", "Name": "Suresh Kumar", "Program": "DGCA 5-Day RPC", "Location": "Pune, India", "Status": "Certified", "Flight Hours": 11.8, "Take-offs": 42, "Landings": 42, "Test Card Dev": 88, "Test Exec": 86, "Data Rep": 85, "Airspace": 90, "DGCA Regs": 92, "Emergency": 95}
    ]
    return pd.DataFrame(data)

df = load_mock_data()

# 3. Sidebar Navigation & Global Filters
st.sidebar.image("https://img.icons8.com/external-flatart-icons-lineal-color-flatart-icons/128/external-drone-smart-city-flatart-icons-lineal-color-flatart-icons.png", width=70)
st.sidebar.title("AeroTrain Dashboard")
st.sidebar.caption("DGCA RPC & Advanced Test Flight Operations")
st.sidebar.markdown("---")

app_mode = st.sidebar.radio("Navigate to:", ["Dashboard Overview", "Trainee Performance Reports"])

# 4. Mode A: Dashboard Overview
if app_mode == "Dashboard Overview":
    st.title("🚁 Drone Training Operations Overview")
    st.markdown("Real-time operational tracking of active Remote Pilot Certificate (RPC) classes and defense flight-test groups.")
    
    # KPI Row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Active Trainees", value=len(df))
    with col2:
        st.metric(label="Total Logged Flight Hours", value=f"{df['Flight Hours'].sum():.1f} hrs")
    with col3:
        pass_rate = (len(df[df["Status"] == "Certified"]) / len(df)) * 100
        st.metric(label="Certification Pass Rate", value=f"{pass_rate:.0f}%")
    with col4:
        st.metric(label="Active Locations", value=df["Location"].nunique())
        
    st.markdown("### Analytics & Distribution")
    chart_col1, chart_col2 = st.columns([2, 1])
    
    with chart_col1:
        # Chart: Flight Hours by Program
        fig_hours = px.bar(
            df, 
            x="Program", 
            y="Flight Hours", 
            color="Program",
            title="Flight Hours Logged by Training Track",
            color_discrete_sequence=px.colors.qualitative.G10
        )
        fig_hours.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_hours, use_container_width=True)
        
    with chart_col2:
        # Chart: Trainee Status Breakup
        fig_status = px.pie(
            df, 
            names="Status", 
            title="Certification Readiness Status",
            hole=0.4,
            color_discrete_map={"Certified": "#10B981", "In-Progress": "#3B82F6", "Action Required": "#EF4444"}
        )
    
        st.plotly_chart(fig_status, use_container_width=True)

    # Searchable Master Roster
    st.markdown("### 📋 Master Trainee Roster")
    
    # Filter Controls
    f_col1, f_col2 = st.columns(2)
    with f_col1:
        search_query = st.text_input("🔍 Search trainee by name:", "")
    with f_col2:
        selected_program = st.selectbox("Filter by Program Type:", ["All Programs"] + list(df["Program"].unique()))
        
    # Apply filters
    filtered_df = df.copy()
    if search_query:
        filtered_df = filtered_df[filtered_df["Name"].str.contains(search_query, case=False)]
    if selected_program != "All Programs":
        filtered_df = filtered_df[filtered_df["Program"] == selected_program]
        
    st.dataframe(
        filtered_df[["Trainee ID", "Name", "Program", "Location", "Status", "Flight Hours"]], 
        use_container_width=True,
        hide_index=True
    )

# 5. Mode B: Trainee Performance Reports (Detailed View)
else:
    st.title("📋 Individual Trainee Competency Reports")
    st.markdown("Access comprehensive automated flight metrics, flight-card execution histories, and regulatory evaluations.")
    
    # Trainee Selector Dropdown
    trainee_options = {f"{row['Trainee ID']} - {row['Name']}": row['Trainee ID'] for _, row in df.iterrows()}
    selected_trainee_label = st.selectbox("Select Trainee Profile to View:", list(trainee_options.keys()))
    trainee_id = trainee_options[selected_trainee_label]
    
    # Extract specific trainee details
    t_data = df[df["Trainee ID"] == trainee_id].iloc[0]
    
    # Profile Header Card
    st.markdown(f"""
    <div style="background-color: #0f172a; padding: 20px; border-radius: 10px; color: white; margin-bottom: 25px;">
        <h2 style='margin: 0; color: #38bdf8;'>{t_data['Name']}</h2>
        <p style='margin: 5px 0 0 0; color: #cbd5e1;'>
            <strong>ID:</strong> {t_data['Trainee ID']} | 
            <strong>Track:</strong> {t_data['Program']} | 
            <strong>Base:</strong> {t_data['Location']} | 
            <strong>Status:</strong> {t_data['Status']}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick action button toolbar
    action_col1, action_col2, _ = st.columns([1, 1, 3])
    with action_col1:
        if st.button("🔄 Sync Telemetry / SITL Logs", type="secondary", use_container_width=True):
            st.toast("Autopilot telemetry ecosystem synced successfully!", icon="🛰️")
    with action_col2:
        # Mock download feature
        report_txt = f"Performance Report for {t_data['Name']}\nTrack: {t_data['Program']}\nHours Logged: {t_data['Flight Hours']}"
        st.download_button("📥 Export PDF Report", data=report_txt, file_name=f"{t_data['Trainee ID']}_report.txt", mime="text/plain", use_container_width=True)

    st.markdown("---")

    # Section A: Automated Flight Logs
    st.markdown("<div class='section-header'>Section A: Flight Logs (Automated Autopilot Eco-System)</div>", unsafe_allow_html=True)
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        st.metric("Total Flight Hours", f"{t_data['Flight Hours']} hrs")
    with f_col2:
        st.metric("Log Take-offs", f"{t_data['Take-offs']} flights")
    with f_col3:
        st.metric("Log Landings", f"{t_data['Landings']} flights")
        
    # Section B: System Testing & Competency
    st.markdown("<div class='section-header'>Section B: Flight-Test Execution & Competency</div>", unsafe_allow_html=True)
    
    b_col1, b_col2, b_col3 = st.columns(3)
    with b_col1:
        st.markdown(f"**Test Card Development** ({t_data['Test Card Dev']}/100)")
        st.progress(t_data['Test Card Dev'] / 100)
    with b_col2:
        st.markdown(f"**Test Execution Matrix** ({t_data['Test Exec']}/100)")
        st.progress(t_data['Test Exec'] / 100)
    with b_col3:
        st.markdown(f"**Data Reporting & Telemetry Logging** ({t_data['Data Rep']}/100)")
        st.progress(t_data['Data Rep'] / 100)

    # Section C: Theory & DGCA Regulations
    st.markdown("<div class='section-header'>Section C: Theory & Regulatory Assessments</div>", unsafe_allow_html=True)
    
    c_col1, c_col2, c_col3 = st.columns(3)
    with c_col1:
        st.markdown(
            f"<div class='report-box'><p style='margin:0;color:#64748b;'>Airspace Rules Mapping</p><h2 style='margin:0;color:#0284c7;'>{t_data['Airspace']}%</h2></div>", 
            unsafe_allow_html=True
        )
    with c_col2:
        st.markdown(
            f"<div class='report-box'><p style='margin:0;color:#64748b;'>DGCA Regulations Compliance</p><h2 style='margin:0;color:#0284c7;'>{t_data['DGCA Regs']}%</h2></div>", 
            unsafe_allow_html=True
        )
    with c_col3:
        # Highlight emergency procedures check visually
        color_alert = "#10B981" if t_data['Emergency'] >= 85 else "#EF4444"
        st.markdown(
            f"<div class='report-box'><p style='margin:0;color:#64748b;'>Emergency Handling Rating</p><h2 style='margin:0;color:{color_alert};'>{t_data['Emergency']}%</h2></div>", 
            unsafe_allow_html=True
        )
