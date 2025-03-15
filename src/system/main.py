import time
import paho.mqtt.client as mqtt

def on_connect(client, userdata, flags, rc):
    print(f"Подключено с кодом результата: {rc}")

def on_publish(client, userdata, mid):
    print("Сообщение отправлено")

client = mqtt.Client(client_id="test", callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_publish = on_publish

error_code = client.connect("localhost")
print("Код ошибки подключения:", error_code)

client.loop_start()

def main():
    while True:
        result = client.publish("robot/command", "start")
        print(result)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print("Опубликовано")
        else:
            print(f"Ошибка при публикации: {result}")
        time.sleep(0.5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        client.loop_stop()
        client.disconnect()