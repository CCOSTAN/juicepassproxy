import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from juicebox_message import juicebox_message_from_string
from juicebox_mitm import JuiceboxMITM
from juicepassproxy import mode_validation_error


V07_STATUS = (
    "0910000000000000000000000000:v07,s0001,u30048,V2400,L0024880114,"
    "S2,T62,M40,m40,t09,i78,e-001,f6001,X0,Y0,E006804,A0394,p0992!KKD:"
)


class TestPassiveMonitor(unittest.IsolatedAsyncioTestCase):
    def build_mitm(self):
        return JuiceboxMITM(
            jpp_addr=("127.0.0.1", 8042),
            enelx_addr=("127.0.0.2", 8047),
            passive_monitor=True,
        )

    async def test_charger_telemetry_is_processed_without_any_udp_send(self):
        mitm = self.build_mitm()
        status = juicebox_message_from_string(V07_STATUS)
        mitm._message_decode = AsyncMock(return_value=status)
        mitm._local_mitm_handler = AsyncMock(return_value=V07_STATUS.encode())
        mitm.send_data = AsyncMock()
        mitm.send_cmd_message_to_juicebox = AsyncMock()
        charger_addr = ("127.0.0.3", 8047)

        await mitm._main_mitm_handler(V07_STATUS.encode(), charger_addr)

        mitm._local_mitm_handler.assert_awaited_once()
        mitm.send_data.assert_not_awaited()
        mitm.send_cmd_message_to_juicebox.assert_not_awaited()

    async def test_cloud_packet_is_dropped_without_processing_or_forwarding(self):
        mitm = self.build_mitm()
        mitm._juicebox_addr = ("127.0.0.3", 8047)
        mitm._remote_mitm_handler = AsyncMock()
        mitm.send_data = AsyncMock()

        await mitm._main_mitm_handler(b"cloud-data", mitm._enelx_addr)

        mitm._remote_mitm_handler.assert_not_awaited()
        mitm.send_data.assert_not_awaited()

    async def test_passive_mode_requires_sensor_only_and_no_local_server(self):
        safe = SimpleNamespace(
            read_only=True,
            update_udpc=False,
            ignore_enelx=True,
            passive_monitor=True,
        )
        writable = SimpleNamespace(
            read_only=False,
            update_udpc=False,
            ignore_enelx=True,
            passive_monitor=True,
        )
        cloud_forwarding = SimpleNamespace(
            read_only=True,
            update_udpc=False,
            ignore_enelx=False,
            passive_monitor=True,
        )
        unsafe_local_server = SimpleNamespace(
            read_only=True,
            update_udpc=False,
            ignore_enelx=True,
            passive_monitor=False,
        )

        self.assertIsNone(mode_validation_error(safe))
        self.assertIn("--read_only", mode_validation_error(writable))
        self.assertIn("--ignore_enelx", mode_validation_error(cloud_forwarding))
        self.assertIn("--ignore_enelx", mode_validation_error(unsafe_local_server))


if __name__ == "__main__":
    unittest.main()
