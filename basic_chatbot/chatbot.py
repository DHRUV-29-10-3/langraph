import streamlit as st
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import TypedDict, Annotated
from dotenv import load_dotenv
from langgraph.graph.message import add_messages
import os
import uuid
import time
from datetime import datetime
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="LangGraph Chatbot",
    page_icon="🤖",
    layout="wide"
)

# Custom CSS for ChatGPT-like UI
st.markdown("""
<style>
    /* Hide default streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Sidebar styling */
    .sidebar-chat-item {
        padding: 0.75rem 1rem;
        margin: 0.25rem 0;
        border-radius: 0.5rem;
        cursor: pointer;
        transition: background-color 0.2s;
        border: 1px solid transparent;
    }
    .sidebar-chat-item:hover {
        background-color: #f0f2f6;
    }
    .sidebar-chat-active {
        background-color: #e3e8ef;
        border: 1px solid #d1d5db;
    }
    .chat-title {
        font-size: 0.9rem;
        font-weight: 500;
        margin-bottom: 0.25rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .chat-date {
        font-size: 0.75rem;
        color: #6b7280;
    }
    .new-chat-btn {
        width: 100%;
        padding: 0.75rem;
        background-color: #10a37f;
        color: white;
        border: none;
        border-radius: 0.5rem;
        font-weight: 500;
        margin-bottom: 1rem;
    }
    .main-header {
        text-align: center;
        padding: 1rem 0;
        margin-bottom: 1rem;
    }
    /* Chat container */
    .chat-container {
        max-width: 800px;
        margin: 0 auto;
    }
</style>
""", unsafe_allow_html=True)

# Initialize LLM
@st.cache_resource
def get_llm():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.error("Please set GOOGLE_API_KEY in your .env file")
        st.stop()
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0
    )

llm = get_llm()

# Define state
class ChatState(TypedDict):
    messages: Annotated[list, add_messages]

# Define chat node
def chat_node(state: ChatState) -> ChatState:
    messages = state["messages"]
    # Stream from LLM and collect full response
    full_response = ""
    for chunk in llm.stream(messages):
        if chunk.content:
            full_response += chunk.content
    # Return complete AI message for state
    return {"messages": [AIMessage(content=full_response)]}

# Generator function for streaming
def stream_llm_response(messages):
    """Generator function for streaming LLM responses"""
    for chunk in llm.stream(messages):
        if chunk.content:
            time.sleep(0.05)  # Add 20ms delay between chunks
            yield chunk.content

# Build graph
@st.cache_resource
def get_workflow():
    checkpointer = MemorySaver()
    graph = StateGraph(ChatState)
    graph.add_node("chat_node", chat_node)
    graph.add_edge(START, "chat_node")
    graph.add_edge("chat_node", END)
    return graph.compile(checkpointer=checkpointer)

workflow = get_workflow()

# Initialize session state for multiple chats
if "chats" not in st.session_state:
    # Structure: {chat_id: {"title": str, "messages": list, "created_at": datetime}}
    initial_chat_id = str(uuid.uuid4())
    st.session_state.chats = {
        initial_chat_id: {
            "title": "New Chat",
            "messages": [],
            "created_at": datetime.now()
        }
    }
    st.session_state.current_chat_id = initial_chat_id

if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = list(st.session_state.chats.keys())[0]

def create_new_chat():
    """Create a new chat and switch to it"""
    new_chat_id = str(uuid.uuid4())
    st.session_state.chats[new_chat_id] = {
        "title": "New Chat",
        "messages": [],
        "created_at": datetime.now()
    }
    st.session_state.current_chat_id = new_chat_id

def switch_chat(chat_id):
    """Switch to a different chat"""
    st.session_state.current_chat_id = chat_id

def delete_chat(chat_id):
    """Delete a chat"""
    if len(st.session_state.chats) > 1:
        del st.session_state.chats[chat_id]
        if st.session_state.current_chat_id == chat_id:
            st.session_state.current_chat_id = list(st.session_state.chats.keys())[0]
    else:
        # If it's the last chat, just clear it
        st.session_state.chats[chat_id] = {
            "title": "New Chat",
            "messages": [],
            "created_at": datetime.now(),
            "custom_title": False
        }

def rename_chat(chat_id, new_title):
    """Rename a chat"""
    if chat_id in st.session_state.chats:
        st.session_state.chats[chat_id]["title"] = new_title
        st.session_state.chats[chat_id]["custom_title"] = True

def get_chat_title(messages, custom_title=False, current_title="New Chat"):
    """Generate title from first user message if no custom title"""
    if custom_title:
        return current_title
    for msg in messages:
        if msg["role"] == "user":
            title = msg["content"][:30]
            if len(msg["content"]) > 30:
                title += "..."
            return title
    return "New Chat"

