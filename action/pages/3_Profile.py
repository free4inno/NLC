import pandas as pd
import streamlit as st
from sqlalchemy.sql import text

st.set_page_config(
    page_title="Profile",
    page_icon="🛠️",
    layout="centered",
    initial_sidebar_state="expanded"
)

if 'user_id' not in st.session_state:
    st.session_state.user_id = 0

if 'conn' not in st.session_state:
    # Create the SQL connection to configs_db as specified in your secrets file.
    st.session_state.conn = st.connection('profile_db', type='sql')

# Insert some data with conn.session.
with st.session_state.conn.session as s:
    s.execute(text('CREATE TABLE IF NOT EXISTS user (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, password TEXT);'))
    s.execute(text('CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT UNIQUE, value TEXT, description TEXT, user_id,FOREIGN KEY (user_id) REFERENCES user(id));'))

    s.execute(
        text('INSERT OR IGNORE INTO user (id, name, password) VALUES (:id, :name, :password);'),
        params=dict(id=st.session_state.user_id, name='admin', password='123456')
    )

    s.commit()

st.subheader(':hammer_and_wrench: Profile', divider='gray')
st.text('You can derictly modify the Profile table, and save it by click the button below')

def get_profile():
    with st.session_state.conn.session as s:
        profile = s.execute(text('select * from profile where user_id = :user_id'),
                    params=dict(user_id=st.session_state.user_id))
        s.commit()

    return pd.DataFrame(profile.all())


profile = pd.DataFrame(get_profile())
if len(profile) == 0:
    profile = pd.DataFrame(columns=['id', 'key', 'value', 'description', 'user_id'])

edited_profile = st.data_editor(profile, 
                                column_config={
                                    'id':None, 
                                    'user_id':None, 
                                    'key':st.column_config.TextColumn('Key', required=True), 
                                    'value':st.column_config.TextColumn('Value'), 
                                    'description':st.column_config.TextColumn('Description')}, 
                                num_rows='dynamic', 
                                disabled=['id', 'user_id'], 
                                use_container_width=True)

edited_profile['user_id'] = st.session_state.user_id

if st.button('Save'):
    if not profile.equals(edited_profile):
        if not edited_profile['key'].is_unique:
            st.warning('Key should be unique')
        elif edited_profile['key'].isnull().any() or edited_profile['value'].isnull().any():
            st.warning('Key and Value should not be empty')
        else:
            with st.session_state.conn.session as s:
                s.execute(text('DELETE FROM profile where user_id = :user_id'),
                        params=dict(user_id=st.session_state.user_id))

                for index, row in edited_profile.iterrows():
                    s.execute(
                        text('INSERT INTO profile (key, value, description, user_id) VALUES (:key, :value, :description, :user_id);'),
                        params=dict(key=row['key'], value=row['value'], description=row['description'], user_id=st.session_state.user_id)
                    )
                s.commit()
            st.success('Profile saved', icon="✅")
    else:
        st.info('Profile not changed')
