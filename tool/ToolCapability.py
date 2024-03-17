import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import discoverTool

app = Flask(__name__)
DATABASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DATABASE_FILE
db = SQLAlchemy(app)

app.debug = False

class Tool(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    address = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    parameters = db.Column(db.String(300), nullable=False)
    status = db.Column(db.String(50)) 

with app.app_context():
    db.create_all() 

@app.route('/register', methods=['POST'])
def register_tool():
    data = request.get_json()
    new_tool = Tool(
        name=data['Tname'],
        address=data['Taddress'],
        description=data['Tdescription'],
        parameters=data['Tparameters'],
        status='true'
    )
    db.session.add(new_tool)
    db.session.commit()
    return jsonify({"message": "register tool success!"}), 200

@app.route('/delete_tool/<int:tool_id>', methods=['DELETE'])
def delete_tool(tool_id):
    tool = Tool.query.get(tool_id)
    if tool:
        db.session.delete(tool)
        db.session.commit()
        return jsonify({"message": "工具删除成功!"}), 200
    else:
        return jsonify({"message": "工具未找到"}), 404

@app.route('/tools', methods=['GET'])
def get_tools():
    tools = Tool.query.all()
    return jsonify([{'id': tool.id, 'name': tool.name, 'address': tool.address, 'description': tool.description, 'parameters': tool.parameters, 'status': tool.status} for tool in tools]), 200

@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.get_json()
    tool_id = data.get("tool_id")
    new_status = data.get("status")

    tool = Tool.query.get(tool_id)
    if tool:
        tool.status = new_status
        db.session.commit()
        return jsonify({"message": "update status success!"}), 200
    else:
        return jsonify({"message": "cannot find tools"}), 404

@app.route('/discover_tool', methods=['POST'])
def discover_tool():
    data = request.get_json()
    print(data)
    
    ans = discoverTool.ask_question(data)
    
    return jsonify(ans), 200

if __name__ == '__main__':
    app.run(debug=True,port=5000)
