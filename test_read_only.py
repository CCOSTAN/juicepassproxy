import unittest
from unittest.mock import patch

from ha_mqtt_discoverable import Settings
from juicebox_mqtthandler import JuiceboxMQTTHandler, MQTT_SENDING_ENTITIES


class FakeConfig:
    def get_device(self, _juicebox_id, _key, default=None):
        return default


class TestReadOnlyMode(unittest.IsolatedAsyncioTestCase):
    def build_handler(self, read_only):
        return JuiceboxMQTTHandler(
            device_name="JuiceBox Test",
            mqtt_settings=None,
            experimental=True,
            config=FakeConfig(),
            juicebox_id="test-juicebox",
            read_only=read_only,
        )

    async def test_read_only_starts_sensor_entities_only(self):
        handler = self.build_handler(read_only=True)
        started = []

        for name, entity in handler._entities.items():
            async def record_start(entity_name=name):
                started.append(entity_name)
            entity.start = record_start

        await handler.start()

        self.assertTrue(started)
        self.assertTrue(all(
            handler.get_entity(name).entity_type not in MQTT_SENDING_ENTITIES
            for name in started
        ))
        self.assertNotIn("current_max_online_set", started)
        self.assertNotIn("current_max_offline_set", started)
        self.assertNotIn("act_as_server", started)
        self.assertNotIn("send_to_juicebox", started)

    async def test_read_only_sending_entity_never_calls_mitm(self):
        handler = self.build_handler(read_only=True)
        entity = handler.get_entity("current_max_online_set")

        await entity.set_state(32)

        self.assertEqual(32, entity.state)
        self.assertIsNone(entity._mqtt)
        self.assertIsNone(entity._mitm_handler)

    async def test_read_only_sensor_publishes_discovery_without_state(self):
        handler = JuiceboxMQTTHandler(
            device_name="JuiceBox Test",
            mqtt_settings=Settings.MQTT(host="localhost"),
            experimental=False,
            config=FakeConfig(),
            juicebox_id="test-juicebox",
            read_only=True,
        )
        entity = handler.get_entity("power")

        with patch("juicebox_mqtthandler.ha_mqtt.Sensor") as sensor_class:
            await entity.start()

        sensor_class.return_value.write_config.assert_called_once_with()
        sensor_class.return_value.set_state.assert_not_called()

    async def test_normal_mode_keeps_upstream_command_entities(self):
        handler = self.build_handler(read_only=False)
        started = []

        for name, entity in handler._entities.items():
            async def record_start(entity_name=name):
                started.append(entity_name)
            entity.start = record_start

        await handler.start()

        self.assertIn("current_max_online_set", started)
        self.assertIn("current_max_offline_set", started)
        self.assertIn("act_as_server", started)
        self.assertIn("send_to_juicebox", started)


if __name__ == "__main__":
    unittest.main()
