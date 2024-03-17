import openai
from flask import Flask, request, jsonify

import json
import os
import requests
from configparser import ConfigParser


class Plan:
    def add_subtask(self, goal):
        self.subtasks.append({'goal':goal})

    def __init__(self) -> None:
        self.subtasks = []

class PlanningCapability:
    def __init__(self) -> None:
        # load config
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")
        cf = ConfigParser()
        cf.read(file_path, encoding='utf-8')
        openai.api_base = cf.get('openai', 'api_base')
        openai.api_key = cf.get('openai', 'api_key')
        
        self.max_attempt_num = 1
    
    def generate_plan(self, task_description:str) -> list[dict]:
        # search methodology
        methodology_list = self.search_methodology(task_description)

        print(f"[Task Description]\n{task_description}\n\n")
        print(f"[Methodology List]\n{methodology_list}\n\n")

        # design plan
        for attempt in range(1,self.max_attempt_num + 1):
            plan_text = self.design_plan(methodology_list, task_description)
            print(f"[Plan Text]\n{plan_text}")

            try:
                plan_list = json.loads(plan_text)
                if not(isinstance(plan_list, list)):
                    raise json.JSONDecodeError(msg = "plan_list should be: list[dict]")

                for subtask in plan_list:
                    if not isinstance(subtask, dict):
                        raise json.JSONDecodeError(msg = "subtask shoud be dict type: {subtask_description, type, profile}}")
                    elif  'subtask_description' not in subtask or not isinstance(subtask['subtask_description'], str):
                        raise json.JSONDecodeError(msg = "subtask_description not found, or shoud be str")
                    elif  'type' not in subtask or not isinstance(subtask['type'], str):
                        raise json.JSONDecodeError(msg = "type not found, or shoud be str")
                    elif  subtask['type'] == 'profile' and not isinstance(subtask['profile'], list):
                        raise json.JSONDecodeError(msg = "profile not found, or shoud be list[str]")
                
                print(f"[Design Plan]\n{plan_list}")
                return plan_list
                
            except Exception as e:
                print(f"[Design Plan] format error: {e}, attempt = {attempt}")

        # if error
        return []
    
    def search_methodology(self, task_description:str):
        try :
            payload = {'task_description': task_description}
            response = requests.post('http://127.0.0.1:8003/search_methodology', json=payload)
            methodoloy_list = response.json()
        except Exception as e:
            methodoloy_list
            print(f"[Err] search_methodology: {e}") 

        return methodoloy_list

    def design_plan(self, metodology_list: str, task_description:str):
        prompt = f"""
You are an expert at specifying a plan, and you need to create a detailed list of plans based on the problem and reference methodology 

The format of the reference method is: Methedology={{ScenarioDescription,ProcessStep[StepDetails],DecisionPoint,Rules,ExceptionHandling,Recommendestions, Reference Materials}}
The meaning of each of these elements is as follows:
ScenarioDescription:Description of the application scenario
ProcessStep: Process step, defines each step of the process
DecisionPoint: Decision point, defines the key decision point in the process and its decision logic
Rules: Conditions and rules that affect the process path or step execution
ExceptionHandling: Exception handling, describes how to handle exceptions or errors that may occur in the process
Recommendations: Optimizations and recommendations
ReferenceMaterials: Documentation and references

You should answer in a json list format where each element of the list is a dictionary object {{subtask_description, type, profile}}, the elements of dict are as follows:   
subtask_description: the description of this subtask in as much detail as possible in conjunction with the reference methodology
profile: in some subtask there are 'profile macros' in the format: {{{{ value }}}}, you MUST collect the 'value' in the text and organize them into a list, e.g. if there are two macros in the text, {{{{ text_abc }}}} and {{{{ action_type }}}}, then the list would be ["text_abc", "action_type"], if there are no macro, then this field is [].
type: the task type of this subtask, limited to "tool" and "profile", when the profile macros is needed in the subtask, then it is "profile", otherwise it's "tool"

The final answer is formatted as [{{subtask_description:(string, such as "Step 1:..."), type:(string enumeration type, limited to "tool" and "profile", when the profile element list is not empty, then it is "profile", otherwise it's "tool"), profile:(list of string, such as ["...", "..."], if there are no macro, then this field does not need to be written out)}}, ...] 

The problem to be solved is:  
{task_description}

Possibly useful reference methods are as follows:  
{metodology_list}

Give your answer:
"""
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
        return completion.choices[0].message.content
    

    def generate_info(self, instruction:str, task_list:str) -> list[dict]:
        # design plan
        for attempt in range(1,self.max_attempt_num + 1):
            try:
                prompt = f"""
You are an expert at summarizing the information given below:
Problems raised by users:
{instruction}
Workflow for solving the problem:
{task_list}

Based on the above information, you need to come up with an easy-to-understand name for this workflow
Also, briefly summarize the functionality of the workflow in a paragraph of text. You MUST give the result in JSON format like:
{{
    "name": "..." ,
    "description": "..."
}}

Give your answer:
"""
                completion = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])

                print(completion.choices[0].message.content)

                info = json.loads(completion.choices[0].message.content)
                name = info["name"]
                description = info["description"]

                if not name or not(isinstance(name, str)):
                    raise json.JSONDecodeError(msg = "name should be: str")

                if not description or not(isinstance(description, str)):
                    raise json.JSONDecodeError(msg = "description should be: str")
                
                print(f"[Design Info]: {name}\n{description}")
                return name, description
                
            except Exception as e:
                print(f"[Design Info] format error: {e}, attempt = {attempt}")

        # if error
        return "", ""
    

app = Flask(__name__)
pc = PlanningCapability()

@app.route('/generate_plan', methods=['POST'])
def generate_plan_route():
    """
    POST

    JSON Args:
        {'task_description': str}

    Return:
        {'plan': list[str]}
    """

    # get argument: task_description
    data = request.get_json()
    task_description = data.get('task_description', '')
    if not task_description:
        return jsonify({'error': 'Task description is required'}), 400

    # plan: list[str]
    plan = pc.generate_plan(task_description)
    if len(plan) == 0:
        return jsonify({'plan': plan})
    
    return jsonify({'plan': plan})

@app.route('/generate_info', methods=['POST'])
def generate_info():
    """
    POST

    JSON Args:
        {'task_list': str, 'instruction': str}

    Return:
        {'name': str, 'description': str}
    """

    # get argument: task_description
    data = request.get_json()
    instruction = data.get('instruction', '')
    task_list = data.get('task_list', '')
    if not instruction or not task_list:
        return jsonify({'error': 'task description or task_list is required'}), 400

    print(f"[To Generate]\n{instruction}\n\n{task_list}\n")

    name, description = pc.generate_info(instruction, task_list)
    if name == "" or description == "":
        return jsonify({'error': 'generate info failed'}), 400
    return jsonify({'name': name, 'description': description})

if __name__ == "__main__":
    app.run(debug=True, port=8002)
    pass