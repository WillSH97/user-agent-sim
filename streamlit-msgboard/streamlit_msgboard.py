import streamlit as st
import time
import os
import psycopg2

#upon init
def init_chats(chat_room):
    '''
    creates tables for chat rooms - one is chat history and other stores login, system prompt, tools
    '''
    conn = psycopg2.connect(    
        host="db",                     # Matches the docker-compose service name
        database="test",
        user="myuser",
        password="mypassword",
        port="5432"
    )
    cur = conn.cursor()
    create_chathist_table_query = f'''
CREATE TABLE IF NOT EXISTS msgboard_{chat_room}(
id SERIAL PRIMARY KEY,
name VARCHAR NOT NULL,
message VARCHAR NOT NULL
)
    ''' # REMINDER - change message type to some json-like thing when ready
    create_login_table_query = f'''
CREATE TABLE IF NOT EXISTS statuses_{chat_room}(
user_type VARCHAR PRIMARY KEY,
signed_in BOOL NOT NULL
)
    ''' # tools_avail JSON/BSON ?????

    cur.execute(create_chathist_table_query)
    cur.execute(create_login_table_query)
    conn.commit()
    cur.close()

def check_role(chat_room, user_type):
    '''TO DO'''
    return
    
    

def return_messages(chat_room):
    '''
    check the postgres and return all, formatted as message history
    '''
    conn = psycopg2.connect(    
        host="db",                     # Matches the docker-compose service name
        database="test",
        user="myuser",
        password="mypassword",
        port="5432"
    )
    cur = conn.cursor()
    return_msgboard_query = f'''
SELECT name, message from public.msgboard_{chat_room}
'''
    results = cur.execute(return_msgboard_query)
    return_list = []
    for result in cur.fetchall():
        return_list.append(
            {
                "name": result[0],
                "message": result[1],
                # "personality": result[2]
            }
        )

    cur.close()
    conn.close()
    return return_list

def send_message(chat_room, user_type, message):
    '''
    add msg into chat hist
    '''
    conn = psycopg2.connect(    
        host="db",                     # Matches the docker-compose service name
        database="test",
        user="myuser",
        password="mypassword",
        port="5432"
    )
    cur = conn.cursor()
    insert_query = f"""
INSERT INTO msgboard_{chat_room} (name, message) 
VALUES (%s, %s);
    """
    msg_data = (user_type, message) # friends[name]["img"]
    results = cur.execute(insert_query, msg_data)
    conn.commit()
    cur.close()
    conn.close()

@st.fragment(parallel = True, run_every="1s")
def check_updates(chat_room, user_type):
    '''
    "daemon" process that constantly:
        - checks server for updates on msgs
    '''

    chat_hist = return_messages(chat_room)
    if chat_hist != st.session_state['messages']:
        st.session_state['messages'] = chat_hist
        st.rerun()

#dumb support script
def check_if_active():
    if st.session_state['messages']:
        return st.session_state["messages"][-1]["name"]==st.session_state["user_type"]
    else:
        return False

# session state mgmt
if "messages" not in st.session_state:
    st.session_state['messages'] = []

if "room_number" not in st.session_state:
    st.session_state["room_number"] = 0

if "user_type" not in st.session_state:
    st.session_state["user_type"] = None
        

### UI BULLSHIT
@st.dialog("pick your room", dismissible = False)
def room_pick():
    st.write("pick a room number between 1 and 10")
    st.session_state["room_number"] = st.selectbox(
        label = "select your room number",
        options = list(range(1,11))
    )
    st.write("pick role")
    st.session_state["user_type"] = st.selectbox(
        label = "select your role",
        options = ["User", "Agent"]
    )
    if st.button("enter room"):
        init_chats(st.session_state["room_number"])

        #FUNC TO CREATE ROOM
        # IF ALREADY CREATED/LOGGED IN, DON'T LET THEM LOG IN - "this acct is already logged in!"
        # else create it
        st.session_state["messages"] = return_messages(st.session_state['room_number'])
        st.rerun()
    

if st.session_state["room_number"] == 0 or st.session_state["user_type"] == None: # if no room and/or user type has been picked
    room_pick()
else:
    for message in st.session_state['messages']:
        with st.chat_message(message["name"], ): #using the name par for the username, add avatar here
            st.markdown(message["message"])
            # if message["message"]["image"]: #<- I'll implement this properly in a sec
            #     st.image(message["message"]["image"])
            
    chatinput = st.chat_input("write something", disabled = check_if_active())# st.session_state["waiting_for_response"])
    
    if chatinput: # and chatinput.text: #<- only need this for when multimodal
        send_message(st.session_state["room_number"], st.session_state["user_type"], chatinput)
        
        
    check_updates(st.session_state["room_number"], st.session_state["user_type"])
