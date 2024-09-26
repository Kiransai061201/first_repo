import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

def show_logs():
    st.title("Logs")
    
    # Breadcrumb
    st.markdown("Home > Logs")
    
    # AI Project dropdown
    ai_project = st.selectbox(
        "AI Project",
        ["[Demo] Open Source Prompt ..."],
        label_visibility="collapsed"
    )
    
    # Date range picker
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", datetime.now() - timedelta(days=7))
    with col2:
        end_date = st.date_input("End Date", datetime.now())
    
    # Create a sample dataframe for logs
    df = pd.DataFrame({
        "Timestamp": pd.date_range(start=start_date, end=end_date, freq="D"),
        "Identifier": ["ID" + str(i) for i in range(1, (end_date - start_date).days + 2)],
        "Input": ["Sample input " + str(i) for i in range(1, (end_date - start_date).days + 2)],
        "Output": ["Sample output " + str(i) for i in range(1, (end_date - start_date).days + 2)],
        "Score": [round(i/10, 2) for i in range(1, (end_date - start_date).days + 2)],
        "Credits Used": [i*10 for i in range(1, (end_date - start_date).days + 2)],
        "Trace": ["Trace" + str(i) for i in range(1, (end_date - start_date).days + 2)]
    })
    
    # Display the dataframe
    st.dataframe(df, hide_index=True)

    # Pagination
    st.markdown("1-10 of 10")
    
    # Info tooltips
    st.markdown("""
    <style>
    .tooltip {
      position: relative;
      display: inline-block;
      border-bottom: 1px dotted black;
    }
    .tooltip .tooltiptext {
      visibility: hidden;
      width: 120px;
      background-color: black;
      color: #fff;
      text-align: center;
      border-radius: 6px;
      padding: 5px 0;
      position: absolute;
      z-index: 1;
      bottom: 125%;
      left: 50%;
      margin-left: -60px;
      opacity: 0;
      transition: opacity 0.3s;
    }
    .tooltip:hover .tooltiptext {
      visibility: visible;
      opacity: 1;
    }
    </style>
    
    <div class="tooltip">Identifier ℹ️
      <span class="tooltiptext">Unique identifier for each log entry</span>
    </div>
    
    <div class="tooltip">Score ℹ️
      <span class="tooltiptext">Confidence score of the AI model's output</span>
    </div>
    """, unsafe_allow_html=True)