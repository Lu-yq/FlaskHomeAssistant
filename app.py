import json
from threading import Thread
from time import sleep

from flask import Flask, request, jsonify
from flask_mqtt import Mqtt

app = Flask(__name__)

app.config['MQTT_BROKER_URL'] = '106.14.255.17'
# app.config['MQTT_BROKER_URL'] = 'broker.emqx.io'
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_USERNAME'] = ''  # 当你需要验证用户名和密码时，请设置该项
app.config['MQTT_PASSWORD'] = ''  # 当你需要验证用户名和密码时，请设置该项
app.config['MQTT_KEEPALIVE'] = 5  # 设置心跳时间，单位为秒
app.config['MQTT_TLS_ENABLED'] = False  # 如果你的服务器支持 TLS，请设置为 True

topics = ['/fdse/lab/light/update01', '/fdse/lab/light/update02', '/fdse/lab/light/update03',
          '/fdse/lab/light/update04', '/fdse/lab/light/update05', '/fdse/lab/sensor/sun',
          "/fdse/lab/sensor/tem", "/fdse/lab/curtain/update", '/fdse/lab/heater/tem', '/fdse/lab/cooler/tem',
          "fdse/lab/heater_plus/update"]
data = dict(
    topic='',
    payload=''
)

queue = []

sun = 0
temperature = 20.0

light_state = False
air_condition_state = False
air_cooler_state = False
heater_state = False
curtain_state = False

mqtt_client = Mqtt(app)


def state(object_state):
    if object_state:
        return "on"
    else:
        return "off"


@mqtt_client.on_connect()
def handle_connect(client, userdata, flags, rc):
    if rc == 0:
        print('Connected successfully')
        for topic in topics:
            mqtt_client.subscribe(topic)
    else:
        print('Bad connection. Code:', rc)


@mqtt_client.on_message()
def handle_mqtt_message(client, userdata, message):
    global sun, temperature
    data['topic'] = message.topic
    data['payload'] = message.payload.decode()
    if data['topic'] == '/fdse/lab/light/update01' or data['topic'] == '/fdse/lab/light/update02' or data[
        'topic'] == '/fdse/lab/light/update03':
        update_sun_value(data)
    elif data['topic'] == '/fdse/lab/sensor/sun':
        sun = float(data['payload'])
    elif data['topic'] == '/fdse/lab/curtain/update':
        update_big_sun_value(data)
    elif data['topic'] == '/fdse/lab/sensor/tem':
        temperature = int(float(data['payload']))
    elif data['topic'] == '/fdse/lab/cooler/tem':
        # print(int(float(data['payload'])))
        queue.append(int(float(data['payload'])))
        print(queue)
    elif data['topic'] == '/fdse/lab/heater/tem':
        # print(int(float(data['payload'])))
        queue.append(int(float(data['payload'])))
        print(queue)
    elif data['topic'] == 'fdse/lab/heater_plus/update':
        # print(int(float(data['payload'])))
        queue.append(temperature + round((float(data['payload']) * 30 / 1000), 1))
        print(queue)
    print('Received message on topic: {topic} with payload: {payload}'.format(**data))


def update_sun_value(data):
    global sun

    if data['payload'] == 'on':
        print('开灯，光照强度增加200lux;')
        sun = sun + 200

    elif data['payload'] == "off":
        print('关灯，光照强度回到200lux初始状态;')
        sun = sun - 200
        if sun < 0:
            sun = 0
    return mqtt_client.publish('/fdse/lab/sensor/sun', sun)


def update_big_sun_value(data):
    global sun

    if data['payload'] == 'on':
        print('开窗帘，光照强度增加500lux;')
        sun = sun + 500

    elif data['payload'] == "off":
        print('关窗帘，光照强度降低500lux;')
        if sun - 500 > 0:
            sun = sun - 500
        else:
            sun = 0
    return mqtt_client.publish('/fdse/lab/sensor/sun', sun)


def update_temperature_value():
    # print("?")
    global temperature
    while 1:
        while len(queue) != 0:
            # print("doing")
            old_tem = temperature
            target = queue.pop(0)
            diff = target - temperature
            diff_int = int(diff * 10)
            if diff_int > 0:
                signal = True
            else:
                signal = False
                diff_int = -diff_int
            for i in range(diff_int):
                if signal:
                    old_tem = old_tem + 0.1
                else:
                    old_tem = old_tem - 0.1
                mqtt_client.publish('/fdse/lab/sensor/tem', old_tem)
                sleep(1)


@app.route('/light', methods=['POST'])
def publish_light():
    request_data = request.get_json()

    print(request_data['msg'])
    publish_result = update_sun_value(json.dumps(request_data['msg']))
    return jsonify({'code': publish_result[0]})


@app.route('/light', methods=['GET'])
def get_light():
    print("light state is ", state(light_state))
    return jsonify({'state': state(light_state)})


# @app.route('/air_condition', methods=['POST'])
# def publish_air_condition():
#     request_data = request.get_json()
#
#     print(request_data['msg'])
#     publish_result = update_temperature_value(json.dumps(request_data['msg']))
#     return jsonify({'code': publish_result[0]})
#
#
# @app.route('/air_condition', methods=['GET'])
# def get_air_condition():
#     print("air_condition state is ", state(air_condition_state))
#     return jsonify({'air_condition': state(air_condition_state)})
#
#
# @app.route('/air_cooler', methods=['POST'])
# def publish_air_cooler():
#     request_data = request.get_json()
#
#     print(request_data['msg'])
#     publish_result = update_temperature_value(json.dumps(request_data['msg']))
#     return jsonify({'code': publish_result[0]})
#
#
# @app.route('/air_cooler', methods=['GET'])
# def get_air_cooler():
#     print("air_cooler state is ", state(air_cooler_state))
#     return jsonify({'air_cooler': state(air_cooler_state)})
#
#
# @app.route('/heater', methods=['POST'])
# def publish_heater():
#     request_data = request.get_json()
#
#     print(json.dumps(request_data['msg']))
#     publish_result = update_temperature_value(request_data['msg'])
#     return jsonify({'code': publish_result[0]})
#
#
# @app.route('/heater', methods=['GET'])
# def get_heater():
#     print("heater state is ", state(heater_state))
#     return jsonify({'heater': state(heater_state)})


@app.route('/curtain', methods=['POST'])
def publish_curtain():
    request_data = request.get_json()

    print(request_data['msg'])
    publish_result = update_sun_value(request_data['msg'])
    return jsonify({'code': publish_result[0]})


@app.route('/curtain', methods=['GET'])
def get_curtain():
    print("curtain state is ", state(curtain_state))
    return jsonify({'curtain': state(curtain_state)})


@app.route('/getSun', methods=['GET'])
def get_sun():
    return json.dumps(sun)


@app.route('/getTemperature', methods=['GET'])
def get_temperature():
    return json.dumps(temperature)


if __name__ == '__main__':
    thread = Thread(target=update_temperature_value, args=[])
    thread.start()
    app.run(host='127.0.0.1', port=5000)
