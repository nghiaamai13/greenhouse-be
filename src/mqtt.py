import paho.mqtt.client as mqtt
from .database import SessionLocal
from src import models
import json, time
from threading import Thread
from .route.telemetry import add_ts_postgres, add_ts_cassandra

class MQTTSubscriber:
    def __init__(self):
        self.client = mqtt.Client()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connected to the MQTT broker")
            
            self.subscribe_all()
   
       
    def on_message(self, client, userdata, msg):
        print(f"Received message on topic {msg.topic}: {msg.payload.decode()}")
        device_id = msg.topic.split('/')[1]
        print(f"Device ID: {device_id}")
        try:
            data = json.loads(msg.payload.decode())
        except json.JSONDecodeError:
            print("Failed to parse JSON data")
            return

        if isinstance(data, dict) and bool(data):
            print("Received a non-empty JSON object. Inserting into the database.")
            try:
                db = SessionLocal()
                device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
                current_asset = db.query(models.Asset).filter(models.Asset.asset_id == device.asset_id).first()
                self.client.publish(f"assets/{current_asset.asset_id}/telemetry", json.dumps(data))
                for key, value in data.items():
                    add_ts_postgres(device, key, value, db)
                    add_ts_cassandra(device, key, value)
                    
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

def mqtt_thread():
        
    mqtt_subscriber = MQTTSubscriber()
    mqtt_subscriber.client.on_connect = mqtt_subscriber.on_connect
    mqtt_subscriber.client.on_message = mqtt_subscriber.on_message
    mqtt_subscriber.client.connect("localhost", 1883, 60)
    while True:
        mqtt_subscriber.client.loop_start()
        time.sleep(59)
        
mqtt_thread = Thread(target=mqtt_thread)
mqtt_thread.start()