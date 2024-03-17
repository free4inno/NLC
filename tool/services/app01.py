from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import requests

app = Flask(__name__)

def send_heartbeat():
    try:
        response=requests.post("http://127.0.0.1:5011/heartbeat", json={"service_id": "1"})
        if response.status_code == 200:
            pass
        else:
            print("fail to heartbeat")
    except requests.RequestException as e:
        print(f"fail to heartbeat: {e}")

@app.route('/heartbeat_check', methods=['GET'])
def heartbeat_check():
    return '', 200

@app.route('/NearbyCityFinder', methods=['POST'])
def NearbyCityFinder():
    data = request.get_json()

    home_city = ""
    target_distance = ""

    for d in data:
        if "name" in d:
            if "home_city" == d["name"]:
                home_city = d["value"]
            if "target_distance" == d["name"]:
                target_distance = d["value"]
                
    if home_city == "" or target_distance == "":
        return jsonify([])

    if home_city.lower() == 'beijing':
        city_list_value = 'Langfang, Zhuozhou, Tianjin, Baoding, Bazhou, Tangshan'
    elif home_city.lower() == 'shanghai':
        city_list_value = 'Nantong, Hangzhou, Suzhou, Ningbo, Huzhou, Changzhou, Jiaxing'
    else:
        city_list_value = 'No cities found'

    response = {
        'data': [
            {
                'name': 'city_list',
                'description': f'Query cities less than {{target_distance}} kilometers away from the {{ home_city }}',
                'value': city_list_value
            }
        ]
    }

    return jsonify(response)


scheduler = BackgroundScheduler()
scheduler.add_job(func=send_heartbeat, trigger="interval", minutes=0.1)
scheduler.start()


if __name__ == '__main__':
    app.run(debug=True, port=5007)
