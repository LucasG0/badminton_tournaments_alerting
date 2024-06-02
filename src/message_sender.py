import logging
import os
import time
from typing import List

import boto3
import docker
import requests  # type: ignore
from docker.models.containers import Container


def _run_signal_api_container() -> Container:
    client = docker.from_env()
    image = client.images.pull("bbernhard/signal-cli-rest-api")  # Make sure to always have last version
    logging.info("Starting docker container")
    signal_api_container = client.containers.run(
        image=image,
        detach=True,
        name="signal-api",
        restart_policy={"Name": "always"},
        ports={"8080/tcp": "8080"},
        volumes={
            os.path.expanduser("~/.local/share/signal-cli"): {"bind": "/home/.local/share/signal-cli", "mode": "rw"}
        },  # TODO Fix volumes for production
        environment=["MODE=native"],
    )
    time.sleep(5)  # Wait for the REST API to start. TODO properly wait for the API having started.
    return signal_api_container


def _send_signal_message(message: str):

    ssm = boto3.client("ssm", region_name="eu-north-1")
    phone_number = ssm.get_parameter(Name="phone_number", WithDecryption=True)["Parameter"]["Value"]

    headers = {
        "Content-Type": "application/json",
    }

    json_data = {
        "message": message,
        "number": phone_number,
        "recipients": [
            phone_number,
        ],
    }

    logging.info(f"Before sending message: {message}")
    response = requests.post("http://localhost:8080/v2/send", headers=headers, json=json_data, timeout=5)

    if response.status_code != 201:
        raise ValueError(
            f"Request failed: POST to http://localhost:8080/v2/send with {headers=} and {json_data=}, got response: {response.content=})"
        )

    logging.info("Message sent successfully")


def send_signal_messages(messages: List[str]) -> None:
    if len(messages) == 0:
        return

    signal_api_container = _run_signal_api_container()

    try:
        for message in messages:
            _send_signal_message(message)
    finally:
        signal_api_container.stop()
        signal_api_container.remove()
