import logging
import os
from unittest.mock import patch

import boto3
from freezegun import freeze_time

from src import process_events
from src.db_config import DbConfig

logging.info("test")

_ssm = boto3.client("ssm", region_name="eu-north-1")

EVENTS_DB_TEST_CONFIG = DbConfig(
    db_name=_ssm.get_parameter(Name="test_name_badnet_db")["Parameter"]["Value"],
    user=_ssm.get_parameter(Name="test_username_badnet_db")["Parameter"]["Value"],
    password=_ssm.get_parameter(Name="test_password_badnet_db", WithDecryption=True)["Parameter"]["Value"],
    port=_ssm.get_parameter(Name="test_port_badnet_db")["Parameter"]["Value"],
    host_name=_ssm.get_parameter(Name="test_host_badnet_db")["Parameter"]["Value"],
)


def absolute_file_name(file_name: str) -> str:
    return os.path.join(os.path.dirname(__file__), file_name)


def call_event_id_endpoint_side_effect(event_id: int) -> str:
    if event_id == 21603:
        file_name = "event_id_21603_response.txt"
    elif event_id == 22877:
        file_name = "event_id_22877_response.txt"
    else:
        raise ValueError(f"Test not setup with {event_id=}")

    with open(absolute_file_name(file_name), "r") as f:
        return f.read()


@freeze_time("2022-01-14")
@patch.object(process_events, "call_list_events_endpoint")
@patch.object(process_events, "call_event_id_endpoint")
@patch.object(process_events, "send_signal_messages")
def test_new_events_messages(send_signal_messages, call_event_id_endpoint, call_list_events_endpoint):
    print("Starting test_new_events_messages")
    call_event_id_endpoint.side_effect = call_event_id_endpoint_side_effect
    with open(absolute_file_name("list_events_response.txt"), "r") as f:
        call_list_events_endpoint.return_value = f.read()

    print("Before connect_events_db")
    db_conn = process_events.connect_events_db(EVENTS_DB_TEST_CONFIG)
    print("Before process_events")
    process_events.process_events(db_conn)

    expected_message_21603 = """Nouvau tournoi -> Les Championnats de France 2024
    Categories : Seniors
    Localisation : Fos sur Mer
    Date : Du 2 au 4 février
    Classements : Seniors
    Séries : N
    Ouverture des inscriptions : 2023-11-14"""

    expected_message_22877 = """Nouvau tournoi -> CREGYBADSHOW 2024
    Categories : Seniors
    Localisation : Crégy-Lès-Meaux
    Date : Les 8 et 9 juin
    Classements : Seniors
    Séries : R, D, P, NC
    Ouverture des inscriptions : 2024-02-01"""

    print("Before send_signal_message.assert_has_calls")
    send_signal_messages.assert_called_with([expected_message_21603, expected_message_22877])

    db_cursor = db_conn.cursor()
    print("Before main.get_new_events_notified")
    new_events_notified = process_events.get_new_events_notified(db_cursor)
    assert new_events_notified == [(21603, False), (22877, False)]
    db_cursor.close()

    # Do not commit so test database remains empty


@freeze_time("2023-11-16")  # After Fos sub opening, before Cergy sub opening
@patch.object(process_events, "call_list_events_endpoint")
@patch.object(process_events, "call_event_id_endpoint")
@patch.object(process_events, "send_signal_messages")
def test_only_fos_sub_opening_message(send_signal_messages, call_event_id_endpoint, call_list_events_endpoint):

    call_event_id_endpoint.side_effect = call_event_id_endpoint_side_effect
    with open(absolute_file_name("list_events_response.txt"), "r") as f:
        call_list_events_endpoint.return_value = f.read()

    db_conn = process_events.connect_events_db(EVENTS_DB_TEST_CONFIG)
    db_cursor = db_conn.cursor()
    db_cursor.execute("INSERT INTO new_events_notified VALUES %s, %s;", [(21603, False), (22877, False)])

    process_events.process_events(db_conn)

    expected_message_21603 = """Les inscriptions du tournoi Les Championnats de France 2024 sont désormais ouvertes !
    Categories : Seniors
    Localisation : Fos sur Mer
    Date : Du 2 au 4 février
    Classements : Seniors
    Séries : N"""

    send_signal_messages.assert_called_with([expected_message_21603])

    new_events_notified = process_events.get_new_events_notified(db_cursor)
    assert new_events_notified == [(22877, False), (21603, True)]
    db_cursor.close()

    # Do not commit so test database remains empty


@freeze_time("2023-11-16")  # After Fos sub opening, before Cergy sub opening
@patch.object(process_events, "call_list_events_endpoint")
@patch.object(process_events, "call_event_id_endpoint")
@patch.object(process_events, "send_signal_messages")
def test_no_sub_opening_message(send_signal_messages, call_event_id_endpoint, call_list_events_endpoint):

    call_event_id_endpoint.side_effect = call_event_id_endpoint_side_effect
    with open(absolute_file_name("list_events_response.txt"), "r") as f:
        call_list_events_endpoint.return_value = f.read()

    db_conn = process_events.connect_events_db(EVENTS_DB_TEST_CONFIG)
    db_cursor = db_conn.cursor()
    db_cursor.execute("INSERT INTO new_events_notified VALUES %s, %s;", [(21603, True), (22877, False)])

    process_events.process_events(db_conn)

    send_signal_messages.assert_called_with(["No new tournament neither tournament subscription opening today!"])

    new_events_notified = process_events.get_new_events_notified(db_cursor)
    assert new_events_notified == [(21603, True), (22877, False)]
    db_cursor.close()

    # Do not commit so test database remains empty
