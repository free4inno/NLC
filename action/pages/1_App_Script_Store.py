import streamlit as st
from sqlalchemy.orm import Session
from model import App, session_factory

def get_apps():
    with session_factory() as session:
        apps = session.query(App.id, App.name, App.description, App.profile_list).all()
        session.commit()
    
    return apps

st.set_page_config(
    page_title="App Script Store",
    page_icon="🗂️",
    layout="centered",
    initial_sidebar_state="expanded"
)

st.subheader(':card_index_dividers: App Script Store', divider='gray')

if 'app_id' not in st.session_state:
    st.session_state.app_id = None

def run_app(app_id):
    st.session_state.app_id = app_id
    st.session_state.run_app = False

def on_delete_app(app_id):
    with session_factory() as session:
        session.query(App).filter(App.id == app_id).delete()
        session.commit()
    print(f"[App] delete {app_id}")

apps = get_apps()
for app in apps:
    with st.expander(app[1]):
        st.write(f":information_source: Introduction")
        st.write(app[2])

        st.write(":hammer_and_wrench: Required profile")
        profile_list = eval(app[3])
        for p in profile_list:
            st.write(f"{p['name']}: {p['description']}")
        
        col1, col2 = st.columns([1,6])
        
        with col1:
            if st.button("Enter ", key=str(app[0])+' run', on_click=run_app, args=[app[0]]):
                st.switch_page("pages/2_App_Execution.py")
                
        with col2:
            st.button("Delete", key=app[0], on_click=on_delete_app, args=[app[0]])