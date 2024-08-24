import os
from typing import TypedDict, Union, Annotated
import streamlit as st
from langchain import hub
from langchain.agents import Tool, create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import BaseMessage
from langchain_core.agents import AgentActionMessageLog
import operator
from langgraph.prebuilt.tool_executor import ToolExecutor
from langgraph.prebuilt import ToolInvocation
from langgraph.graph import END, StateGraph

# Streamlit configuration
st.set_page_config(page_title="LangChain Agent", layout="wide")

# Setting environment variables
os.environ["SERPER_API_KEY"] = "34cb8315950330790e93c8c8c9155bb0f83728b6"

# Define tools
search = GoogleSerperAPIWrapper()

def toggle_case(word):
    return ''.join([char.upper() if char.islower() else char.lower() for char in word])

def sort_string(string):
    return ''.join(sorted(string))

tools = [
    Tool(
        name="Search",
        func=search.run,
        description="useful for when you need to answer questions about current events",
    ),
    Tool(
        name="Toggle_Case",
        func=toggle_case,
        description="use when you want to convert the letter to uppercase or lowercase",
    ),
    Tool(
        name="Sort String",
        func=sort_string,
        description="use when you want to sort a string alphabetically",
    ),
]

# Load LLM and create agent
llm = ChatGoogleGenerativeAI(
    model="gemini-pro",
    google_api_key="AIzaSyB3p0pYwUY7sIa390RQh0XVlLAKhv-Lj9E",
    convert_system_message_to_human=True,
    verbose=True,
)

prompt = hub.pull("hwchase17/react")
agent_runnable = create_react_agent(llm, tools, prompt)

# Define AgentState TypedDict
class AgentState(TypedDict):
    input: str
    chat_history: list[BaseMessage]
    agent_outcome: Union[AgentAction, AgentFinish, None]
    return_direct: bool
    intermediate_steps: Annotated[list[tuple[AgentAction, str]], operator.add]

# Initialize ToolExecutor
tool_executor = ToolExecutor(tools)

def run_agent(state):
    agent_outcome = agent_runnable.invoke(state)
    return {"agent_outcome": agent_outcome}

def execute_tools(state):
    last_message = state['agent_outcome']
    tool_name = last_message.tool
    arguments = last_message

    action = ToolInvocation(
        tool=tool_name,
        tool_input=last_message.tool_input,
    )
    response = tool_executor.invoke(action)
    return {"intermediate_steps": [(state['agent_outcome'], response)]}

def should_continue(state):
    last_message = state['agent_outcome']
    if "Action" not in last_message.log:
        return "end"
    else:
        arguments = state["return_direct"]
        if arguments:
            return "final"
        else:
            return "continue"

def first_agent(inputs):
    action = AgentActionMessageLog(
        tool="Search",
        tool_input=inputs["input"],
        log="",
        message_log=[]
    )
    return {"agent_outcome": action}

# Define the workflow
workflow = StateGraph(AgentState)
workflow.add_node("agent", run_agent)
workflow.add_node("action", execute_tools)
workflow.add_node("final", execute_tools)
workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "action",
        "final": "final",
        "end": END
    }
)
workflow.add_edge('action', 'agent')
workflow.add_edge('final', END)

app = workflow.compile()

def main():
    st.title("LangGraph Agent + Gemini Pro + Custom Tool + Streamlit")
    input_text = st.text_area("Enter your text:")

    if st.button("Run Agent"):
        inputs = {"input": input_text, "chat_history": [], "return_direct": False}
        results = []
        for s in app.stream(inputs):
            result = list(s.values())[0]
            results.append(result)
            st.write(result)  # Display each step's output

if __name__ == "__main__":
    main()
