#!/usr/bin/env python3
from kafka import KafkaConsumer
import json

BOOTSTRAP_SERVERS = ["10.83.153.137:9092"]
TOPIC = "cmerror"

def main():
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="cmerror-group",
        value_deserializer=lambda m: json.loads(m.decode("utf-8"))
    )

    print("Listening for messages on topic:", TOPIC)
    for msg in consumer:
        print(f"Received: {msg.value}")

if __name__ == "__main__":
    main()
