import streamlit as st
import psycopg2

LOGIN_HEARTBEATTIME = 5

def get_conn():
    return psycopg2.connect(
        host="db",
        database="test",
        user="myuser",
        password="mypassword",
        port="5432"
    )

def init_chats(chat_room):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f'''
        CREATE TABLE IF NOT EXISTS msgboard_{int(chat_room)}(
            id SERIAL PRIMARY KEY,
            name VARCHAR NOT NULL,
            message VARCHAR NOT NULL
        )
    ''')
    cur.execute(f'''
        CREATE TABLE IF NOT EXISTS statuses_{int(chat_room)}(
            user_type VARCHAR PRIMARY KEY,
            sign_in_activity TIMESTAMP NOT NULL
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

def logged_in(chat_room, user_type):
    '''Returns True if user_type had a heartbeat within LOGIN_HEARTBEATTIME seconds'''
    conn = get_conn()
    cur = conn.cursor()
    # Let Postgres handle the time comparison to avoid UTC vs local timezone mismatches
    cur.execute(
        f'''
        SELECT 1 FROM public.statuses_{int(chat_room)}
        WHERE user_type = %s
          AND sign_in_activity > NOW() - INTERVAL '%s seconds'
        ''',
        (user_type, LOGIN_HEARTBEATTIME)
    )
    is_active = cur.fetchone() is not None
    cur.close()
    conn.close()
    return is_active

def login(chat_room, user_type):
    '''Inserts user or updates heartbeat timestamp if already present'''
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        f'''
        INSERT INTO public.statuses_{int(chat_room)} (user_type, sign_in_activity)
        VALUES (%s, NOW())
        ON CONFLICT (user_type)
        DO UPDATE SET sign_in_activity = NOW()
        ''',
        (user_type,)
    )
    conn.commit()
    cur.close()
    conn.close()

@st.fragment(run_every=f"{LOGIN_HEARTBEATTIME}s")
def login_heartbeat(chat_room, user_type):
    login(chat_room, user_type)

def return_messages(chat_room):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f'SELECT name, message FROM public.msgboard_{int(chat_room)} ORDER BY id ASC')
    return_list = [{"name": row[0], "message": row[1]} for row in cur.fetchall()]
    cur.close()
    conn.close()
    return return_list

def send_message(chat_room, user_type, message):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        f'INSERT INTO msgboard_{int(chat_room)} (name, message) VALUES (%s, %s)',
        (user_type, message)
    )
    conn.commit()
    cur.close()
    conn.close()

@st.fragment(run_every="1s")
def check_updates(chat_room):
    chat_hist = return_messages(chat_room)
    if chat_hist != st.session_state['messages']:
        st.session_state['messages'] = chat_hist
        st.rerun()

def check_if_active():
    if st.session_state['messages']:
        return st.session_state["messages"][-1]["name"] == st.session_state["user_type"]
    return False

# Session state management
if "messages" not in st.session_state:
    st.session_state['messages'] = []
if "room_number" not in st.session_state:
    st.session_state["room_number"] = 0
if "user_type" not in st.session_state:
    st.session_state["user_type"] = None
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

@st.dialog("Pick your room", dismissible=False)
def room_pick():
    # Use local variables inside the dialog so session_state only updates on button click
    room = st.selectbox("Select your room number", options=list(range(1, 11)))
    role = st.selectbox("Select your role", options=["User", "Agent"])
    
    if st.button("Enter room"):
        init_chats(room)
        if logged_in(room, role):
            st.error(f"{role} already logged in to room number {room}! If you're sure you're not logged in, try again in {LOGIN_HEARTBEATTIME} seconds.")
        else:
            login(room, role)
            st.session_state["room_number"] = room
            st.session_state["user_type"] = role
            st.session_state["messages"] = return_messages(room)
            st.session_state["logged_in"] = True
            st.rerun()

@st.dialog("SUPER SECRET AGENT CHATROOM", width = "large")
def agent_chatroom():
    st.iframe(
        "https://docs.google.com/document/d/1rDNM75iNtGMtQRD2aBI4B0eqLGlzIDGyK69Po1suplw/edit?usp=sharing",
    )

if not st.session_state["logged_in"]:
    room_pick()
else:
    
    for message in st.session_state['messages']:
        with st.chat_message(message["name"]):
            st.markdown(message["message"])
            
    chatinput = st.chat_input("Write something", disabled=check_if_active())
    if chatinput:
        send_message(st.session_state["room_number"], st.session_state["user_type"], chatinput)
        st.session_state["messages"] = return_messages(st.session_state["room_number"])
        st.rerun()
        
    # divergent UI here:
    if st.session_state["user_type"] == 'Agent':
        with st.sidebar:
            agent_msgboard = st.button("DO NOT PRESS! ☠️")
            if agent_msgboard:
                agent_chatroom()
    
    check_updates(st.session_state["room_number"])
    login_heartbeat(st.session_state["room_number"], st.session_state["user_type"])