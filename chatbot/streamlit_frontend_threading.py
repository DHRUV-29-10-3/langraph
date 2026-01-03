import streamlit as st
from langgraph_backend import chatbot
from langchain_core.messages import HumanMessage
import uuid

# st.session_state -> dict -> 

#******************************** Helper functions ***************************************
# Generate a unique thread ID for each session
def generate_thread_id():
    return str(uuid.uuid4())

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    add_thread(st.session_state['thread_id'])
    st.session_state['message_history'] = []
  
def add_thread(thread_id):
    if thread_id not in st.session_state["chat_threads"]:
        st.session_state["chat_threads"].append(thread_id)

def load_conversation(thread_id):
    # Placeholder for loading thread-specific message history
    state = chatbot.get_state(config = {'configurable': {'thread_id': thread_id}})
    if state.values and "messages" in state.values:
        return state.values["messages"]
    return []

# ******************************** Session State Initialization *******************************
if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if "chat_threads" not in st.session_state: 
    st.session_state["chat_threads"] = []

add_thread(st.session_state['thread_id'])


# ******************************** Side bar ui ***************************************

st.sidebar.title("LangGraph Chatbot")
if st.sidebar.button("New Chat"):
    reset_chat()

st.sidebar.header("My conversations")


for thread in st.session_state["chat_threads"]:
    if st.sidebar.button(f"Thread ID: {thread}"):
        st.session_state['thread_id'] = thread
        messages = load_conversation(thread)

        temp_message_history = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                message_type = 'user'
            else:
                message_type = 'assistant'
            temp_message_history.append({'role': message_type, 'content': msg.content})
        st.session_state['message_history'] = temp_message_history 


# ******************************** Main chat ui ***************************************


# loading the conversation history
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])

#{'role': 'user', 'content': 'Hi'}
#{'role': 'assistant', 'content': 'Hi=ello'}

user_input = st.chat_input('Type here')

if user_input:

    # first add the message to message_history
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.text(user_input)

    CONFIG = {'configurable': {'thread_id': st.session_state['thread_id']}}     

    # response = chatbot.invoke({'messages': [HumanMessage(content=user_input)]}, config=CONFIG)
    
    # ai_message = response['messages'][-1].content
    # # first add the message to message_history
    # st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})
    with st.chat_message('assistant'):
        # st.text(ai_message)
        ai_message = st.write_stream(
            message_chunk.content for message_chunk, metadata in chatbot.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode="messages"
            )
        )

    st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})