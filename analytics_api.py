import json
import subprocess
import sys
import time

import requests
import websocket

SUBSCRIBED_TOPICS = [
    "SIFIS:Privacy_Aware_Speech_Recognition",
    "SIFIS:Privacy_Aware_Parental_Control",
    "SIFIS:Privacy_Aware_Device_Anomaly_Detection",
    "SIFIS:Privacy_Aware_Object_Recognition",
    "SIFIS:Privacy_Aware_Face_Recognition",
    "SIFIS:Publish_Alarms_Request",
    "SIFIS:AUD_Manager_Request",
    "SIFIS:Privacy_Aware_Speech_Recognition_Results",
    "SIFIS:Privacy_Aware_Parental_Control_Results",
    "SIFIS:Privacy_Aware_Object_Recognition_Results",
    "SIFIS:Privacy_Aware_Object_Recognition_Frame_Results",
    "SIFIS:Privacy_Aware_Device_Anomaly_Detection_Results",
    "SIFIS:Netspot_Control_Results",
    "SIFIS:AUD_Manager_Results",
    "SIFIS:Object_Recognition",
    "SIFIS:Object_Recognition_Frame_Results",
    "SIFIS:Object_Recognition_Results",
    "SIFIS:Privacy_Aware_Speaker_Verification",
    "SIFIS:Privacy_Aware_Audio_Anomaly_Detection",
    "SIFIS:Privacy_Aware_Audio_Anomaly_Detection_Results",
]


def get_last_time():
    """Reads last_time.txt and returns timestamp from there or 0 for known errors"""
    try:
        file = open("last_time.txt")
        timestamp = int(file.readline().rstrip())
        file.close()
        return timestamp
    except (FileNotFoundError, ValueError):
        return 0


def set_last_time():
    """Writes the current timestamp to the last_time.txt file"""
    file = open("last_time.txt", "w")
    file.write(str(time.time_ns()))
    file.close()


def netspot_alarm_check(address, port, within_time=None):
    # Get or make timestamp for alarms request
    if within_time is None:
        timestamp = get_last_time()
    else:
        timestamp = time.time_ns() - int(within_time * 6e10)

    # Making the request
    url = f"http://{address}:{port}/v1/netspots/alarms"
    params = {"time": timestamp, "last": 50}
    try:
        reply = requests.get(url, params)
    except requests.RequestException as e:
        return False, str(e)

    # Checking the reply
    if reply.status_code == 200:
        # Request was okay, save current time to be used with next request
        set_last_time()

        # Handling messages
        messages = reply.json()
        if len(messages) == 0:
            # No alarms
            return True, None
        # Find messages with the highest probability
        highest_probability = 0.0
        most_urgent_message = ""
        for message in messages:
            if message["probability"] >= highest_probability:
                highest_probability = message["probability"]
                most_urgent_message = message
        return True, most_urgent_message

    # Server responded with error. Return status code and content in the message
    return (
        False,
        f"Server responded with {reply.status_code}:\n{reply.content.decode('utf-8')}",
    )


def on_error(ws, error):
    print(error)


def on_close(ws, close_status_code, close_msg):
    print("### Connection closed ###")


def on_open(ws):
    print("### Connection established ###")


