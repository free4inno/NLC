from flask import Flask, request
import datetime
import requests
from apscheduler.schedulers.background import BackgroundScheduler
import sqlite3
import os

app = Flask(__name__)

services_status01 = {}
services_status02 = {}

DATABASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools.db')

def get_services_from_db():
    connection = sqlite3.connect(DATABASE_FILE)
    cursor = connection.cursor()
    cursor.execute("SELECT id, address FROM Tool")
    services = cursor.fetchall()
    connection.close()
    return services

@app.route('/heartbeat', methods=['POST'])
def receive_heartbeat():
    data = request.get_json()
    service_id = data.get("service_id")
    services_status01[service_id] = datetime.datetime.now()
    print(services_status01)
    return "heartbeat", 200

def send_heartbeat_check(service_id, address):
    try:
        response = requests.get(f"{address}/heartbeat_check")
        return response.status_code == 200
    except requests.RequestException:
        return False


def update_service_status(service_id, status):
    tool_status = {
        "tool_id": service_id,
        "status": status
    }
    response = requests.post("http://127.0.0.1:5000/update_status", json=tool_status)
    return response.status_code


def check_services_status01():
    now = datetime.datetime.now()
    for service_id, last_heartbeat in services_status01.items():
        if (now - last_heartbeat).total_seconds() > 10:
            print(f"{service_id} : disconnected")
            response = update_service_status(service_id, 'false')
            print(response)
        else:
            response = update_service_status(service_id, 'true')
            print(response)

def check_services_status02():
    services = get_services_from_db()
    now = datetime.datetime.now()
    for service_id, address in services:
        alive = send_heartbeat_check(service_id, address)
        last_status = services_status02.get(service_id, {"last_checked": None, "fail_count": 0})

        if alive:
            services_status02[service_id] = {"last_checked": now, "fail_count": 0}
            update_service_status(service_id, 'true')
        else:
            print(f"Service Invalid, ID = {service_id} ")
            fail_count = last_status["fail_count"] + 1
            services_status02[service_id] = {"last_checked": now, "fail_count": fail_count}

            if fail_count >= 3: 
                update_service_status(service_id, 'false')



scheduler = BackgroundScheduler()
scheduler.add_job(func=check_services_status01, trigger="interval", minutes=1)
scheduler.add_job(func=check_services_status02, trigger="interval", minutes=0.1)
scheduler.start()

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=5011)
