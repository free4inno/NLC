import uuid
import json
import requests
import pandas as pd
import traceback

from model import App, Task, Arg, session_factory
from sqlalchemy.sql import text
import streamlit as st

st.set_page_config(
    page_title="App Creation/Releasing",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded"
)

if 'user_id' not in st.session_state:
    st.session_state.user_id = 0

if 'conn' not in st.session_state:
    st.session_state.conn = st.connection('profile_db', type='sql')

class WorkflowCapability:
    def __init__(self) -> None:
        self.workflows = {}
        self.reception_url = 'http://127.0.0.1:8001'
        self.planning_url = 'http://127.0.0.1:8002'
        self.tool_url = 'http://127.0.0.1:5000'

    def init_workflow(self, request:str):
        workflow_id = uuid.uuid4()
        workflow = Workflow(workflow_id, request)
        print(f"[New Wrokflow] {workflow_id}\n")

        # run workflow
        ok, message = workflow.run()
        self.workflows[workflow_id] = workflow

        return ok, message, workflow_id
    
    def save_app(self, workflow_id: uuid.UUID):
        if workflow_id not in self.workflows:
            return False, f"Workflow(id = {workflow_id}) not found", ""
        workflow = self.workflows[workflow_id]

        # build App
        ok, app_name, app_description = workflow.get_app_info()
        if not ok:
            return False, "Save App failed", ""
        app = App(
            id = str(workflow.workflow_id),
            name = app_name,
            description = app_description,
            profile_list = workflow.profile,
            tasks = workflow.task_list
        )

        # save to db
        with session_factory.begin() as session:
            session.add(app)

        self.workflows.pop(workflow.workflow_id)

        return True, app_name, app_description
    
    def fake_app(self):
        workflow_id = uuid.uuid4()
        workflow = Workflow(workflow_id, "I want to go to a nearby city with my family this vacation, can you help me find some suitable cities?")
        workflow.task_list = [
            Task(task_id=0, description='Search for {{ home_city }}', type='profile', 
                 address='', 
                args = [
                    Arg(type='profile', name='home_city', description='City of home', value='')
                ]),
            Task(task_id=1, description='Query cities less than 200 kilometers away from the home city', type='tool', 
                 address='http://127.0.0.1:5007/NearbyCityFinder',
                args = [
                    Arg(type='profile', name='home_city', description='City of home', value=''),
                    Arg(type='fix', name='target_distance', description='Maximum distance to target city', value='200')
                ]),
            Task(task_id=2, description='Sort the HSR fares from the selected cities to the home city (from lowest to highest)', type='tool', 
                 address='http://127.0.0.1:5008/HighSpeedRailPriceSorter',
                args = [
                    Arg(type='profile', name='home_city', description='City of home', value=''),
                    Arg(type='tool', name='city_list', description='')
                ]),
            Task(task_id=3, description='Excluding cities with adverse weather during the travel period', type='tool', 
                 address='http://127.0.0.1:5009/WeatherFit',
                args = [
                    Arg(type='tool', name='city_list', description='sort the HSR fares from the selected cities (Langfang, Zhuozhou, Tianjin, Baoding, Bazhou, Tangshan) to the home city(Beijing) (from lowest to highest)', value='')
                ])
        ]
        workflow.profile = str([{'name': 'home_city', 'description': 'city of home'}])

        self.workflows[workflow_id] = workflow
        return workflow_id

