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
        cfg = self._config.get('message_sensor', {})
        self._bootstrap_servers = cfg.get('bootstrap_servers', '10.83.153.137:9092')
        self._topic = cfg.get('topics', [{}])[0].get('name', 'cmerror')
        self._group_id = cfg.get('topics', [{}])[0].get('group_id', 'st2_cmerror')
        self._trigger = cfg.get('topics', [{}])[0].get('trigger', 'demo.cmerror_trigger')

        LOG.info(f"Connecting to Kafka: {self._bootstrap_servers}, topic: {self._topic}")
        self._consumer = KafkaConsumer(
            self._topic,
            bootstrap_servers="10.83.153.137:9092",
            group_id=self._group_id,
            value_deserializer=lambda m: m.decode('utf-8')
        )

    def poll(self):
        for message in self._consumer:
            LOG.info(f"Received message on {self._topic}: {message.value}")
            try:
                payload = json.loads(message.value)
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
