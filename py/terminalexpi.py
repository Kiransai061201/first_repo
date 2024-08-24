from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from google.generativeai.types import HarmCategory, HarmBlockThreshold



# Function to handle the initial image upload and generate text output
def initial_task(image_path):
    # Task 1 logic
        # print(image,"\n",prompt)
    # print(image_path)
    # image = Image.open(image_path)
    # image.save("output_image.png")
    prompt_instructions = """i want the what  type of the data that file contains example - Name
- Date of birth
- Height
- Hair color
- Eye color
- Address
- Driver's license number
- Expiration date
- Issue date
soo on depending on the images 
 dont give the original values only tags
 """

    llm = ChatGoogleGenerativeAI(model="gemini-pro-vision",google_api_key="AIzaSyB3p0pYwUY7sIa390RQh0XVlLAKhv-Lj9E",
                                temperature=0.7,convert_system_message_to_human=True,safety_settings={
                                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT : HarmBlockThreshold.BLOCK_NONE
                                })


    # example
    image_message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": prompt_instructions,
            },
            {"type": "image_url", "image_url": image_path},
        ]
    )
    image_response = llm.invoke([image_message])
    return image_response.content


import os

# Function to handle the initial image upload and generate text output
def process_images_in_folder(folder_path):
    # Initialize a list to store responses for each image
    all_responses = []
    
    # Iterate over each file in the folder
    for filename in os.listdir(folder_path):
        # Check if the file is an image (you may want to improve this check)
        if filename.endswith(".jpg") or filename.endswith(".png"):
            # Construct the full path to the image file
            image_path = os.path.join(folder_path, filename)
            
            # Call the initial_task function to process the image and get the response
            response = initial_task(image_path)
            
            # Append the response to the list
            all_responses.append((filename, response))
    
    return all_responses

# Example usage:
folder_path = r"images"
responses = process_images_in_folder(folder_path)

# Print responses for each image
for filename, response in responses:

    # print(f"Response for {filename}:")
    print(response)
    print("\n")








