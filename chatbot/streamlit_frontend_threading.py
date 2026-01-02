import streamlit as st
from langgraph_backend import chatbot
from langchain_core.messages import HumanMessage
import uuid

# st.session_state -> dict -> 

# Generate a unique thread ID for each session
def generate_thread_id():
    return str(uuid.uuid4())

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    add_thread(st.session_state['thread_id'])
    st.session_state['message_history'] = []

def add_thread(thread_id):
    if thread_id not in st.session_state:
        st.session_state[thread_id] = []

def new_chat():
    st.session_state['message_history'] = []
    st.session_state['thread_id'] = generate_thread_id()

# ******************************** Session State Initialization *******************************
if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if "chat_threads" not in st.session_state:
    st.session_state["chat_threads"] = []




# ******************************** Side bar ui ***************************************
st.sidebar.title("LangGraph Chatbot")
st.sidebar.button("New Chat", on_click=new_chat)
st.sidebar.header("My conversations")
st.sidebar.text(f"Thread ID: {st.session_state['thread_id']}")



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