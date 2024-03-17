from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import requests

app = Flask(__name__)

def send_heartbeat():
    try:
        response=requests.post("http://127.0.0.1:5011/heartbeat", json={"service_id": "3"})
        if response.status_code == 200:
            pass
        else:
            print("fail to heartbeat")
    except requests.RequestException:
        pass

@app.route('/heartbeat_check', methods=['GET'])
def heartbeat_check():
    return '', 200


@app.route('/WeatherFit', methods=['POST'])
def WeatherFit():
    data = request.get_json()

    # city_list = data.get('city_list')
    city_list = ""

    for d in data:
        if "name" in d:
            if "city_list" == d["name"]:
                city_list = d["value"]
    
    if city_list == "":
        return jsonify([])
    
    print(city_list)

    if 'Tianjin' in city_list:
        city_list_value = 'Tianjin, Langfang, Zhuozhou'
    elif 'Ningbo' in city_list:
        city_list_value = 'Nantong, Hangzhou, Ningbo'
    else:
        city_list_value = 'No cities found'

    response = {
        'data': [
            {
                'name': 'city_list',
                'description': f'Filter out cities that are unsuitable for travelling based on weather conditions',
                'value': city_list_value
            }
        ]
    }

    return jsonify(response)

scheduler = BackgroundScheduler()
scheduler.add_job(func=send_heartbeat, trigger="interval", minutes=0.1)
scheduler.start()

if __name__ == '__main__':
    app.run(debug=True, port=5009)
