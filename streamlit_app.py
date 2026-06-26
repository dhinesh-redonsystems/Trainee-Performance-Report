# import streamlit as st
# import pandas as pd
# import json
# import plotly.express as px
# from google import genai

# # --- CONFIGURATION ---
# # Best practice for Streamlit: Don't hardcode API keys. 
# # We'll set a placeholder here, but you can use st.secrets in production.
# try:
#     API_KEY = st.secrets["GEMINI_API_KEY"]
# except KeyError:
#     st.error("API Key not found! Please set GEMINI_API_KEY in Streamlit secrets.")
#     st.stop()
# st.set_page_config(
#     page_title="Achuk Flight Analytics",
#     page_icon="🚁",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# # --- HELPER FUNCTIONS ---
# def calculate_score(events, comms):
#     """Calculates the deterministic score based on logs."""
#     scores = {"Navigation": 15, "Tracking": 15, "Communication": 5, "Total": 100}
    
#     # Navigation Deductions
#     nav_warnings = len(events[(events['Module'] == 'NavSystem') & (events['Severity/Status'] == 'WARNING')])
#     scores["Navigation"] -= (nav_warnings * 1) 

#     # Tracking Deductions
#     track_losses = len(events[events['Event_Description'] == 'Track Lost'])
#     scores["Tracking"] -= (track_losses * 2)

#     # Comm Deductions
#     if len(comms[comms['Latency_ms'] > 30]) > 0 or comms['Dropped_Frames'].sum() > 0:
#         scores["Communication"] -= 1

#     # Calculate final (Simplified for dashboard)
#     deductions = (15 - scores["Navigation"]) + (15 - scores["Tracking"]) + (5 - scores["Communication"])
#     scores["Total"] = 100 - deductions
    
#     return scores

# # --- SIDEBAR UI ---
# st.sidebar.title("🚁 Redon Systems")
# st.sidebar.subheader("Project Achuk Dashboard")
# st.sidebar.markdown("---")
# st.sidebar.write("**Upload Mission Data:**")

# file_config = st.sidebar.file_uploader("Upload config.json", type=['json'])
# file_events = st.sidebar.file_uploader("Upload events.csv", type=['csv'])
# file_telem = st.sidebar.file_uploader("Upload telemetry.csv", type=['csv'])
# file_comms = st.sidebar.file_uploader("Upload comms.csv", type=['csv'])

# # --- MAIN DASHBOARD UI ---
# st.title("Mission Analysis & CV Tracking Overview")

# # Only render the dashboard if all files are uploaded
# if file_config and file_events and file_telem and file_comms:
    
#     # Load Data
#     config = json.load(file_config)
#     df_events = pd.read_csv(file_events)
#     df_telem = pd.read_csv(file_telem)
#     df_comms = pd.read_csv(file_comms)
    
#     scores = calculate_score(df_events, df_comms)

#     # --- SECTION 1: HEADER & KPIs ---
#     st.markdown(f"### Mission: `{config.get('MissionID', 'N/A')}` | Trainee: `{config.get('Trainee', 'N/A')}`")
    
#     col1, col2, col3, col4 = st.columns(4)
#     col1.metric("Overall Score", f"{scores['Total']}/100", f"{'PASS' if scores['Total'] >= 80 else 'FAIL'}")
#     col2.metric("CV Tracking Score", f"{scores['Tracking']}/15")
#     col3.metric("Avg Telemetry Speed", f"{df_telem['Speed'].mean():.2f} m/s")
#     col4.metric("Avg Video Latency", f"{df_comms[df_comms['Type'] == 'Video']['Latency_ms'].mean():.1f} ms")

#     st.markdown("---")

#     # --- SECTION 2: INTERACTIVE CHARTS ---
#     st.subheader("📊 Telemetry & Payload Analytics")
#     chart_col1, chart_col2 = st.columns(2)

#     with chart_col1:
#         st.write("**Target Position Error vs Course Deviation**")
#         # Visualizing tracking accuracy over time
#         fig_tracking = px.line(df_telem, x="Timestamp", y=["Target_Pos_Err", "Course_Deviation"], 
#                                markers=True, title="Tracking & Navigation Deviations")
#         st.plotly_chart(fig_tracking, use_container_width=True)

