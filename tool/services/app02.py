from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import requests  # 用于发送心跳请求

app = Flask(__name__)

# 心跳发送函数
def send_heartbeat():
    try:
        response=requests.post("http://127.0.0.1:5011/heartbeat", json={"service_id": "2"})
        if response.status_code == 200:
            pass
        else:
            print("fail to heartbeat")
    except requests.RequestException:
        pass


@app.route('/heartbeat_check', methods=['GET'])
def heartbeat_check():
    return '', 200

@app.route('/HighSpeedRailPriceSorter', methods=['POST'])
def HighSpeedRailPriceSorter():
    data = request.get_json()

    # home_city = data.get('home_city')
    # city_list = data.get('city_list')

    home_city = ""
    city_list = ""

    for d in data:
        if "name" in d:
            if "home_city" == d["name"]:
                home_city = d["value"]
            if "city_list" == d["name"]:
                city_list = d["value"]
    
    if home_city == "" or city_list == "":
        return jsonify([])

    if home_city.lower() == 'beijing':
        city_list_value = 'Langfang, Zhuozhou, Tianjin, Baoding, Bazhou, Tangshan'
    elif home_city.lower() == 'shanghai':
        city_list_value = 'Jiaxing, Suzhou, Nantong, Hangzhou, Huzhou, Changzhou, Ningbo'
    else:
        city_list_value = 'No cities found'

    response = {
        'data': [
            {
                'name': 'city_list',
                'description': f'sort the HSR fares from the selected cities to the {{ home_city }} (from lowest to highest)',
                'value': city_list_value
            }
        ]
    }

    return jsonify(response)


scheduler = BackgroundScheduler()
scheduler.add_job(func=send_heartbeat, trigger="interval", minutes=0.1)
scheduler.start()

if __name__ == '__main__':
    app.run(debug=True, port=5008)