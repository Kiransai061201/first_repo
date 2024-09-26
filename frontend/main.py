import streamlit as st
from streamlit_option_menu import option_menu

# Import page functions
from pages.dashboard import show_dashboard
from pages.ai_projects import show_ai_projects
from pages.data_sets import show_data_sets
from pages.logs import show_logs
# from pages.api_keys import show_api_keys
from pages.app_directory import show_app_directory

st.set_page_config(page_title="Tori", layout="wide")

# Hide default Streamlit elements
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
.stDeployButton {display:none;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Custom sidebar
with st.sidebar:
    st.markdown('<h2 style="display: flex; align-items: center;"><span style="font-size: 24px; margin-right: 10px;">🖥️</span> Tori</h2>', unsafe_allow_html=True)
    
    selected = option_menu(
        menu_title=None,
        options=["Dashboard", "AI Projects", "Data Sets", "Logs", "API Keys", "App Directory"],
        icons=['house', 'robot', 'database', 'list-check', 'key', 'grid'],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "#262730"},
            "icon": {"color": "white", "font-size": "18px"}, 
            "nav-link": {"color": "white", "font-size": "16px", "text-align": "left", "margin":"0px", "--hover-color": "#3f3f4e"},
            "nav-link-selected": {"background-color": "#FF4B4B"},
        }
    )

# Main content
if selected == "Dashboard":
    show_dashboard()
elif selected == "AI Projects":
    show_ai_projects()
elif selected == "Data Sets":
    show_data_sets()
elif selected == "Logs":
    show_logs()
elif selected == "API Keys":
    show_api_keys()
elif selected == "App Directory":
    show_app_directory()

# Top right buttons
col1, col2 = st.sidebar.columns([2,1])
with col1:
    st.button("CREATE PROJECT")
with col2:
    st.image("https://via.placeholder.com/40", width=40)  # Replace with actual user image

st.sidebar.write("19831a0440@gmrit.edu.in")

# Bottom left
st.sidebar.markdown('<div style="position: fixed; bottom: 10px; left: 10px;"><a href="#">Report Bug</a></div>', unsafe_allow_html=True)

# Footer
st.markdown('<div style="position: fixed; bottom: 10px; right: 10px; font-size: 12px;">© 2024 Tori Technologies. v1.19.0</div>', unsafe_allow_html=True)