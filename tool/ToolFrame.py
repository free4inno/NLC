import gradio as gr
import json
import requests

def submit_tool_info(Tname, Taddress, Tdescription, Tparameters):
    tool_info = {
        "Tname": Tname,
        "Taddress": Taddress,
        "Tdescription": Tdescription,
        "Tparameters": Tparameters
    }
    tool_info_json = json.dumps(tool_info, ensure_ascii=False)

    response = requests.post("http://127.0.0.1:5000/register", json=tool_info)

    if response.status_code == 200:
        return "register tool success", tool_info_json
    else:
        return "fail to register tool", tool_info_json

def get_all_tools():
    response = requests.get("http://127.0.0.1:5000/tools")

    if response.status_code == 200:
        return json.dumps(response.json(), indent=4, ensure_ascii=False)
    else:
        return "fail to get tool info"

def delete_tool(tool_id):
    response = requests.delete(f"http://127.0.0.1:5000/delete_tool/{tool_id}")

    if response.status_code == 200:
        return "The tool was deleted successfully!"
    else:
        return "Tool deletion failed!"

with gr.Blocks() as demo:
    gr.Markdown("### Regester Tool")
    with gr.Row():
        Tname = gr.Textbox(label="Tname")
        Taddress = gr.Textbox(label="Taddress")
    with gr.Row():
        Tdescription = gr.Textbox(label="Tdescription")
        Tparameters = gr.Textbox(label="Tparameters")
    submit_button = gr.Button("Submit")
    output = gr.Textbox(label="Result", interactive=False)
    output_json = gr.Textbox(label="Submitting Info (JSON)", interactive=False)

    submit_button.click(fn=submit_tool_info,
                        inputs=[Tname, Taddress, Tdescription, Tparameters],
                        outputs=[output, output_json])

    get_all_button = gr.Button("Get all tools information")
    all_tools_output = gr.Textbox(label="Tools:", interactive=False)

    get_all_button.click(fn=get_all_tools,
                         outputs=[all_tools_output])

    with gr.Row():
        tool_id_input = gr.Textbox(label="Tool ID for Deletion")
        delete_button = gr.Button("Delete Tool")
    delete_output = gr.Textbox(label="Deletion Results", interactive=False)

    delete_button.click(fn=delete_tool,
                        inputs=[tool_id_input],
                        outputs=[delete_output])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0",server_port=5010)