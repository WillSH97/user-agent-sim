import streamlit as st
import time
import os
from celery import Celery
import psycopg2

# REDIS_BROKER=os.environ.get("REDIS_BROKER")
# REDIS_BACKEND=os.environ.get("REDIS_BACKEND")
# print(REDIS_BROKER)
# print(REDIS_BACKEND)

# celery_app = Celery('worker', broker=REDIS_BROKER, backend=REDIS_BACKEND)

#support func



'''
just some inline brainstorming

message type should be: 
        {
        text: text,
        image: bytestring,
        }


upon init, we get a dialogue box. This dialogue box asks what room number you are in. When asked, can be limited from 1-10 initially (in code).
When confirmed, run CREATE TABLE query(s):

CREATE TABLE IF NOT EXISTS {number}(
id SERIAL PRIMARY KEY,
user_type VARCHAR NOT NULL,
message JSON NOT NULL, # THIS PART I MADE UP
personality VARCHAR NOT NULL
)


#this one will be made up
CREATE TABLE IF NOT EXISTS {number_statuses}(
user_type VARCHAR PRIMARY KEY
signed_in BOOL NOT NULL,
tools_avail JSON/BSON ?????
)

I'll also add a fragment here that is constantly sending a ping to a celery worker or fastapi endpoint which will log people off when inactive????

'''

#upon init


def init_chats(chat_room):
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





if "messages" not in st.session_state:
    st.session_state['messages'] = []

if "room_number" not in st.session_state:
    st.session_state["room_number"] = 0

if "user_type" not in st.session_state:
    st.session_state["user_type"] = None

@st.fragment(parallel = True, run_every="1s")
def check_updates(chat_room):
    #add ping in here too?
    chat_hist = return_messages(chat_room)
    if chat_hist != st.session_state['messages']:
        st.session_state['messages'] = chat_hist
        st.rerun()
        

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
            
    chatinput = st.chat_input("write something")
    
    if chatinput: # and chatinput.text: #<- only need this for when multimodal
        send_message(st.session_state["room_number"], st.session_state["user_type"], chatinput)
        
        
    check_updates(st.session_state["room_number"])