#     with chart_col2:
#         st.write("**Communications Latency**")
#         # Visualizing network stability
#         fig_comms = px.bar(df_comms, x="Timestamp", y="Latency_ms", color="Type", 
#                            title="Link Latency by Type (Video vs Telemetry)")
#         st.plotly_chart(fig_comms, use_container_width=True)

#     st.markdown("---")

#     # --- SECTION 3: LLM GENERATED INSIGHTS ---
#     st.subheader("🧠 AI Post-Flight Narrative")
#     st.write("Generate a qualitative analysis of the computer vision tracking and flight execution using Gemini.")
    
#     if st.button("Generate AI Insights"):
#         with st.spinner("Analyzing telemetry and CV events..."):
#             try:
#                 # Construct the prompt
#                 prompt = f"""
#                 You are a senior flight simulation analyzer evaluating a YOLO_DeepSORT tracking payload.
#                 Analyze the following data and provide a concise, 3-paragraph executive summary focusing on:
#                 1. Overall flight and navigation execution.
#                 2. Computer Vision tracking performance (mention specific target errors or track losses).
#                 3. Network and safety health.
                
#                 CONFIG: {json.dumps(config)}
#                 SCORES: {json.dumps(scores)}
#                 EVENTS: {df_events.to_string(index=False)}
#                 """
                
#                 # Call Gemini
#                 client = genai.Client(api_key=API_KEY)
#                 response = client.models.generate_content(
#                     model='gemini-2.5-flash',
#                     contents=prompt,
#                 )
                
#                 st.success("Analysis Complete!")
#                 st.write(response.text)
                
#             except Exception as e:
#                 st.error(f"Failed to generate insights: {e}")

# else:
#     st.info("👈 Please upload all four simulation files in the sidebar to generate the dashboard.")


import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pymavlink import mavutil
import tempfile
import os

# --- SYSTEM CONFIGURATION & THEMING ---
st.set_page_config(page_title="Achuk Navigation Analytics", layout="wide", page_icon="📊")

st.markdown("""
<style>
    body { background-color: #0d1117; color: #c9d1d9; }
    .stApp { background-color: #0d1117; }
    .insight-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 15px;
        height: 100%;
    }
    .insight-title { font-size: 0.85rem; color: #8b949e; text-transform: uppercase; font-weight: bold; letter-spacing: 0.5px; }
    .insight-value { font-size: 1.8rem; font-weight: bold; color: #58a6ff; margin: 10px 0; }
    .insight-sub { font-size: 0.8rem; color: #8b949e; }
    .highlight-green { color: #3fb950; font-weight: bold; }
    .highlight-red { color: #f85149; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 100% DYNAMIC TELEMETRY PARSER ---
@st.cache_data(show_spinner="Extracting raw MAVLink telemetry...")
def parse_analytical_telemetry(file_bytes, filename):
    """
    Strictly extracts data from the uploaded .tlog. Zero simulated fallbacks.
    Synchronizes MAVLink packets using timestamps.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".tlog") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    mlog = mavutil.mavlink_connection(tmp_path)
    records = []
    
    # State tracking variables for asynchronous packets
    current_mode = "UNKNOWN"
    current_alt = 0.0
    current_nav_roll = 0.0
    current_nav_pitch = 0.0
    start_time = None
    
    while True:
        m = mlog.recv_match(blocking=False)
        if m is None:
            break
            
        m_type = m.get_type()
        timestamp = getattr(m, '_timestamp', None)
        
        # Initialize master clock on first valid timestamp
        if timestamp is not None and start_time is None:
            start_time = timestamp

        # 1. State Transitions (Modes via Heartbeat)
        if m_type == 'HEARTBEAT':
            try: 
                mode_str = mlog.flightmode
            except AttributeError: 
                mode_str = f"MODE_{m.custom_mode}"
            if mode_str: 
                current_mode = mode_str.upper()

        # 2. Altitude Tracking (Handles both GPS and SITL Local formats)
        elif m_type == 'GLOBAL_POSITION_INT':
            current_alt = m.relative_alt / 1000.0
        elif m_type == 'LOCAL_POSITION_NED':
            current_alt = -m.z

        # 3. Target Navigation Commands
        elif m_type == 'NAV_CONTROLLER_OUTPUT':
            current_nav_roll = m.nav_roll
            current_nav_pitch = m.nav_pitch

        # 4. Actual Attitude (Acts as the recording trigger)
        elif m_type == 'ATTITUDE':
            if timestamp is None: 
                continue
            
            roll = m.roll * 57.2958
            pitch = m.pitch * 57.2958
            
            # Simple combined absolute error tracker
            tracking_error = abs(current_nav_roll - roll) + abs(current_nav_pitch - pitch)

            records.append({
                'time_sec': timestamp - start_time,
                'alt': current_alt,
                'roll': roll,
                'pitch': pitch,
                'nav_roll': current_nav_roll,
                'nav_pitch': current_nav_pitch,
                'mode': current_mode,
                'tracking_error': tracking_error
            })

    os.remove(tmp_path)
    return pd.DataFrame(records)

