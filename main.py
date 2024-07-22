import requests
import json
import urllib.parse
import time
from datetime import datetime, timedelta
import streamlit as st

# Frontend for https://web18.ibo.de/prognos/AleaStoppuhr/
# https://chatgpt.com/share/71cba47a-caf3-4849-8384-37cd4d4e59de
# https://chatgpt.com/share/bd8cc3cc-47c8-4463-8fa6-874b064c9e16
# install: pip install streamlit
# run: streamlit run app.py
# run (windows): python -m streamlit run streeamlit-automate.py

# Funktion zum Generieren des dynamischen Zeitstempels
def get_current_timestamp():
    return int(time.time())

# Funktion zum Generieren des dynamischen ID-Werts
def generate_dynamic_id():
    return f"ibo-gen{get_current_timestamp()}"

# Initialisieren von Session State Variablen
if "session" not in st.session_state:
    st.session_state.session = requests.Session()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""

if "tasks_list" not in st.session_state:
    st.session_state.tasks_list = []

if "selected_date" not in st.session_state:
    st.session_state.selected_date = datetime.now().date()

if "success_messages" not in st.session_state:
    st.session_state.success_messages = {}

# Header for JSON content
if "headers" not in st.session_state:
    st.session_state.headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0',
        'Accept': '*/*',
        'Accept-Language': 'de,en-US;q=0.7,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://web18.ibo.de',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Referer': 'https://web18.ibo.de/prognos/AleaStoppuhr/',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
        'TE': 'trailers'
    }

# Streamlit UI
st.title("Zeiterfassung")

if st.session_state.logged_in:
    st.subheader(f"Hallo {st.session_state.username} 👋")
    if st.button("Abmelden", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.session = requests.Session()
        st.experimental_rerun()
else:
    # Login-Informationen eingeben
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Anmelden", use_container_width=True, type="primary"):
        # URLS
        login_url = 'https://web18.ibo.de/prognos/PbApi/v1/Login'
        dc_value = int(time.time() * 1000)  # Dynamischer Zeitstempel für _dc
        tasks_url = f'https://web18.ibo.de/prognos/PbApi/v1/ap/su/TasksTree?crud=read&_dc={dc_value}'

        # Anmeldedaten
        login_payload = {
            "username": username,
            "password": password,
            "client": "SU",
            "isAdminSct": False
        }

        # Body für das Abrufen der Aufgaben
        tasks_payload = {
            "node": "root"
        }

        # Step 1: Login
        response = st.session_state.session.post(login_url, data=json.dumps(login_payload), headers=st.session_state.headers)

        # Check if login was successful
        if response.status_code == 200 and response.json().get('success'):
            st.success("Erfolgreich angemeldet")
            # Extract the session cookie
            session_cookie = response.cookies.get('AleaPbSessionId')
            if session_cookie:
                # Decode the session cookie value
                decoded_cookie = urllib.parse.unquote(session_cookie)
                
                # Step 2: Set the required cookies for further requests
                st.session_state.session.cookies.set('AleaPbSessionId', decoded_cookie)
                st.session_state.session.cookies.set('AleaStoppuhr_Language', 'de')

                # Step 3: Fetch the tasks
                tasks_response = st.session_state.session.post(tasks_url, data=json.dumps(tasks_payload), headers=st.session_state.headers)
                
                if tasks_response.status_code == 200:
                    tasks_data = tasks_response.json().get('data', [])
                    st.session_state.tasks_list = []

                    # Step 4: Process the tasks data
                    for task in tasks_data:
                        if 'children' in task:
                            for child in task['children']:
                                task_info = {
                                    "id": child.get("id"),
                                    "PbId": child.get("PbId"),
                                    "txt": child.get("txt"),
                                    "qtip": child.get("qtip"),
                                    "hours": None,  # Start with None to represent empty input
                                    "minutes": None  # Start with None to represent empty input
                                }
                                st.session_state.tasks_list.append(task_info)
                    
                    st.session_state.logged_in = True
                    st.session_state.username = username  # Set the username in session state

                else:
                    st.error(f"Failed to fetch tasks, status code: {tasks_response.status_code}")
                    st.error(tasks_response.text)
            else:
                st.error("Session cookie not found in the login response.")
        else:
            st.error(f"Login failed, status code: {response.status_code}")
            st.error(response.json())

if st.session_state.logged_in:
    # Datumswähler hinzufügen und Sprache auf Deutsch einstellen
    selected_date = st.date_input("Datum auswählen", value=st.session_state.selected_date, key="date_input")
    
    if selected_date != st.session_state.selected_date:
        # Reset times and success messages when date changes
        st.session_state.selected_date = selected_date
        for key in list(st.session_state.keys()):
            if key.startswith('hours_') or key.startswith('minutes_'):
                del st.session_state[key]
        st.session_state.success_messages = {}
        st.experimental_rerun()

    start_time = datetime.combine(selected_date, datetime.min.time()) + timedelta(hours=8)
    now = datetime.now()

    tasks_list = st.session_state.tasks_list
    durations = {}
    all_tasks_completed = True

    for task in tasks_list:
        expanded = False
        hours_key = f"hours_{task['id']}"
        minutes_key = f"minutes_{task['id']}"

        # Check if the task has any duration set
        if st.session_state.get(hours_key, 0) != 0 or st.session_state.get(minutes_key, 0) != 0:
            expanded = True
            all_tasks_completed = False

        with st.expander(task["txt"], expanded=expanded):
            st.write(task["qtip"])
            col1, col2 = st.columns(2)
            with col1:
                hours = st.number_input(f"Stunden", min_value=0, max_value=24, step=1, key=hours_key, value=st.session_state.get(hours_key, 0))
            with col2:
                minutes = st.number_input(f"Minuten", min_value=0, max_value=59, step=1, key=minutes_key, value=st.session_state.get(minutes_key, 0))
            task["hours"] = hours
            task["minutes"] = minutes
            durations[task['id']] = {"hours": hours, "minutes": minutes}

    if st.button("Senden", use_container_width=True, type="primary", disabled=all_tasks_completed):
        # Step 5: Prepare and send update requests
        update_url = 'https://web18.ibo.de/prognos/PbApi/v1/ap/su/StoppedTasks?crud=update'
        for task in tasks_list:
            duration = durations[task['id']]
            if duration["hours"] > 0 or duration["minutes"] > 0:
                duration_seconds = duration["hours"] * 3600 + duration["minutes"] * 60
                end_time = start_time + timedelta(seconds=duration_seconds)
                update_payload = [{
                    "id": generate_dynamic_id(),
                    "datStart": start_time.isoformat(),
                    "dur": 0,
                    "durMan": duration_seconds,
                    "amount": 1,
                    "useAmount": True,
                    "seqTxt": None,
                    "seqKind": 1,
                    "krit": None,
                    "pbItemId": task["id"],
                    "datEnd": end_time.isoformat(),
                    "datErst": now.isoformat(),
                    "notes": None,
                    "isFinalized": True,
                    "selTime": 3.847,
                    "seqId": None,
                    "seqTaskId": None,
                    "seqIsFinalized": False
                }]

                update_response = st.session_state.session.post(update_url, data=json.dumps(update_payload), headers=st.session_state.headers)
                
                if update_response.status_code == 200:
                    st.session_state.success_messages[task['id']] = f"Zeiterfassung für {task['txt']} erfolgreich"
                else:
                    st.error(f"Failed to update {task['txt']}, status code: {update_response.status_code}")
                    st.error(update_response.text)

    for message in st.session_state.success_messages.values():
        st.success(message)
