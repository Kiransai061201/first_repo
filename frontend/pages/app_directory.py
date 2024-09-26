import streamlit as st

def create_card(title, description, button_text, icon=None, button_type="dark"):
    button_style = "dark" if button_type == "dark" else "light"
    icon_html = f'<span style="font-size: 24px; margin-right: 10px;">{icon}</span>' if icon else ""
    return f"""
    <div style="border:1px solid #ddd; border-radius:5px; padding:10px; margin-bottom:10px;">
        <h3>{icon_html}{title}</h3>
        <p>{description}</p>
        <button style="background-color:{'#333' if button_type == 'dark' else '#fff'}; color:{'white' if button_type == 'dark' else 'black'}; border:{'none' if button_type == 'dark' else '1px solid #ddd'}; padding:5px 10px; border-radius:3px;">{button_text}</button>
    </div>
    """

def show_app_directory():
    # Main content
    st.title("App Directory")
    st.write("Home > App Directory")

    # Data Sources
    st.header("Data Sources")
    st.write("Applications that offer a wide variety of data sources for importing into your custom AI.")

    data_sources = [
        {"name": "Confluence", "description": "Import your Confluence pages from your space.", "icon": "⚡"},
        {"name": "Google Drive", "description": "Import your Google Docs, Sheets, and other files.", "icon": "📁"},
        {"name": "Microsoft SharePoint", "description": "Import your Microsoft documents and other files.", "icon": "📂"},
        {"name": "Notion", "description": "Import your Notion pages from your account.", "icon": "📝"}
    ]

    cols = st.columns(2)
    for idx, source in enumerate(data_sources):
        with cols[idx % 2]:
            st.markdown(create_card(source['name'], source['description'], "CONNECT", source['icon']), unsafe_allow_html=True)

    st.markdown('<a href="#">Suggest an Integration</a>', unsafe_allow_html=True)

    # Apps
    st.header("Apps")
    st.write("Apps that can be powered by your custom AI with no coding required.")

    apps = [
        {"name": "Zapier", "description": "Give your LLM pipeline access to thousands of apps via Zapier.", "icon": "⚡", "button_type": "light"},
        {"name": "Pipedream", "description": "Give your LLM pipeline access to thousands of apps via Pipedream.", "icon": "🌊", "button_type": "light"},
        {"name": "Discord", "description": "Add a Discord bot to your server powered by your LLM pipeline.", "icon": "💬"},
        {"name": "Slack", "description": "Connect your LLM pipeline to Slack to create a powerful chatbot.", "icon": "🔷"},
        {"name": "Teams", "description": "Connect your LLM pipeline to Teams to create a powerful chatbot.", "icon": "👥", "button_text": "COMING SOON", "button_type": "disabled"},
        {"name": "Messenger", "description": "Connect your LLM pipeline to Messenger to create a powerful chatbot.", "icon": "✉️", "button_text": "COMING SOON", "button_type": "disabled"},
        {"name": "Telegram", "description": "Connect your LLM pipeline to Telegram to create a powerful chatbot.", "icon": "📱", "button_text": "COMING SOON", "button_type": "disabled"}
    ]

    for app in apps:
        st.markdown(create_card(app['name'], app['description'], app.get('button_text', 'CONNECT'), app['icon'], app.get('button_type', 'dark')), unsafe_allow_html=True)

    st.markdown('<a href="#">Suggest an Integration</a>', unsafe_allow_html=True)

    # LLMs
    st.header("LLMs")
    st.write("Bring your own LLM to the platform.")

    llms = [
        {"name": "AWS SageMaker", "description": "Integrate your own models and utilize them on Vext.", "icon": "🧠", "button_text": "LEARN MORE", "button_type": "light"},
        {"name": "AWS Bedrock", "description": "Integrate your LLMs hosted on Bedrock and them on Vext.", "icon": "🪨", "button_text": "COMING SOON", "button_type": "disabled"}
    ]

    for llm in llms:
        st.markdown(create_card(llm['name'], llm['description'], llm['button_text'], llm['icon'], llm['button_type']), unsafe_allow_html=True)