class Workflow(WorkflowCapability):
    def __init__(self, workflow_id: uuid.UUID, task_description: str) -> None:
        super().__init__()
        self.workflow_id = workflow_id
        self.task_description = task_description
        self.task_list: list[Task] = []
        self.profile: list[str] = []
        self.invoke_result_list = []

    def run(self):
        print(f"[Run] {self.workflow_id}\n")
        plan = self.get_plan()
        return self.workflow(plan)

    def get_plan(self):
        payload = {'task_description': self.task_description}
        response = requests.post(self.planning_url + '/' + 'generate_plan', json=payload)
        json_data = response.json()
        plan = json_data['plan']

        if not plan:
            print(f"[Plan]: plan not found in json body")

        print(f"[Plan]: {plan}\n")
        return plan
    
    def get_app_info(self):
        payload = {'task_list': [t.__repr__() for t in self.task_list], 'instruction': self.task_description}
        response = requests.post(self.planning_url + '/' + 'generate_info', json=payload)

        if (response.status_code == 400):
            return False, "", ""
        
        json_data = response.json()
        app_name = json_data['name']
        app_description = json_data['description']

        if not app_name:
            print(f"[Plan]: app.name not found in json body")
        elif not app_description:
            print(f"[Plan]: app.description not found in json body")

        print(f"[App Info] \nApp Name:\n{app_name}\nDescription: \n{app_description}")
        return True, app_name, app_description
    
    def workflow(self, plan_list:list[dict]) -> tuple[bool,str]:
        # plan capability error
        if len(plan_list) == 0:
            return False, "Sorry, I can't solve this question ..."
        
        profile_cache = dict()
        tool_cache = dict()

        # subtask: {subtask_description, type, profile}
        for (i, subtask) in enumerate(plan_list):
            short_term_memory = [profile_cache[p_name] for p_name in profile_cache]
            short_term_memory.extend([tool_cache[t_name] for t_name in tool_cache])
            print(f"[Task {i + 1}] {subtask}\nshort_term_memory: { short_term_memory }\n")

            if subtask['type'] == 'profile':
                # profile: list[{name: str, value: str, description: str}]
                profile_list = self.get_profile(subtask['profile'])
                print(f"[Profile]\n{profile_list}\n")

                # profile cache(type=profile)
                arg_list = []
                for p in profile_list:
                    profile_cache[p["name"]] = p
                    a = Arg(
                        name = p['name'],
                        value = p['value'],
                        description = p['description'],
                        type = 'profile',
                    )
                    arg_list.append(a)
                
                # invoke result
                # self.invoke_result_list.append(profile_list)
                result = ""
                if len(profile_list) > 0:
                    result = profile_list[0]["value"]
                self.invoke_result_list.append(dict(result=result, tool_name = "Profile"))

                # save task
                task = Task(
                    task_id = i,
                    description = subtask['subtask_description'],
                    type = 'profile',
                    address = "",
                    args = arg_list,
                )
                self.task_list.append(task)

            elif subtask['type'] == 'tool':
                # discover tool
                tool_info, arg_list, message, ok = self.discover_tool(subtask['subtask_description'], short_term_memory)
                
                print(f"[Discover Tool]\nstatus: { ok }\ntool_info: { tool_info }\nmessage: { message }\n")
                if not ok:
                    return False, f"{message}\n task description: {subtask['subtask_description']}"
                
                # invoke tool
                data, message, ok = self.invoke_tool(tool_info)
                print(f"[Invoke Tool]\nstatus: { ok }\ndata: {data}\nmessage: {message}\n")
                if not ok:
                    return False, message
                
                # tool cache(type=tool)
                for d in data:
                    tool_cache[d["name"]] = d
                
                result = ""
                if len(data) > 0:
                    result = data[0]["value"]
                # invoke result
                self.invoke_result_list.append(dict(result=result, tool_name = tool_info["tool_name"]))

                # save task
                task = Task(
                    task_id = i,
                    description = subtask['subtask_description'],
                    type = 'tool',
                    address = tool_info['url'],
                    args = arg_list,
                )
                self.task_list.append(task) 
            
            else:
                print("subtask.type not correct\n")
                return False, "Internal Error: subtask.type not correct\n"

        # save profile_list
        self.profile = str([{'name': profile_cache[p]["name"], 'description': profile_cache[p]["description"]} for p in profile_cache])

        # answer
        ans = ""
        for (i, task) in enumerate(self.task_list):
            ans += f"Task {i+1}: {task.description}  \n"
            ans += f"Tool: {self.invoke_result_list[i]['tool_name']}  \n"
            ans += f"Result: {self.invoke_result_list[i]['result']}\n\n"
        ans += (f"\n\nFinal Anwser: {self.invoke_result_list[-1]['result']}\n")
        
        return True, ans
    
    def get_profile(self, key_list: list[str]):
        profile_list = []
        with st.session_state.conn.session as s:
            for key in key_list:
                profile = s.execute(text('select key, value, description from profile where key = :key and user_id = :user_id'),
                            dict(key = key, user_id = st.session_state.user_id))
            s.commit()

            df = pd.DataFrame(profile.all())
        
            for _, row in df.iterrows():
                profile_list.append(dict(name = row['key'], value = row['value'], description = row['description'], type = 'profile'))
                break

        return profile_list

    """
    request:
        {'description': str, 'params': list[dict]}
    response:  
        {
            Matched: true/false
            Status: true/false
            "Interface ID",
            "Interface Name",
            "Interface Address",
            "Interface Description",
            "Interface Parameters": {
                key: value,
                ...
            }
        }
    """
    def discover_tool(self, subtask_description: str, short_term_memory: list[dict]) -> tuple[dict, str, bool]:
        payload = {'description': subtask_description, 'params': short_term_memory}
        response = requests.post(self.tool_url + '/discover_tool', json=payload)

        try:
            json_data = json.loads(response.text)
            if type(json_data) == str:
                json_data = json.loads(json_data)

            matched = json_data['Matched']
            if not matched or matched == 'false':
                return {}, [], "No matching tool yet ...", False
            address = json_data['Interface Address']
            route = json_data['Interface Name']
            params = json_data['Interface Parameters']

            if not address or not route or not params:
                raise json.JSONDecodeError(msg = "[Discover Tool]: address/route/params not found in json body")
            if not isinstance(address, str) or not isinstance(route, str):
                raise json.JSONDecodeError(msg = "[Discover Tool]: address/route should be str")
            if not isinstance(params, list):
                raise json.JSONDecodeError(msg = "[Discover Tool]: params should be list")

            arg_list = []
            for arg in params:
                if 'name' not in arg or not isinstance(arg['name'], str):
                    raise json.JSONDecodeError(msg = f"{arg}: arg.name not found, or shoud be str")
                elif 'value' not in arg or not isinstance(arg['value'], str):
                    raise json.JSONDecodeError(msg = f"{arg}: arg.value not found, or shoud be str")
                elif 'description' not in arg or not isinstance(arg['description'], str):
                    raise json.JSONDecodeError(msg = f"{arg}: arg.description not found, or shoud be str")
                elif 'type' not in arg or not isinstance(arg['type'], str) or arg['type'] not in ['tool', 'profile', 'fix']:
                    raise json.JSONDecodeError(msg = f"{arg}: arg.type not found, or shoud be str, or must be of ('tool', 'profile', 'fix')")
                
                a = Arg(
                    name = arg['name'],
                    value = arg['value'],
                    description = arg['description'],
                    type = arg['type'],
                )
                arg_list.append(a)
            
            tool_info = dict(url = address + "/" + route, params=params, tool_name = route)
            return tool_info, arg_list, '', True
            
        except Exception as e:
            return {}, [], f"Discover tool error: {e}", False
    
    
    def invoke_tool(self, tool_info: dict):
        payload = tool_info['params']
        response = requests.post(tool_info['url'], json=payload)

        try:
            json_data = response.json()
            if type(json_data) == str:
                json_data = json.loads(json_data)

            # print(f"\n[Invoke Tool] json_data = {json_data}\ntype={type(json_data)}")

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
            return output_list, '', True
            
        except Exception as e:
            print(traceback.format_exc())
            return [], f"{e}", False


    def call_back_by_requestId(self) -> tuple[uuid.UUID, str]:
        return (self.workflow_id, "This is a call back message")

