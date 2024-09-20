import os
import pathlib
import textwrap
from PIL import Image
import google.generativeai as genai
from langchain.llms import OpenAI
from dotenv import load_dotenv
import streamlit as st

load_dotenv() # take environment variables from .env.

os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

## Function to load OpenAI model and get respones
def get_gemini_response(input, images, prompt):
    model = genai.GenerativeModel('gemini-pro-vision')
    response = model.generate_content([input, *images, prompt])
    return response.text

def input_image_setup(uploaded_files):
    # Check if files have been uploaded
    if uploaded_files is not None:
        image_parts = []
        for uploaded_file in uploaded_files:
            bytes_data = uploaded_file.getvalue()
            image_parts.append({
                "mime_type": uploaded_file.type,  # Get the mime type of the uploaded file
                "data": bytes_data
            })
        return image_parts
    else:
        raise FileNotFoundError("No files uploaded")

##initialize our streamlit app
st.set_page_config(page_title="Gemini Image Demo")
st.header("Gemini Application")
input = st.text_input("Input Prompt: ", key="input")
uploaded_files = st.file_uploader("Choose images...", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
images = []
if uploaded_files is not None:
    for uploaded_file in uploaded_files:
        image = Image.open(uploaded_file)
        # st.image(image, caption="Uploaded Image.", use_column_width=True)
        # images.append(image)

submit = st.button("Tell me about the images")
input_prompt = """You are an expert in understanding invoices. You will receive input images as invoices & you will have to answer questions based on the input images"""

## If ask button is clicked
if submit:
    image_data = input_image_setup(uploaded_files)
    response = get_gemini_response(input_prompt, image_data, input)
    st.subheader("The Response is")
    st.write(response)