# Initialize editing state
if "editing_chat_id" not in st.session_state:
    st.session_state.editing_chat_id = None

# Sidebar
with st.sidebar:
    st.markdown("### 🤖 LangGraph Chat")
    st.divider()
    
    # New Chat Button
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        create_new_chat()
        st.rerun()
    
    st.divider()
    st.markdown("#### 💬 Your Chats")
    
    # Sort chats by creation date (newest first)
    sorted_chats = sorted(
        st.session_state.chats.items(),
        key=lambda x: x[1]["created_at"],
        reverse=True
    )
    
    # Display chat list
    for chat_id, chat_data in sorted_chats:
        is_active = chat_id == st.session_state.current_chat_id
        is_editing = st.session_state.editing_chat_id == chat_id
        
        # Update title based on messages (only if not custom)
        display_title = get_chat_title(
            chat_data["messages"], 
            chat_data.get("custom_title", False),
            chat_data["title"]
        )
        
        if is_editing:
            # Show rename input
            col1, col2 = st.columns([5, 1])
            with col1:
                new_title = st.text_input(
                    "Rename",
                    value=display_title,
                    key=f"rename_{chat_id}",
                    label_visibility="collapsed"
                )
            with col2:
                if st.button("✓", key=f"save_{chat_id}", help="Save name"):
                    rename_chat(chat_id, new_title)
                    st.session_state.editing_chat_id = None
                    st.rerun()
        else:
            col1, col2, col3 = st.columns([4, 1, 1])
            
            with col1:
                button_type = "primary" if is_active else "secondary"
                if st.button(
                    f"{'💬' if is_active else '○'} {display_title}",
                    key=f"chat_{chat_id}",
                    use_container_width=True,
                    type=button_type
                ):
                    switch_chat(chat_id)
                    st.rerun()
            
            with col2:
                if st.button("✏️", key=f"edit_{chat_id}", help="Rename chat"):
                    st.session_state.editing_chat_id = chat_id
                    st.rerun()
            
            with col3:
                if st.button("🗑️", key=f"delete_{chat_id}", help="Delete chat"):
                    delete_chat(chat_id)
                    st.rerun()
    
    st.divider()
    
    # Stats
    st.caption(f"📊 Total chats: {len(st.session_state.chats)}")
    current_messages = len(st.session_state.chats[st.session_state.current_chat_id]["messages"])
    st.caption(f"💬 Current chat messages: {current_messages}")

# Main chat area
current_chat = st.session_state.chats[st.session_state.current_chat_id]

# Header
st.markdown('<div class="main-header">', unsafe_allow_html=True)
st.title("🤖 LangGraph Chatbot")
st.caption("Powered by Google Gemini & LangGraph")
st.markdown('</div>', unsafe_allow_html=True)

# Display chat history for current chat
for message in current_chat["messages"]:
    role = message["role"]
    content = message["content"]
    with st.chat_message(role):
        st.markdown(content)

# Chat input
if user_input := st.chat_input("Type your message here..."):
    # Display user message
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Add to current chat history
    current_chat["messages"].append({
        "role": "user",
        "content": user_input
    })
    
    # Update chat title if it's the first message and no custom title
    if len(current_chat["messages"]) == 1 and not current_chat.get("custom_title", False):
        current_chat["title"] = get_chat_title(
            current_chat["messages"],
            current_chat.get("custom_title", False),
            current_chat["title"]
        )
    
    # Get AI response
    with st.chat_message("assistant"):
        # Create message history for streaming
        llm_messages = []
        for msg in current_chat["messages"][:-1]:  # Exclude the just-added user message
            if msg["role"] == "user":
                llm_messages.append(HumanMessage(content=msg["content"]))
            else:
                llm_messages.append(AIMessage(content=msg["content"]))
        llm_messages.append(HumanMessage(content=user_input))
        
        # Stream response using st.write_stream
        full_response = st.write_stream(stream_llm_response(llm_messages))
        
        # Update workflow state in background (for checkpointing)
        state = {"messages": [HumanMessage(content=user_input)]}
        config = {"configurable": {"thread_id": st.session_state.current_chat_id}}
        workflow.invoke(state, config=config)
    
    # Add AI response to current chat history
    current_chat["messages"].append({
        "role": "assistant",
        "content": full_response
    })
    
    st.rerun()

# Show welcome message if no messages
if len(current_chat["messages"]) == 0:
    st.markdown("""
    <div style="text-align: center; padding: 3rem; color: #6b7280;">
        <h2>👋 Welcome!</h2>
        <p>Start a conversation by typing a message below.</p>
        <p>You can create multiple chats using the sidebar.</p>
    </div>
    """, unsafe_allow_html=True)
