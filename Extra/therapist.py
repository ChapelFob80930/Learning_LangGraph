#TODO: Fix Agent Memory 

from dotenv import load_dotenv
from typing import Annotated, Literal, Sequence
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

llm = init_chat_model("openai:gpt-4.1-nano")

class MessageClassifier(BaseModel):
    message_type: Literal["emotional", "logical"] = Field(
        ...,
        description="Classify if the message requires an emotional (therapist) or logical response."
    )

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    message_types: str|None
    
def classify_message(state: AgentState)->AgentState:
    last_message = state["messages"][-1]
    classifier_llm = llm.with_structured_output(MessageClassifier)
    
    result = classifier_llm.invoke([
        SystemMessage(content="""Classify the user message as either:
            - 'emotional': if it asks for emotional support, therapy, deals with feelings, or personal problems
            - 'logical': if it asks for facts, information, logical analysis, or practical solutions"""),
        last_message
    ])

    return {
        "messages": [
            SystemMessage(content=f"Classified as: {result.message_type}")
        ],
        "message_types":result.message_type
    }


def router(state: AgentState):
    message_type = state.get("message_types", "logical")
    if message_type == "emotional":
        return {"next": "therapist"}

    return {"next": "logical"}

def therapist_agent(state: AgentState)-> AgentState:
    print("Therapist agent responding...")
    last_message = state["messages"][-1]
    
    all_messages = [SystemMessage(content= """You are a compassionate therapist. Focus on the emotional aspects of the user's message.
    Show empathy, validate their feelings, and help them process their emotions.
    Ask thoughtful questions to help them explore their feelings more deeply.
    Avoid giving logical solutions unless explicitly asked.""")]+list(state["messages"])
    
    result = llm.invoke(all_messages)

    return {
        "messages": state["messages"] + [AIMessage(content = result.content)]
    }

def logical_agent(state: AgentState)-> AgentState:
    print("Logical agent responding...")
    last_message = state["messages"][-1]
    all_messages = [SystemMessage(content= """You are a purely logical assistant. Focus only on facts and information.
            Provide clear, concise answers based on logic and evidence.
            Do not address emotions or provide emotional support.
            Be direct and straightforward in your responses.""")]+list(state["messages"])
    
    result = llm.invoke(all_messages)

    return {
        "messages": state["messages"] + [AIMessage(content = result.content)]
    }
    
graph = StateGraph(AgentState)

graph.add_node("classifier", classify_message)
graph.add_node("router", router)
graph.add_node("therapist", therapist_agent)
graph.add_node("logical", logical_agent)

graph.add_edge(START, "classifier")
graph.add_edge("classifier", "router")
graph.add_conditional_edges(
    "router",
    lambda state: state.get("next"),
    {
        "therapist": "therapist",
        "logical": "logical"
    }
)
graph.add_edge("therapist", END)
graph.add_edge("logical", END)

agent = graph.compile()

def run_chatbot():
    state = {"messages": [], "message_types": None}

    while True:
        user_input = input("You: ")
        if user_input == "exit":
            print("Bye")
            break

        state["messages"] = state.get("messages", []) + [
            HumanMessage(content = user_input)
        ]

        state = agent.invoke(state)

        if state.get("messages") and len(state["messages"]) > 0:
            last_message = state["messages"][-1]
            print(f"AI: {last_message.content}")


if __name__ == "__main__":
    run_chatbot()
    

# from dotenv import load_dotenv
# from typing import Annotated, Literal
# from langgraph.graph import StateGraph, START, END
# from langgraph.graph.message import add_messages
# from langchain.chat_models import init_chat_model
# from pydantic import BaseModel, Field
# from typing_extensions import TypedDict

# load_dotenv()

# llm = init_chat_model(
#     "anthropic:claude-3-5-sonnet-latest"
# )


# class MessageClassifier(BaseModel):
#     message_type: Literal["emotional", "logical"] = Field(
#         ...,
#         description="Classify if the message requires an emotional (therapist) or logical response."
#     )


# class State(TypedDict):
#     messages: Annotated[list, add_messages]
#     message_type: str | None


# def classify_message(state: State):
#     last_message = state["messages"][-1]
#     classifier_llm = llm.with_structured_output(MessageClassifier)

#     result = classifier_llm.invoke([
#         {
#             "role": "system",
#             "content": """Classify the user message as either:
#             - 'emotional': if it asks for emotional support, therapy, deals with feelings, or personal problems
#             - 'logical': if it asks for facts, information, logical analysis, or practical solutions
#             """
#         },
#         {"role": "user", "content": last_message.content}
#     ])
#     return {"message_type": result.message_type}


# def router(state: State):
#     message_type = state.get("message_type", "logical")
#     if message_type == "emotional":
#         return {"next": "therapist"}

#     return {"next": "logical"}


# def therapist_agent(state: State):
#     last_message = state["messages"][-1]

#     messages = [
#         {"role": "system",
#          "content": """You are a compassionate therapist. Focus on the emotional aspects of the user's message.
#                         Show empathy, validate their feelings, and help them process their emotions.
#                         Ask thoughtful questions to help them explore their feelings more deeply.
#                         Avoid giving logical solutions unless explicitly asked."""
#          },
#         {
#             "role": "user",
#             "content": last_message.content
#         }
#     ]
#     reply = llm.invoke(messages)
#     return {"messages": [{"role": "assistant", "content": reply.content}]}


# def logical_agent(state: State):
#     last_message = state["messages"][-1]

#     messages = [
#         {"role": "system",
#          "content": """You are a purely logical assistant. Focus only on facts and information.
#             Provide clear, concise answers based on logic and evidence.
#             Do not address emotions or provide emotional support.
#             Be direct and straightforward in your responses."""
#          },
#         {
#             "role": "user",
#             "content": last_message.content
#         }
#     ]
#     reply = llm.invoke(messages)
#     return {"messages": [{"role": "assistant", "content": reply.content}]}


# graph_builder = StateGraph(State)

# graph_builder.add_node("classifier", classify_message)
# graph_builder.add_node("router", router)
# graph_builder.add_node("therapist", therapist_agent)
# graph_builder.add_node("logical", logical_agent)

# graph_builder.add_edge(START, "classifier")
# graph_builder.add_edge("classifier", "router")

# graph_builder.add_conditional_edges(
#     "router",
#     lambda state: state.get("next"),
#     {"therapist": "therapist", "logical": "logical"}
# )

# graph_builder.add_edge("therapist", END)
# graph_builder.add_edge("logical", END)

# graph = graph_builder.compile()


# def run_chatbot():
#     state = {"messages": [], "message_type": None}

#     while True:
#         user_input = input("Message: ")
#         if user_input == "exit":
#             print("Bye")
#             break

#         state["messages"] = state.get("messages", []) + [
#             {"role": "user", "content": user_input}
#         ]

#         state = graph.invoke(state)

#         if state.get("messages") and len(state["messages"]) > 0:
#             last_message = state["messages"][-1]
#             print(f"Assistant: {last_message.content}")


# if __name__ == "__main__":
#     run_chatbot()