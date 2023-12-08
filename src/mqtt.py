import paho.mqtt.client as mqtt
from .database import SessionLocal
from src import models
import json


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
                for key, value in data.items():
                    existing_key = db.query(models.TimeSeriesKey).filter(models.TimeSeriesKey.key == key).first()
                    if not existing_key:
                        new_key = models.TimeSeriesKey(key=key)
                        db.add(new_key)
                        db.commit()
                        db.refresh(new_key)
                        print(f"Inserted new key: {new_key.key}")
                    else:
                        new_key = existing_key
                    telemetry_data = models.TimeSeries(
                        key_id=new_key.ts_key_id,
                        device_id=device_id,
                        value=float(value),
                    )
                    db.add(telemetry_data)
                    db.commit()
                    print(f"Posted telemetry data from device with id: {device_id}")
            except Exception as e:
                print(f"Failed to insert data into the database: {str(e)}")
            finally:
                db.close()

    def subscribe_all(self):
        print("Subscribing all topics")
        try:
            db = SessionLocal()
            device_ids = [str(device.device_id) for device in db.query(models.Device).all()]
            for device_id in device_ids:
                self.client.subscribe(f"device/{device_id}/telemetry")
            print(f"Subscribed to {device_ids}")
        except Exception as e:
            print(f"Failed to query device IDs and subscribe to topics: {str(e)}")
        finally:
            db.close()

        
mqtt_subscriber = MQTTSubscriber()
mqtt_subscriber.client.on_connect = mqtt_subscriber.on_connect
mqtt_subscriber.client.on_message = mqtt_subscriber.on_message
mqtt_subscriber.client.connect("localhost", 1883, 60)
mqtt_subscriber.client.loop_start()