#!/usr/bin/env python3
from kafka import KafkaProducer
import json
import time

BOOTSTRAP_SERVERS = ["10.83.153.137:9092"]
TOPIC = "cmerror"

def main():
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )

    try:
        for i in range(1, 6):
            msg = {"message": f"CMERROR DETECTED ON PFE {i}"}
            producer.send(TOPIC, value=msg)
            print(f"Sent: {msg}")
            time.sleep(1)
    finally:
        producer.flush()
        producer.close()

if __name__ == "__main__":
    main()
