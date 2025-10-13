from st2reactor.sensor.base import PollingSensor
from kafka import KafkaConsumer
import json
import logging

LOG = logging.getLogger(__name__)

class CmErrorKafkaSensor(PollingSensor):
    def __init__(self, sensor_service, config=None, poll_interval=5):
        super(CmErrorKafkaSensor, self).__init__(sensor_service, config, poll_interval)
        self._consumer = None
        self._topic = None
        self._bootstrap_servers = None
        self._group_id = None
        self._trigger = None

    def setup(self):
        cfg = self._config.get('demo', {})
        
        if not cfg:
            print ("No configuration found for demo pack in config attribute.")
        else:
            print ("Received config:", json.dumps(cfg, indent=4))
            demo_cfg = cfg.get('message_sensor', {})

            self._bootstrap_servers = demo_cfg.get('bootstrap_servers', 'localhost:9092')
            self._topic = demo_cfg.get('topics', [{}])[0].get('name', 'default_topic')
            self._group_id = demo_cfg.get('topics', [{}])[0].get('group_id', 'default_group')
            self._trigger = demo_cfg.get('topics', [{}])[0].get('trigger', 'default_trigger')
            
            print(f"Kafka Sensor Config - Bootstrap Servers: {self._bootstrap_servers}, Topic: {self._topic}, Group ID: {self._group_id}, Trigger: {self._trigger}")

            LOG.info(f"Connecting to Kafka: {self._bootstrap_servers}, topic: {self._topic}")
            self._consumer = KafkaConsumer(
                self._topic,
                bootstrap_servers=self._bootstrap_servers,
                group_id=self._group_id,
                value_deserializer=lambda m: m.decode('utf-8')
            )

    def poll(self):
        for message in self._consumer:
            LOG.info(f"Received message on {self._topic}: {message.value}")
            try:
                payload = {'message': json.loads(message.value)}
            except Exception:
                payload = {'message': message.value}

            self.sensor_service.dispatch(trigger=self._trigger, payload=payload)
            break  # process one message per poll cycle

    def cleanup(self):
        if self._consumer:
            self._consumer.close()

    def add_trigger(self, trigger):
        # called when a trigger is added dynamically
        pass

    def update_trigger(self, trigger):
        # called when a trigger is updated
        pass

    def remove_trigger(self, trigger):
        # called when a trigger is removed
        pass