def on_message(ws, message):
    print("Received:")
    print(message)
    json_message = json.loads(message)

    if "Persistent" in json_message:
        json_message = json_message["Persistent"]

        if "topic_name" in json_message:
            if json_message["topic_name"] in SUBSCRIBED_TOPICS:
                if (
                    json_message["topic_name"]
                    == "SIFIS:Publish_Alarms_Request"
                ):
                    print("Received instance of " + json_message["topic_name"])
                    print("Topic Name: " + json_message["topic_name"])
                    print("Address: " + json_message["value"]["Address"])
                    print("Port: " + str(json_message["value"]["Port"]))

                    Address = json_message["value"]["Address"]
                    Port = json_message["value"]["Port"]
                    within_time = json_message["value"]["Within Time"]
                    device = json_message["value"]["Device name"]

                    if (
                        Address is not None
                        and Port is not None
                        and within_time is not None
                    ):
                        print("Time is not None")
                        (success, message) = netspot_alarm_check(
                            Address, Port, within_time
                        )
                    elif (
                        Address is not None
                        and Port is not None
                        and within_time is None
                    ):
                        print("Time is None")
                        (success, message) = netspot_alarm_check(Address, Port)
                    else:
                        print("Error, no variables were passed")

                    if success:
                        if message is None:
                            return 0
                        # We have an alarm message. Let us create DHT message from it.
                        ws_req = {
                            "RequestPostTopicUUID": {
                                "topic_name": "SIFIS:Netspot_Control_Results",
                                "topic_uuid": "AlarmResult",
                                "value": {
                                    "description": "Netspot alarms check results",
                                    "Device": device,
                                    "Statistic": message["stat"],
                                    "Status": message["status"],
                                    "Probability": message["probability"],
                                    "Time": message["time"],
                                },
                            }
                        }
                        ws.send(json.dumps(ws_req))

                        dht_message_json = json.dumps(
                            ws_req, separators=(",", ":")
                        )
                        print(dht_message_json)
                        return 1
                    print(
                        "Could not receive alarms:", message, file=sys.stdout
                    )
                    return 2

                elif json_message["topic_name"] == "SIFIS:AUD_Manager_Request":
                    print("Received instance of " + json_message["topic_name"])
                    print("Topic Name: " + json_message["topic_name"])
                    print("Request: " + json_message["value"]["Request"])

                    Request = json_message["value"]["Request"]
                    cmd1 = "curl http://localhost:5050/" + str(Request)
                    cmd = cmd1.split()
                    print(cmd)
                    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
                    out, err = p.communicate()
                    # print(out)
                    print(out.decode("ascii"))

                    ws_req = {
                        "RequestPostTopicUUID": {
                            "topic_name": "SIFIS:AUD_Manager_Results",
                            "topic_uuid": "AUD_Manager_Results",
                            "value": {
                                "description": "AUD Manager Results",
                                "Request": str(Request),
                                "Results": out.decode("ascii"),
                            },
                        }
                    }
                    ws.send(json.dumps(ws_req))

                elif (
                    json_message["topic_name"]
                    == "SIFIS:Privacy_Aware_Speech_Recognition"
                ):
                    print("Received instance of " + json_message["topic_name"])
                    print("Audio File: " + json_message["value"]["Audio File"])
                    print(
                        "requestor_id: "
                        + json_message["value"]["requestor_id"]
                    )
                    print(
                        "requestor_type: "
                        + json_message["value"]["requestor_type"]
                    )
                    print("request_id: " + json_message["value"]["request_id"])
                    print(
                        "Entity Types: "
                        + str(json_message["value"]["Entity Types"])
                    )
                    print("method: " + str(json_message["value"]["method"]))

                    audio = json_message["value"]["Audio File"]
                    requestor_id = json_message["value"]["requestor_id"]
                    requestor_type = json_message["value"]["requestor_type"]
                    request_id = json_message["value"]["request_id"]
                    Entity_Types = json_message["value"]["Entity Types"]
                    method = json_message["value"]["method"]

                    if method == "DeepSpeeach":
                        cmd1 = "docker run -ti -v /var/run/docker.sock:/var/run/docker.sock -u root --net=host --name privacy_preserving_speech_recognition privacy_preserving_speech_recognition python -m recognize_wavFile_Func --audio "
                        cmd2 = cmd1 + audio

                        cmd = cmd2.split()
                        print(cmd)
                        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
                        out, err = p.communicate()
                        print(out)

                        cmd = "docker rm -f privacy_preserving_speech_recognition".split()
                        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
                        out, err = p.communicate()
                        print(out)

                    elif method == "Whisper":
                        url = (
                            "http://localhost:5040/whisper/"
                            + audio
                            + "/"
                            + requestor_id
                            + "/"
                            + requestor_type
                            + "/"
                            + request_id
                        )
                        file = {
                            "file": open("/analytics_api/data/" + audio, "rb")
                        }
                        response = requests.post(url, files=file)

                        # Check the response
                        if response.status_code == 200:
                            print("Request succeeded.")
                            response_dict = json.loads(response.content)
                            response_dict2 = response_dict[
                                "RequestPostTopicUUID"
                            ]["value"]
                            ws.send(json.dumps(response_dict))
                        else:
                            print("Request failed.")
                            print(response.content)

                elif (
                    json_message["topic_name"]
                    == "SIFIS:Privacy_Aware_Audio_Anomaly_Detection"
                ):
                    print("Received instance of " + json_message["topic_name"])
                    print("Audio File: " + json_message["value"]["audio_file"])
                    print(
                        "requestor_id: "
                        + json_message["value"]["requestor_id"]
                    )
                    print(
                        "requestor_type: "
                        + json_message["value"]["requestor_type"]
                    )
                    print("request_id: " + json_message["value"]["request_id"])
                    print("method: " + str(json_message["value"]["method"]))

                    audio_file = json_message["value"]["audio_file"]
                    requestor_id = json_message["value"]["requestor_id"]
                    requestor_type = json_message["value"]["requestor_type"]
                    request_id = json_message["value"]["request_id"]
                    method = json_message["value"]["method"]

                    url = (
                        "http://localhost:5000/model/predict/"
                        + audio_file
                        + "/"
                        + method
                        + "/"
                        + requestor_id
                        + "/"
                        + requestor_type
                        + "/"
                        + request_id
                    )
                    file = {
                        "audio": (
                            "sample1.wav",
                            open("/analytics_api/data/" + audio_file, "rb"),
                            "audio/wav",
                        )
                    }
                    response = requests.post(url, files=file)

                    # Check the response
                    if response.status_code == 200:
                        print("Request succeeded.")

                        response_dict = json.loads(response.content)
                        for prediction in range(5):
                            print(
                                response_dict["predictions"][prediction][
                                    "label"
                                ],
                                response_dict["predictions"][prediction][
                                    "probability"
                                ],
                            )

                        ws_req = {
                            "RequestPostTopicUUID": {
                                "topic_name": "SIFIS:Privacy_Aware_Audio_Anomaly_Detection_Results",
                                "topic_uuid": "Audio_Anomaly_Detection_Results",
                                "value": {
                                    "description": "Speech Recognition Results",
                                    "requestor_id": str(
                                        response_dict["requestor_id"]
                                    ),
                                    "requestor_type": str(
                                        response_dict["requestor_type"]
                                    ),
                                    "request_id": str(
                                        response_dict["request_id"]
                                    ),
                                    "analyzer_id": str(
                                        response_dict["analyzer_id"]
                                    ),
                                    "analysis_id": str(
                                        response_dict["analysis_id"]
                                    ),
                                    "audio_file": str(
                                        response_dict["audio_file"]
                                    ),
                                    "method": str(response_dict["method"]),
                                    "predictions": response_dict[
                                        "predictions"
                                    ],
                                },
                            }
                        }
                        ws.send(json.dumps(ws_req))

                    else:
                        print("Request failed.")
                        print(response.content)

                elif (
                    json_message["topic_name"]
                    == "SIFIS:Privacy_Aware_Device_Anomaly_Detection"
                ):
                    print("Received instance of " + json_message["topic_name"])
                    print("Topic Name: " + json_message["topic_name"])
                    temp = json_message["value"]["Temperatures"]
                    t = " ".join(str(item) for item in temp)
                    requestor_id = json_message["value"]["requestor_id"]
                    requestor_type = json_message["value"]["requestor_type"]
                    request_id = json_message["value"]["request_id"]

                    url = (
                        "http://localhost:9090/temperature/"
                        + str(t)
                        + "/"
                        + requestor_id
                        + "/"
                        + requestor_type
                        + "/"
                        + request_id
                    )

                    # Make the request
                    response = requests.get(url)

                    # Check the response
                    if response.status_code == 200:
                        print("Request succeeded.")
                        response_dict = json.loads(response.content)
                        response_dict2 = response_dict["RequestPostTopicUUID"][
                            "value"
                        ]
                        ws.send(json.dumps(response_dict))
                    else:
                        print("Request failed.")
                        print(response.content)

                elif (
                    json_message["topic_name"]
                    == "SIFIS:Privacy_Aware_Parental_Control"
                ):
                    print("Received instance of " + json_message["topic_name"])
                    print("file_name: " + json_message["value"]["file_name"])
                    print(
                        "requestor_id: "
                        + json_message["value"]["requestor_id"]
                    )
                    print(
                        "requestor_type: "
                        + json_message["value"]["requestor_type"]
                    )
                    print("request_id: " + json_message["value"]["request_id"])
                    print(
                        "Privacy_Parameter: "
                        + str(json_message["value"]["Privacy_Parameter"])
                    )

                    file_name = json_message["value"]["file_name"]
                    Privacy_Parameter = json_message["value"][
                        "Privacy_Parameter"
                    ]
                    requestor_id = json_message["value"]["requestor_id"]
                    requestor_type = json_message["value"]["requestor_type"]
                    request_id = json_message["value"]["request_id"]

                    file_path = "/analytics_api/data/" + file_name

                    url = (
                        "http://localhost:6060/file_estimation/"
                        + file_name
                        + "/"
                        + str(Privacy_Parameter)
                        + "/"
                        + requestor_id
                        + "/"
                        + requestor_type
                        + "/"
                        + request_id
                    )
                    file = {"file": open(file_path, "rb")}
                    response = requests.post(url, files=file)

                    # Use the json module to load CKAN's response into a dictionary.
                    response_dict = json.loads(response.text)
                    print(response_dict)

                    # Make the request
                    response = requests.post(
                        url, files={"file": open(file_path, "rb")}
                    )

                    # Check the response
                    if response.status_code == 200:
                        print("Request succeeded.")
                        response_dict = json.loads(response.content)
                        response_dict2 = response_dict["RequestPostTopicUUID"][
                            "value"
                        ]
                        ws.send(json.dumps(response_dict))
                    else:
                        print("Request failed.")
                        print(response.content)

                elif (
                    json_message["topic_name"]
                    == "SIFIS:Privacy_Aware_Object_Recognition"
                ):
                    print("Received instance of " + json_message["topic_name"])
                    print("file_path: " + json_message["value"]["file_path"])
                    print("file_name: " + json_message["value"]["file_name"])
                    print(
                        "requestor_id: "
                        + json_message["value"]["requestor_id"]
                    )
                    print(
                        "requestor_type: "
                        + json_message["value"]["requestor_type"]
                    )
                    print("request_id: " + json_message["value"]["request_id"])
                    print("epsilon: " + str(json_message["value"]["epsilon"]))
                    print(
                        "sensitivity: "
                        + str(json_message["value"]["sensitivity"])
                    )

                    file_path = json_message["value"]["file_path"]
                    file_name = json_message["value"]["file_name"]
                    requestor_id = json_message["value"]["requestor_id"]
                    requestor_type = json_message["value"]["requestor_type"]
                    request_id = json_message["value"]["request_id"]
                    epsilon = json_message["value"]["epsilon"]
                    sensitivity = json_message["value"]["sensitivity"]

                    url = (
                        "http://localhost:8080/file_object/"
                        + file_name
                        + "/"
                        + str(epsilon)
                        + "/"
                        + str(sensitivity)
                        + "/"
                        + requestor_id
                        + "/"
                        + requestor_type
                        + "/"
                        + request_id
                    )
                    file_path = "/analytics_api/data/" + file_name

                    # Make the request
                    response = requests.post(
                        url, files={"file": open(file_path, "rb")}
                    )

                    # Check the response
                    if response.status_code == 200:
                        print("Request succeeded.")
                        response_dict = json.loads(response.content)
                        response_dict2 = response_dict["RequestPostTopicUUID"][
                            "value"
                        ]
                        ws.send(json.dumps(response_dict))
                    else:
                        print("Request failed.")
                        print(response.content)

                elif (
                    json_message["topic_name"]
                    == "SIFIS:Privacy_Aware_Face_Recognition"
                ):
                    print("Received instance of " + json_message["topic_name"])
                    print("file_name: " + json_message["value"]["file_name"])
                    print(
                        "database_path: "
                        + json_message["value"]["database_path"]
                    )
                    print(
                        "requestor_id: "
                        + json_message["value"]["requestor_id"]
                    )
                    print(
                        "requestor_type: "
                        + json_message["value"]["requestor_type"]
                    )
                    print("request_id: " + json_message["value"]["request_id"])
                    print(
                        "privacy_parameter: "
                        + str(json_message["value"]["privacy_parameter"])
                    )

                    file_name = json_message["value"]["file_name"]
                    database_path = json_message["value"]["database_path"]
                    requestor_id = json_message["value"]["requestor_id"]
                    requestor_type = json_message["value"]["requestor_type"]
                    request_id = json_message["value"]["request_id"]
                    privacy_parameter = json_message["value"][
                        "privacy_parameter"
                    ]

                    url = (
                        "http://localhost:8090/check_directory/"
                        + file_name
                        + "/"
                        + str(privacy_parameter)
                        + "/"
                        + requestor_id
                        + "/"
                        + requestor_type
                        + "/"
                        + request_id
                    )
                    file_path = "/analytics_api/data/" + file_name
                    # database_path = '/analytics_api/data/' + database_path
                    # database_path = '/app/database'
                    database_path = database_path

                    files = [
                        ("file", open(file_path, "rb")),
                        ("path", database_path),
                    ]

                    # Make the request
                    response = requests.post(url, files=files)

                    # Check the response
                    if response.status_code == 200:
                        print("Request succeeded.")
                        response_dict = json.loads(response.content)
                        response_dict2 = response_dict["RequestPostTopicUUID"][
                            "value"
                        ]

                        ws.send(json.dumps(response_dict))
                    else:
                        print("Request failed.")
                        print(response.content)

                elif (
                    json_message["topic_name"]
                    == "SIFIS:Privacy_Aware_Speaker_Verification"
                ):
                    print("Received instance of " + json_message["topic_name"])
                    print(
                        "First Audio File: "
                        + json_message["value"]["first_audio_file"]
                    )
                    print(
                        "Second Audio File: "
                        + json_message["value"]["second_audio_file"]
                    )
                    print(
                        "requestor_id: "
                        + json_message["value"]["requestor_id"]
                    )
                    print(
                        "requestor_type: "
                        + json_message["value"]["requestor_type"]
                    )
                    print("request_id: " + json_message["value"]["request_id"])

                    first_audio_file = json_message["value"][
                        "first_audio_file"
                    ]
                    second_audio_file = json_message["value"][
                        "second_audio_file"
                    ]
                    requestor_id = json_message["value"]["requestor_id"]
                    requestor_type = json_message["value"]["requestor_type"]
                    request_id = json_message["value"]["request_id"]

                    url = (
                        "http://localhost:7070/speaker_verification/"
                        + first_audio_file
                        + "/"
                        + second_audio_file
                        + "/"
                        + requestor_id
                        + "/"
                        + requestor_type
                        + "/"
                        + request_id
                    )
                    files = [
                        (
                            "file1",
                            (
                                "filename1.wav",
                                open(
                                    "/analytics_api/data/" + first_audio_file,
                                    "rb",
                                ),
                                "audio/wav",
                            ),
                        ),
                        (
                            "file2",
                            (
                                "filename2.wav",
                                open(
                                    "/analytics_api/data/" + second_audio_file,
                                    "rb",
                                ),
                                "audio/wav",
                            ),
                        ),
                    ]
                    response = requests.post(url, files=files)

                    # Check the response
                    if response.status_code == 200:
                        print("Request succeeded.")
                        response_dict = json.loads(response.content)
                        response_dict2 = response_dict["RequestPostTopicUUID"][
                            "value"
                        ]
                        ws.send(json.dumps(response_dict))
                    else:
                        print("Request failed.")
                        print(response.content)

            else:
                print(
                    "We are not subscribed to this topic ",
                    json_message["topic_name"],
                )


if __name__ == "__main__":
    ws = websocket.WebSocketApp(
        "ws://localhost:3000/ws",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )

    ws.run_forever()
