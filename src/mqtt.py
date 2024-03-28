import paho.mqtt.client as mqtt
from .database import SessionLocal
from src import models
import json
from threading import Thread
from .route.telemetry import add_ts_postgres, add_ts_cassandra
from .config import settings

class MQTTSubscriber:
    def __init__(self):
        self.client = mqtt.Client()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"Connected to the MQTT broker {settings.mqtt_hostname}:{settings.mqtt_port}")
            self.subscribe_all()
   
       
    def on_message(self, client, userdata, msg):
        device_id = msg.topic.split('/')[1]
        print(f"Received message from device {device_id}, message: {msg.payload.decode()}")
        try:
            data = json.loads(msg.payload.decode())
        except json.JSONDecodeError:
            print("Failed to parse JSON data")
            return

        if isinstance(data, dict) and bool(data):
            print("Received valid JSON object. Inserting into the databases.")
            try:
                # Republish for fe
                db = SessionLocal()
                device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
                self.client.publish(f"assets/{device.asset_id}/telemetry", json.dumps(data))
                # Add ts to databases
                for key, value in data.items():
                    if type(value) != int and type(value) != float:
                        print(f"Invalid value type received for key '{key}':  {type(value)}")
                        continue
                    Thread(target=add_ts_cassandra, args=(device_id, key, value)).start()
                    #Thread(target=add_ts_postgres, args=(device_id, key, value, db)).start()
                    add_ts_postgres(device_id, key, value, db)
                    
            except Exception as e:
                print(str(e))
            finally:
                db.close()
            
    def subscribe_all(self):
        try:
            db = SessionLocal()
            device_ids = [str(device.device_id) for device in db.query(models.Device).all()]
            for device_id in device_ids:
                self.client.subscribe(f"devices/{device_id}/telemetry")
            print(f"Subscribed to {device_ids}")
        except Exception as e:
            print(f"Failed to query device IDs and subscribe to topics: {str(e)}")
        finally:
            db.close()
            
    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print("Unexpected disconnection. Attempting to reconnect...")
            self.client.reconnect()
        

mqtt_subscriber = MQTTSubscriber()
mqtt_subscriber.client.on_connect = mqtt_subscriber.on_connect
mqtt_subscriber.client.on_message = mqtt_subscriber.on_message
mqtt_subscriber.client.connect(settings.mqtt_hostname, int(settings.mqtt_port), 10)
mqtt_subscriber.client.on_disconnect = mqtt_subscriber.on_disconnect

mqtt_subscriber.client.loop_start()