if 'workflow_capability' not in st.session_state:
    st.session_state.workflow_capability = WorkflowCapability()

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'workflow_id' not in st.session_state:
    st.session_state.workflow_id = uuid.uuid4()

if 'savable' not in st.session_state:
    st.session_state.savable = False

def on_save_app():
    ok, name, description = st.session_state.workflow_capability.save_app(st.session_state.workflow_id)
    if ok:
        st.session_state.chat_history.append({'name':'ai','chat':f'Successfully created app!\n\nName: {name}\n\n App Introduction: {description}'})

# if st.button('Fake Save'):
#     w_id = st.session_state.workflow_capability.fake_app()
#     ok, name, message = st.session_state.workflow_capability.save_app(w_id)
#     if ok:
#         st.success(message)
#     else:
#         st.warning(message)   

st.subheader(':robot_face: App Creation/Releasing', divider='gray')

for dialog in st.session_state.chat_history:
    with st.chat_message(dialog['name']):
        st.write(dialog['chat'])

prompt = st.chat_input("Say something to NLC")
if prompt:
    with st.chat_message("user"):
        user_chat = f"{prompt}"
        st.session_state.chat_history.append({'name':'user','chat':user_chat})
        st.write(user_chat)
    
    with st.chat_message("ai"):
        # Fake
        # workflow_id = st.session_state.workflow_capability.fake_app()
        # message="Task 1, Task 2, ..."
        # ok = True
        ok, message, workflow_id = st.session_state.workflow_capability.init_workflow(prompt)

        st.session_state.workflow_id = workflow_id
        
        ai_chat = f"{message}"
        st.session_state.chat_history.append({'name':'ai','chat':ai_chat})
        st.write(ai_chat)

        if ok:
            st.button('Save this workflow as an App?', on_click=on_save_app)