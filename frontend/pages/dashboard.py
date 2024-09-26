import streamlit as st
from streamlit_option_menu import option_menu
import pages.app_directory as app_directory

def create_card(title, description, image_url):
    return f"""
    <div style="border:1px solid #ddd; border-radius:5px; padding:10px; margin-bottom:10px;">
        <img src="{image_url}" style="width:100%; height:150px; object-fit:cover; border-radius:5px;">
        <h3>{title}</h3>
        <p>{description}</p>
    </div>
    """

def dashboard():
    st.set_page_config(page_title="TORI", layout="wide")

    # Sidebar
    with st.sidebar:
        selected = option_menu(
            menu_title="TORI",
            options=["Dashboard", "AI Projects", "Data Sets", "Logs", "API Keys", "App Directory"],
            icons=['house', 'robot', 'database', 'list-check', 'key', 'grid'],
            menu_icon="cast",
            default_index=0,
        )

    if selected == "Dashboard":
        show_dashboard()
    elif selected == "App Directory":
        app_directory.show_app_directory()
    else:
        st.title(selected)
        st.write(f"This is the {selected} page. Content to be added.")

    # Top right buttons
    st.sidebar.button("CREATE PROJECT")
    st.sidebar.write("19831a0440@gmrit.edu.in")

    # Bottom left
    st.sidebar.markdown('<div style="position:fixed; bottom:10px; left:10px;"><a href="#">Report Bug</a></div>', unsafe_allow_html=True)

def show_dashboard():
    # Main content
    st.title("Dashboard")
    st.write("Home > Dashboard")

    # Welcome message and checklist
    st.markdown("""
    <div style="border:1px solid #ddd; border-radius:5px; padding:20px; margin-bottom:20px;">
        <h2>Welcome, Kiran 👋</h2>
        <p>We're delighted to have you here! Here's a check list to help you get started.</p>
        <ul style="list-style-type: none; padding-left: 0;">
            <li>✅ Create a new project</li>
            <li>⬜ Test your AI in the TORI Playground <button style="background-color:#333; color:white; border:none; padding:5px 10px; border-radius:3px;">START</button></li>
            <li>⬜ Fine-tune AI configuration</li>
            <li>⬜ View history</li>
        </ul>
        <a href="#" style="color: #666;">Hide Checklist</a>
    </div>
    """, unsafe_allow_html=True)

    # Usage statistics
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Credit Usage", value="0 / 100 Credits")
    with col2:
        st.metric(label="Data Storage", value="0 GB / 1 GB")

    # Resources
    st.header("Resources")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(create_card(
            "Help Center",
            "Need help with something? Find your answer at our Help Center.",
            "https://via.placeholder.com/400x200?text=Help+Center"
        ), unsafe_allow_html=True)
    with col2:
        st.markdown(create_card(
            "Blog",
            "See our latest updates, sharing, technical content, and more.",
            "https://via.placeholder.com/400x200?text=Blog"
        ), unsafe_allow_html=True)

    # Footer
    st.markdown('<div style="position:fixed; bottom:10px; right:10px; font-size:10px;">© 2024 TORI Technologies. v1.19.0</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    dashboard()