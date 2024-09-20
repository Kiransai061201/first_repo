from langchain_ibm import WatsonxLLM
from ibm_watsonx_ai.foundation_models.utils.enums import ModelTypes
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from ibm_watsonx_ai.foundation_models.utils.enums import DecodingMethods

watsonx_api_key = "D5B9pJCF_adaiG_5GUDLe1Df7pjEMOnJ_b8PGkvnUg7-"
watsonx_url = "https://us-south.ml.cloud.ibm.com"
project_id = "ccd1b2db-196d-42fa-9941-0305160282da"

try:
    llm = WatsonxLLM(
        model_id=ModelTypes.GRANITE_13B_CHAT_V2.value,
        url=watsonx_url,
        apikey=watsonx_api_key,
        project_id=project_id,
        params={
            GenParams.DECODING_METHOD: DecodingMethods.GREEDY,
            GenParams.MIN_NEW_TOKENS: 1,
            GenParams.MAX_NEW_TOKENS: 100,
            GenParams.STOP_SEQUENCES: [".", "?", "!"]
        }
    )
    print("WatsonxLLM initialized successfully")
    
    # Test the LLM
    response = llm("Hello, how are you?")
    print(f"LLM Response: {response}")
    
except Exception as e:
    print(f"Error initializing WatsonxLLM: {str(e)}")