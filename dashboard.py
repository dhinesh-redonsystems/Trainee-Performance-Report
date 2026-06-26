import streamlit as st
import pandas as pd
import json
import plotly.express as px
from google import genai

# --- CONFIGURATION ---
# Best practice for Streamlit: Don't hardcode API keys. 
# We'll set a placeholder here, but you can use st.secrets in production.
API_KEY = "Gemini_API_Key"

st.set_page_config(
    page_title="Achuk Flight Analytics",
    page_icon="🚁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- HELPER FUNCTIONS ---
def calculate_score(events, comms):
    """Calculates the deterministic score based on logs."""
    scores = {"Navigation": 15, "Tracking": 15, "Communication": 5, "Total": 100}
    
    # Navigation Deductions
    nav_warnings = len(events[(events['Module'] == 'NavSystem') & (events['Severity/Status'] == 'WARNING')])
    scores["Navigation"] -= (nav_warnings * 1) 

    # Tracking Deductions
    track_losses = len(events[events['Event_Description'] == 'Track Lost'])
    scores["Tracking"] -= (track_losses * 2)

    # Comm Deductions
    if len(comms[comms['Latency_ms'] > 30]) > 0 or comms['Dropped_Frames'].sum() > 0:
        scores["Communication"] -= 1

    # Calculate final (Simplified for dashboard)
    deductions = (15 - scores["Navigation"]) + (15 - scores["Tracking"]) + (5 - scores["Communication"])
    scores["Total"] = 100 - deductions
    
    return scores

# --- SIDEBAR UI ---
st.sidebar.title("🚁 Redon Systems")
st.sidebar.subheader("Project Achuk Dashboard")
st.sidebar.markdown("---")
st.sidebar.write("**Upload Mission Data:**")

file_config = st.sidebar.file_uploader("Upload config.json", type=['json'])
file_events = st.sidebar.file_uploader("Upload events.csv", type=['csv'])
file_telem = st.sidebar.file_uploader("Upload telemetry.csv", type=['csv'])
file_comms = st.sidebar.file_uploader("Upload comms.csv", type=['csv'])

# --- MAIN DASHBOARD UI ---
st.title("Mission Analysis & CV Tracking Overview")

# Only render the dashboard if all files are uploaded
if file_config and file_events and file_telem and file_comms:
    
    # Load Data
    config = json.load(file_config)
    df_events = pd.read_csv(file_events)
    df_telem = pd.read_csv(file_telem)
    df_comms = pd.read_csv(file_comms)
    
    scores = calculate_score(df_events, df_comms)

    # --- SECTION 1: HEADER & KPIs ---
    st.markdown(f"### Mission: `{config.get('MissionID', 'N/A')}` | Trainee: `{config.get('Trainee', 'N/A')}`")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Overall Score", f"{scores['Total']}/100", f"{'PASS' if scores['Total'] >= 80 else 'FAIL'}")
    col2.metric("CV Tracking Score", f"{scores['Tracking']}/15")
    col3.metric("Avg Telemetry Speed", f"{df_telem['Speed'].mean():.2f} m/s")
    col4.metric("Avg Video Latency", f"{df_comms[df_comms['Type'] == 'Video']['Latency_ms'].mean():.1f} ms")

    st.markdown("---")

    # --- SECTION 2: INTERACTIVE CHARTS ---
    st.subheader("📊 Telemetry & Payload Analytics")
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.write("**Target Position Error vs Course Deviation**")
        # Visualizing tracking accuracy over time
        fig_tracking = px.line(df_telem, x="Timestamp", y=["Target_Pos_Err", "Course_Deviation"], 
                               markers=True, title="Tracking & Navigation Deviations")
        st.plotly_chart(fig_tracking, use_container_width=True)

    with chart_col2:
        st.write("**Communications Latency**")
        # Visualizing network stability
        fig_comms = px.bar(df_comms, x="Timestamp", y="Latency_ms", color="Type", 
                           title="Link Latency by Type (Video vs Telemetry)")
        st.plotly_chart(fig_comms, use_container_width=True)

    st.markdown("---")

    # --- SECTION 3: LLM GENERATED INSIGHTS ---
    st.subheader("🧠 AI Post-Flight Narrative")
    st.write("Generate a qualitative analysis of the computer vision tracking and flight execution using Gemini.")
    
    if st.button("Generate AI Insights"):
        with st.spinner("Analyzing telemetry and CV events..."):
            try:
                # Construct the prompt
                prompt = f"""
                You are a senior flight simulation analyzer evaluating a YOLO_DeepSORT tracking payload.
                Analyze the following data and provide a concise, 3-paragraph executive summary focusing on:
                1. Overall flight and navigation execution.
                2. Computer Vision tracking performance (mention specific target errors or track losses).
                3. Network and safety health.
                
                CONFIG: {json.dumps(config)}
                SCORES: {json.dumps(scores)}
                EVENTS: {df_events.to_string(index=False)}
                """
                
                # Call Gemini
                client = genai.Client(api_key=API_KEY)
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                
                st.success("Analysis Complete!")
                st.write(response.text)
                
            except Exception as e:
                st.error(f"Failed to generate insights: {e}")

else:
    st.info("👈 Please upload all four simulation files in the sidebar to generate the dashboard.")
