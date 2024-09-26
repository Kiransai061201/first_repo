import streamlit as st
from datetime import datetime

def show_ai_projects():
    st.title("AI Projects")
    st.markdown("Home > AI Projects")

    # Create Project Section
    st.markdown("""
    <div style="background-color: #f0f0f0; padding: 20px; border-radius: 5px; margin-bottom: 20px;">
        <h3>Create a New Project</h3>
        <button style="background-color: #333; color: white; border: none; padding: 10px 20px; margin-right: 10px; border-radius: 5px;">BUILD YOUR OWN</button>
        <button style="background-color: white; color: #333; border: 1px solid #333; padding: 10px 20px; border-radius: 5px;">USE A TEMPLATE</button>
    </div>
    """, unsafe_allow_html=True)

    # Existing Projects
    projects = [
        {
            "name": "[Demo] Open Source Prompt w/ RAG",
            "description": "This is an incredibly smart AI.",
            "created_by": "Kiran",
            "last_changed": "September 25, 2024 at 06:36 PM"
        },
        {
            "name": "Untitled",
            "description": "This is an incredibly smart AI.",
            "created_by": "Unknown",
            "last_changed": "Invalid Date"
        }
    ]

    for project in projects:
        st.markdown(f"""
        <div style="border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin-bottom: 15px;">
            <h3>{project['name']}</h3>
            <p>{project['description']}</p>
            <p>Created by {project['created_by']}</p>
            <p>Last changed: {project['last_changed']}</p>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="width: 40px; height: 20px; background-color: #ccc; border-radius: 10px;"></div>
                <span>•••</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Pagination
    st.markdown("""
    <div style="display: flex; justify-content: center; align-items: center; margin-top: 20px;">
        <span style="margin: 0 10px;">◀</span>
        <span style="background-color: #f0f0f0; padding: 5px 10px; border-radius: 5px;">1</span>
        <span style="margin: 0 10px;">▶</span>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    show_ai_projects()