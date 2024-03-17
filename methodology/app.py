import gradio as gr
from fastapi import FastAPI
import uvicorn
import methodology_capability
from model import MethedologyInfo

mc =  methodology_capability.MethodologyCpability()

def add_methodology_callback(scenario_description_text: str, 
                             process_steps_text: str,
                             decision_points_text: str, 
                             rules_text: str,
                             exception_handling_text: str,
                             suggestions_text: str,
                             reference_materials_text: str):

    new_methedology = MethedologyInfo(scenario_description = scenario_description_text, 
                             process_steps = process_steps_text,
                             decision_points = decision_points_text,
                             rules = rules_text,
                             exception_handling = exception_handling_text,
                             suggestions = suggestions_text,
                             reference_materails = reference_materials_text)

    result = mc.insert(new_methedology)
    if result:
        print(f"[Add] new info")
        gr.Info('Add successful')
    
    return mc.list_all(), gr.Dropdown(choices=mc.list_id(), label="ID", value=None), "", "", "", "", "", "", ""

def delete_text_callback(id):
    if id == []:
        return mc.list_all(), gr.Dropdown(choices=mc.list_id(), label="ID", value=None)
    
    result = mc.delete(id)
    if result:
        gr.Info('Delete successful')
    return mc.list_all(), gr.Dropdown(choices=mc.list_id(), label="ID", value=None)

with gr.Blocks() as demo:
    gr.Markdown(
    """
    # Methodology Capability
    """)
    
    table = gr.DataFrame(headers=['ID', 'ScenarioDescription', 'ProcessSteps', 'DecisionPoints', 'Rules', 
                                  'ExceptionHandling', 'Suggestions', 'ReferenceMaterials'],
                         datatype=["str", "str", "str", "str", "str", "str", "str", "str"],
                         value=mc.list_all(),
                         wrap = True)

    # Delete
    with gr.Row():
        drop = gr.Dropdown(choices=mc.list_id(), label="ID")
        btn_delete = gr.Button("Delete")
        btn_delete.click(delete_text_callback, inputs=[drop], outputs=[table, drop])

    # Add
    scenario_description_text_box = gr.Textbox(label="Scenario",placeholder="Add your scenario description:")
    process_steps_text_box = gr.Textbox(label="Process Steps",placeholder="Add your process steps:")
    decision_points_text_box = gr.Textbox(label="Decision Points",placeholder="Add your decision points:")
    rules_text_box = gr.Textbox(label="Rules",placeholder="Add your rules:")
    exception_handling_text_box = gr.Textbox(label="Exception Handling",placeholder="Add your exception handling:")
    suggestions_text_box = gr.Textbox(label="Suggestions",placeholder="Add your suggestions:")
    reference_materials_text_box = gr.Textbox(label="Reference Materials",placeholder="Add your reference materials:")

    btn_add = gr.Button("Submit")
    btn_add.click(add_methodology_callback, 
                inputs=[
                    scenario_description_text_box, 
                    process_steps_text_box,
                    decision_points_text_box, 
                    rules_text_box,
                    exception_handling_text_box,
                    suggestions_text_box,
                    reference_materials_text_box], 
                outputs=[
                    table, 
                    drop, 
                    scenario_description_text_box, 
                    process_steps_text_box,
                    decision_points_text_box, 
                    rules_text_box,
                    exception_handling_text_box,
                    suggestions_text_box,
                    reference_materials_text_box])


app = FastAPI()

@app.post('/search_methodology')
def search_methodology(data: dict):
    """
    POST

    JSON Args:
        {'task_description': str}

    Return:
        {'methodoloy_list': list[str]}
    """
    # get task_description
    task_description = data['task_description']
    if not task_description:
        return {'error': 'Task description is required'}, 400
    
    # call search_methodology
    methodoloy_list = mc.search_methodology(task_description)
    print(f"task_description:{task_description}\nmethodoloy_list.len={len(methodoloy_list)}")
    return {'methodoloy_list': methodoloy_list}

app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == '__main__':
    uvicorn.run(app="app:app", host="0.0.0.0", port=8003, reload=True)