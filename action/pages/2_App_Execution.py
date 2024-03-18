import streamlit as st
import pandas as pd
import json, requests, traceback

from sqlalchemy.orm import joinedload
from model import App, Task, session_factory

st.set_page_config(
    page_title="App Execution",
    page_icon="🚀",
    layout="centered",
    initial_sidebar_state="expanded"
)

def get_app(id: str)->App:
    with session_factory.begin() as session:
        app = session.query(App).filter(App.id == id).options(joinedload(App.tasks).subqueryload(Task.args)).first()

    return app

def on_change_editor():
    pass

def run_app(app:App, edited_profile_list:pd.DataFrame):
    # cache
    profile_cache=dict()
    tool_cache=dict()

    # profile
    for _, row in edited_profile_list.iterrows():
        profile_cache[row["name"]] = dict(name=row["name"], description=row["description"], value=row["value"])
    
    # for every task
    task_list = app.tasks
    task_list.sort(key=lambda x : x.task_id)
    result_list = []
    for task in task_list:
        arg_list = []

        # gather arg list
        for arg in task.args:
            if arg.type == "profile":
                if arg.name in profile_cache:
                    arg_list.append(profile_cache[arg.name])
                else:
                    pass
            elif arg.type == "tool":
                if arg.name in tool_cache:
                    arg_list.append(tool_cache[arg.name])
                else:
                    pass
            elif arg.type == "fix":
                 arg_list.append(dict(name=arg.name, description=arg.description, value=arg.value))
        
        # invoke tool
        if task.type == "profile":
            result_list.append(arg_list)
        elif task.type == "tool":
            response, msg, ok = invoke_tool(playload=arg_list, url=task.address)
            if not ok:
                pass
            for tool_result in response:
                tool_cache[tool_result["name"]] = tool_result
            result_list.append(response)
        else:
            pass
    
    st.session_state.run_result = dict(task_list=task_list, result_list=result_list)
    st.session_state.run_app = True

    return task_list, result_list

def invoke_tool(url:str, playload:list[dict]):
    response = requests.post(url, json=playload)

    try:
        json_data = response.json()
        if type(json_data) == str:
            json_data = json.loads(json_data)

        output_list = []
        if type(json_data) == 'str' or json_data == []:
            return  output_list, f"invoke tool failed, tool response = {json_data}", False
        
        data = json_data['data']
        if not data:
            raise json.JSONDecodeError(msg = "data not found")
        elif not isinstance(data, list):
            raise json.JSONDecodeError(msg = "data format shoud be list[dict]")

        for d in data:
            if 'name' not in d or not isinstance(d['name'], str):
                raise json.JSONDecodeError(msg = f"{d}: data.name not found, or shoud be str")
            elif 'value' not in d or not isinstance(d['value'], str):
                raise json.JSONDecodeError(msg = f"{d}: data.value not found, or shoud be str")
            elif 'description' not in d or not isinstance(d['description'], str):
                raise json.JSONDecodeError(msg = f"{d}: data.description not found, or shoud be str")
            output_list.append(dict(name = d['name'], value = d['value'], description = d['description'], type = 'tool'))
            break

        print(f"\n[Invoke Tool]\nURL={url}\nplayload={playload}\nresponse={json_data}")

        return output_list, '', True
        
    except Exception as e:
        print(traceback.format_exc())
        return [], f"{e}", False
    

# st.subheader(':rocket: Running', divider='gray')

if 'app_id' not in st.session_state:
    st.session_state.app_id = None

if 'run_app' not in st.session_state:
    st.session_state.run_app = False

if 'run_result' not in st.session_state:
    st.session_state.run_result = dict()

if None == st.session_state.app_id:
    st.page_link("pages/1_App_Script_Store.py", label=":card_index_dividers: App Script Store", use_container_width=True)
else:
    app = get_app(st.session_state.app_id)
    if None == app:
        st.page_link("pages/1_App_Script_Store.py", label=":card_index_dividers: App Store", use_container_width=True)
    else:
        # with st.chat_message("ai"):
        # st.write(f":pushpin: App Name")
        # st.write(f"{app.name}")
        st.subheader(f':rocket: {app.name}', divider='gray')


        st.write(f":information_source: Introduction")
        st.write(f"{app.description}")

        st.write(f":white_check_mark: Tasks")
        tasks_list = [f"Task {i+1}: "+task.description+"  " for i, task in enumerate(app.tasks)]
        tasks_list = "\n".join(tasks_list)
        st.markdown(tasks_list)

        
        st.write(f":hammer_and_wrench: Configuration")
        profile_list = eval(app.profile_list)
        df = pd.DataFrame(
            [
                {"name": profile["name"], "description": profile["description"], "value": ""} for profile in profile_list
            ]
        )
        edited_profile_list = st.data_editor( 
            df, 
            column_config={
                'name':None, 
                'description':st.column_config.TextColumn('Description', required=True), 
                'value':st.column_config.TextColumn('Value', required=True)
            },
            disabled=['id', 'name', 'description'], 
            use_container_width=True,
            hide_index=True
        )
        
        st.button(":rocket: Run", on_click=run_app, args=[app, edited_profile_list])

        st.divider()

if True == st.session_state.run_app:
    st.write(f":bookmark_tabs: Running logs")

    task_list = st.session_state.run_result["task_list"]
    result_list = st.session_state.run_result["result_list"]

    ans = ""
    for (i, task) in enumerate(task_list):
        ans += f"Task {i+1}: {task.description}  \n"
        ans += f"Result: {result_list[i][0]['value']}\n\n"
    st.write(ans)

    st.write(f":ok: Running Result")
    st.write(f"{result_list[-1][0]['value']}")