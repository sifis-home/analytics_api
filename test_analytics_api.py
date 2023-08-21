import sys
import unittest
from argparse import Namespace
from unittest.mock import Mock, mock_open, patch, MagicMock

import requests
import json

import websocket
import check
from analytics_api import (
    get_last_time,
    netspot_alarm_check,
    on_close,
    on_error,
    on_open,
    set_last_time,
    on_message,
)

# ws = websocket.WebSocketApp(
#         "ws://localhost:3000/ws",
#         on_open=on_open,
#         on_message=on_message,
#         on_error=on_error,
#         on_close=on_close,
#     )

class TestOnMessageFunction(unittest.TestCase):
    def setUp(self):
        self.ws = MagicMock()

    @patch('analytics_api.json.loads')
    def test_speech_recognition_message(self, mock_json_loads):
        # Define a sample JSON message for Privacy_Aware_Speech_Recognition
        json_message = {
            "Persistent": {
                "topic_name": "SIFIS:Privacy_Aware_Speech_Recognition",
                "value": {
                    "Audio File": "example.wav",
                    "requestor_id": "user123",
                    "requestor_type": "user",
                    "request_id": "123",
                    "Entity Types": ["person"],
                    "method": "DeepSpeeach"
                }
            }
        }
        mock_json_loads.return_value = json_message

        on_message(self.ws, json.dumps(json_message))

    @patch('analytics_api.json.loads')
    def test_publish_alarms_request_message(self, mock_json_loads):
        json_message = {
            "Persistent": {
                "topic_name": "SIFIS:Publish_Alarms_Request",
                "value": {
                    "Address": "192.168.1.1",
                    "Port": 1234,
                    "Within Time": 10,
                    "Device name": "Device1"
                }
            }
        }
        mock_json_loads.return_value = json_message

        on_message(self.ws, json.dumps(json_message))

    @patch('analytics_api.json.loads')
    def test_aud_manager_request_message(self, mock_json_loads):
        json_message = {
            "Persistent": {
                "topic_name": "SIFIS:AUD_Manager_Request",
                "value": {
                    "Request": "some_request"
                }
            }
        }
        mock_json_loads.return_value = json_message

        on_message(self.ws, json.dumps(json_message))

class TestMainFunction(unittest.TestCase):
    @patch(
        "argparse.ArgumentParser.parse_args",
        return_value=Namespace(address="127.0.0.1", port=8080, minutes=None),
    )
    @patch("check.netspot_alarm_check", return_value=(True, None))
    @patch("json.dumps")
    def test_no_alarms(
        self, mock_dumps, mock_netspot_alarm_check, mock_parse_args
    ):
        mock_dumps.return_value = '{"Topic": "SIFIS: Netspot Alarm Results", "Device": "DefaultDevice", "Statistic": "stats", "Status": "status", "Probability": 0.9, "Time:": 1234567890}'
        sys.stdout = Mock()

        result = check.main()

        self.assertEqual(result, 0)
        mock_parse_args.assert_called_once()
        mock_netspot_alarm_check.assert_called_once_with(
            "127.0.0.1", 8080, None
        )
        mock_dumps.assert_not_called()
        sys.stdout.write.assert_not_called()

        sys.stdout = sys.__stdout__

    @patch(
        "argparse.ArgumentParser.parse_args",
        return_value=Namespace(address="127.0.0.1", port=8080, minutes=None),
    )
    @patch("check.netspot_alarm_check", return_value=(False, "Request failed"))
    def test_application_error(
        self, mock_netspot_alarm_check, mock_parse_args
    ):
        sys.stdout = Mock()

        result = check.main()

        self.assertEqual(result, 2)
        mock_parse_args.assert_called_once()
        mock_netspot_alarm_check.assert_called_once_with(
            "127.0.0.1", 8080, None
        )

        sys.stdout = sys.__stdout__


class TestCheckNetSpotAlarmCheck(unittest.TestCase):
    @patch("check.get_last_time", return_value=1234567890)
    @patch("check.set_last_time")
    @patch("requests.get")
    def test_check_successful_request_no_alarms(
        self, mock_get, mock_set_last_time, mock_get_last_time
    ):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        result, message = check.netspot_alarm_check("127.0.0.1", 8080)

        mock_get_last_time.assert_called_once()

    @patch(
        "requests.get", side_effect=requests.RequestException("Request failed")
    )
    def test_request_exception(self, mock_get):
        result, message = check.netspot_alarm_check("127.0.0.1", 8080)

    @patch("requests.get")
    def test_server_error(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.content = b"Internal Server Error"
        mock_get.return_value = mock_response

        result, message = check.netspot_alarm_check("127.0.0.1", 8080)


class TestNetSpotAlarmCheck(unittest.TestCase):
    @patch("analytics_api.get_last_time", return_value=1234567890)
    @patch("analytics_api.set_last_time")
    @patch("requests.get")
    def test_successful_request_no_alarms(
        self, mock_get, mock_set_last_time, mock_get_last_time
    ):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        result, message = netspot_alarm_check("127.0.0.1", 8080)

        mock_get_last_time.assert_called_once()

    @patch(
        "requests.get", side_effect=requests.RequestException("Request failed")
    )
    def test_request_exception(self, mock_get):
        result, message = netspot_alarm_check("127.0.0.1", 8080)

    @patch("requests.get")
    def test_server_error(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.content = b"Internal Server Error"
        mock_get.return_value = mock_response

        result, message = netspot_alarm_check("127.0.0.1", 8080)


class TestCheckGetLastTime(unittest.TestCase):
    @patch("builtins.open", new_callable=mock_open, read_data="12345\n")
    def test_check_successful_read(self, mock_file):
        timestamp = check.get_last_time()

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_check_file_not_found(self, mock_file):
        timestamp = check.get_last_time()

    @patch(
        "builtins.open", new_callable=mock_open, read_data="not_an_integer\n"
    )
    def test_value_error(self, mock_file):
        timestamp = check.get_last_time()


class TestGetLastTime(unittest.TestCase):
    @patch("builtins.open", new_callable=mock_open, read_data="12345\n")
    def test_successful_read(self, mock_file):
        timestamp = get_last_time()

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_file_not_found(self, mock_file):
        timestamp = get_last_time()

    @patch(
        "builtins.open", new_callable=mock_open, read_data="not_an_integer\n"
    )
    def test_value_error(self, mock_file):
        timestamp = get_last_time()


class TestCheckSetLastTime(unittest.TestCase):
    @patch("builtins.open", new_callable=mock_open)
    def test_check_successful_write(self, mock_file):
        check.set_last_time()

    @patch("builtins.open", side_effect=PermissionError)
    def test_check_permission_error(self, mock_file):
        with self.assertRaises(PermissionError):
            check.set_last_time()


class TestSetLastTime(unittest.TestCase):
    @patch("builtins.open", new_callable=mock_open)
    def test_successful_write(self, mock_file):
        set_last_time()

    @patch("builtins.open", side_effect=PermissionError)
    def test_permission_error(self, mock_file):
        with self.assertRaises(PermissionError):
            set_last_time()


def test_on_error():
    error = "WebSocket error occurred"

    with patch("builtins.print") as mock_print:
        on_error(None, error)

    mock_print.assert_called_once_with(error)


def test_on_close():
    close_status_code = 1000
    close_msg = "Connection closed"

    with patch("builtins.print") as mock_print:
        on_close(None, close_status_code, close_msg)

    mock_print.assert_called_once_with("### Connection closed ###")


def test_on_open():
    with patch("builtins.print") as mock_print:
        on_open(None)

    mock_print.assert_called_once_with("### Connection established ###")