# --- METRIC CALCULATION ENGINE ---
def calculate_mode_segments(df):
    """Calculates start, end, and duration of every dynamic flight mode trigger."""
    if df.empty:
        return pd.DataFrame()
        
    df['mode_shift'] = df['mode'] != df['mode'].shift()
    df['segment_id'] = df['mode_shift'].cumsum()
    
    segments = df.groupby(['segment_id', 'mode']).agg(
        start_time=('time_sec', 'min'),
        end_time=('time_sec', 'max'),
        avg_alt=('alt', 'mean'),
        max_error=('tracking_error', 'max')
    ).reset_index()
    
    segments['duration'] = segments['end_time'] - segments['start_time']
    return segments

# --- MAIN UI ---
st.markdown("## 📊 DYNAMIC TELEMETRY & NAVIGATION TRACKING")
st.markdown("`SOURCE: DIRECT MAVLINK EXTRACTION` • `ATTITUDE LATENCY` • `STATE TRANSITIONS`")
st.markdown("---")

with st.sidebar:
    st.header("Log Ingestion")
    uploaded_files = st.file_uploader("Upload Trainee Logs (.tlog)", accept_multiple_files=True, type=['tlog'])

if uploaded_files:
    trainee_db = {}
    for file in uploaded_files:
        profile_name = file.name.split('.')[0].replace('_', ' ').upper()
        df_parsed = parse_analytical_telemetry(file.getvalue(), file.name)
        if not df_parsed.empty:
            trainee_db[profile_name] = df_parsed

    if not trainee_db:
        st.error("Uploaded files did not contain valid ATTITUDE or HEARTBEAT telemetry packets.")
        st.stop()

    target_profile = st.selectbox("🎯 Select Trainee Log Profile", list(trainee_db.keys()))
    df = trainee_db[target_profile]
    
    segments_df = calculate_mode_segments(df)
    
    # Dynamically find tracked/guided modes (Offboard, Guided, Auto)
    automated_modes = ['OFFBOARD', 'GUIDED', 'AUTO']
    tracked_segments = segments_df[segments_df['mode'].isin(automated_modes)]
    
    track_count = len(tracked_segments)
    total_track_time = tracked_segments['duration'].sum() if not tracked_segments.empty else 0
    peak_nav_error = df['tracking_error'].max() if not df.empty else 0
    avg_alt = df['alt'].mean() if not df.empty else 0

    # --- ROW 1: MISSION INSIGHTS ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class='insight-card'>
            <div class='insight-title'>Guided/Offboard Triggers</div>
            <div class='insight-value'>{track_count} <span style='font-size:1rem;color:#8b949e;'>Engagements</span></div>
            <div class='insight-sub'>Total Track Time: <span class='highlight-green'>{total_track_time:.1f}s</span></div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class='insight-card'>
            <div class='insight-title'>Peak Tracking Deviation</div>
            <div class='insight-value'>{peak_nav_error:.2f}°</div>
            <div class='insight-sub'>Max error across mission</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class='insight-card'>
            <div class='insight-title'>Mission Average Altitude</div>
            <div class='insight-value'>{avg_alt:.1f} m</div>
            <div class='insight-sub'>Relative to home origin</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class='insight-card'>
            <div class='insight-title'>Data Points Extracted</div>
            <div class='insight-value'>{len(df)}</div>
            <div class='insight-sub'>Valid Attitude Packets</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # --- ROW 2: FLIGHT MODE STATE TIMELINE ---
    st.subheader("Dynamic Flight Phase Transitions")
    st.markdown("Exact boundaries showing when firmware mode transitions occurred.")
    
    fig_timeline = px.timeline(
        segments_df, x_start="start_time", x_end="end_time", y="mode", color="mode",
        hover_data={"duration": ':.1f', "avg_alt": ':.1f'}
    )
    
    fig_timeline.layout.xaxis.type = 'linear'
    for d in fig_timeline.data:
        filt = segments_df['mode'] == d.name
        d.x = segments_df[filt]['duration']
        d.base = segments_df[filt]['start_time']

    fig_timeline.update_layout(
        paper_bgcolor='#161b22', plot_bgcolor='#161b22', font_color='#c9d1d9',
        xaxis=dict(title="Mission Time (Seconds)", gridcolor='#30363d'),
        yaxis=dict(title="Active Flight Mode"),
        height=280, margin=dict(l=0, r=0, t=30, b=0), showlegend=False
    )
    st.plotly_chart(fig_timeline, width='stretch')

    # --- ROW 3: NAVIGATION COMMAND VS ACTUAL ---
    st.markdown("---")
    st.subheader("Target Navigation vs. Actual Attitude")
    st.markdown("Evaluates response latency and overshoot based on `NAV_CONTROLLER_OUTPUT` streams.")

    axis_view = st.radio("Select Analysis Vector", ["Roll Tracking", "Pitch Tracking", "Both Axes"], horizontal=True)

    fig_nav = go.Figure()

    if axis_view in ["Roll Tracking", "Both Axes"]:
        fig_nav.add_trace(go.Scatter(x=df['time_sec'], y=df['nav_roll'], name="Target Roll (Command)", line=dict(color='#3fb950', width=2, dash='dot')))
        fig_nav.add_trace(go.Scatter(x=df['time_sec'], y=df['roll'], name="Actual Roll", line=dict(color='#58a6ff', width=2)))

    if axis_view in ["Pitch Tracking", "Both Axes"]:
        fig_nav.add_trace(go.Scatter(x=df['time_sec'], y=df['nav_pitch'], name="Target Pitch (Command)", line=dict(color='#d29922', width=2, dash='dot')))
        fig_nav.add_trace(go.Scatter(x=df['time_sec'], y=df['pitch'], name="Actual Pitch", line=dict(color='#ff7b72', width=2)))

    # Automatically highlight sections where the drone was in automated tracking modes
    for idx, row in tracked_segments.iterrows():
        fig_nav.add_vrect(
            x0=row['start_time'], x1=row['end_time'],
            fillcolor="#a371f7", opacity=0.1, layer="below", line_width=0,
            annotation_text=f"{row['mode']} ACTIVE", annotation_position="top left",
            annotation_font=dict(color="#a371f7", size=10)
        )

    fig_nav.update_layout(
        paper_bgcolor='#161b22', plot_bgcolor='#161b22', font_color='#c9d1d9',
        xaxis=dict(title="Mission Time (Seconds)", gridcolor='#30363d'),
        yaxis=dict(title="Degrees", gridcolor='#30363d'),
        height=450, margin=dict(l=0, r=0, t=30, b=0), hovermode="x unified"
    )
    st.plotly_chart(fig_nav, width='stretch')

    # --- ROW 4: DATA TABLE INSIGHTS ---
    st.markdown("---")
    st.subheader("Raw Phase Diagnostics")
    st.dataframe(
        segments_df[['mode', 'start_time', 'end_time', 'duration', 'max_error', 'avg_alt']].style.format({
            'start_time': '{:.1f}s', 'end_time': '{:.1f}s', 
            'duration': '{:.1f}s', 'max_error': '{:.2f}°', 'avg_alt': '{:.1f}m'
        }),
        width='stretch',
        hide_index=True
    )

else:
    st.info("Awaiting telemetry logs. Please upload raw `.tlog` files to map the dynamic tracking vectors.")
