import streamlit as st

def show_data_sets():
    st.title("Data Sets")
    st.markdown("Home > Data Sets")

    # Create two columns
    col1, col2 = st.columns([3, 2])

    with col1:
        # Add Data Set section
        st.markdown("""
        <div style="background-color: #f0f0f0; padding: 20px; border-radius: 5px; margin-bottom: 20px;">
            <button style="background-color: white; color: #333; border: 1px solid #333; padding: 10px 20px; border-radius: 5px;">ADD A DATA SET</button>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        # Existing Data Set
        st.markdown("""
        <div style="border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin-bottom: 15px;">
            <h3>Open Source Prompt (w/ RAG)</h3>
            <div style="display: flex; align-items: center;">
                <span style="background-color: #28a745; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px; margin-right: 10px;">Ready</span>
                <span style="flex-grow: 1;"></span>
                <span>•••</span>
            </div>
            <p>Created by Kiran -</p>
            <p style="color: #666;">Last changed: September 25, 2024 at 06:36 PM</p>
        </div>
        """, unsafe_allow_html=True)

    # Pagination
    st.markdown("""
    <div style="display: flex; justify-content: center; align-items: center; margin-top: 20px;">
        <span style="margin: 0 10px; color: #ccc;">◀</span>
        <span style="background-color: #f0f0f0; padding: 5px 10px; border-radius: 5px;">1</span>
        <span style="margin: 0 10px; color: #ccc;">▶</span>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    show_data_sets()