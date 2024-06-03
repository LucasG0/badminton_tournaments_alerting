import logging
import traceback
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional, Tuple

import psycopg2
from psycopg2._psycopg import connection, cursor

from .call_badnet_apis import call_event_id_endpoint, call_list_events_endpoint
from .db_config import DbConfig
from .message_sender import send_signal_messages

try:
    from BeautifulSoup import BeautifulSoup
except ImportError:
    from bs4 import BeautifulSoup, Tag


@dataclass
class EventInfo:
    id_: int
    name: str
    location: str
    categories: str
    series: str
    formats: str
    date_: date
    date_sub_opening: date


def remove_spans_inplace(div):
    for span in div.findAll("span"):
        span.replace_with("")
    return div


def parse_date_sub_opening(parsed_html: BeautifulSoup) -> date:
    div_limit_content = parsed_html.find("div", class_="limit").text.strip()
    start_str = "Ouverture des inscriptions"
    end_str = "\nFermeture des inscriptions"
    date_sub_opening_start_index = div_limit_content.index(start_str) + len(start_str)
    date_sub_opening_end_index = div_limit_content.index(end_str)
    date_sub_opening_str = div_limit_content[date_sub_opening_start_index:date_sub_opening_end_index]
    date_sub_opening = datetime.strptime(date_sub_opening_str, "%d/%m/%Y").date()
    return date_sub_opening


# TODO To avoid calling all these API events everyday, we could store the sub opening date,
#  but this might lead to bugs if sub opening date changed meanwhile.
#  To make sure sub opening date did not change, we could compare stored sub opening date with "Ouverture dans X days"
#  that we got in the list_events endpoint (that we call only once).
def parse_date_sub_opening_and_formats(event_id: int) -> Tuple[date, str]:

    html = call_event_id_endpoint(event_id)
    parsed_html = BeautifulSoup(html, features="lxml")
    date_sub_opening = parse_date_sub_opening(parsed_html)
    return date_sub_opening, "TODO"


def parse_event_info(event_row) -> EventInfo:
    """Assumes event_row is a event which subscriptions are not opened yet."""

    id_ = int(event_row["id"][6:])  # remove "event-" prefix
    name = remove_spans_inplace(event_row.find("div", class_="name")).text.strip()
    location = remove_spans_inplace(event_row.find("div", class_="location")).text
    categories = event_row.find("div", class_="cat").text
    series = event_row.find("div", class_="clt").text
    date = event_row.find("div", class_="date").text
    date_sub_opening, formats = parse_date_sub_opening_and_formats(id_)

    return EventInfo(
        id_=id_,
        name=name,
        location=location,
        categories=categories,
        series=series,
        formats=formats,
        date_=date,
        date_sub_opening=date_sub_opening,
    )


def build_new_event_message(event_info: EventInfo) -> str:
    message = f"""Nouvau tournoi -> {event_info.name.strip()}
    Categories : {event_info.categories.strip()}
    Localisation : {event_info.location.strip()}
    Date : {event_info.date_}
    Classements : {event_info.categories.strip()}
    Séries : {event_info.series.strip()}
    Ouverture des inscriptions : {event_info.date_sub_opening}"""
    return message


def build_sub_opened_message(event_info: EventInfo) -> str:
    message = f"""Les inscriptions du tournoi {event_info.name.strip()} sont désormais ouvertes !
    Categories : {event_info.categories.strip()}
    Localisation : {event_info.location.strip()}
    Date : {event_info.date_}
    Classements : {event_info.categories.strip()}
    Séries : {event_info.series.strip()}"""
    return message


def connect_events_db(db_config: DbConfig) -> connection:

    conn = psycopg2.connect(
        database=db_config.db_name,
        user=db_config.user,
        password=db_config.password,
        host=db_config.host_name,
        port=db_config.port,
        connect_timeout=3,
    )
    return conn


def get_new_events_notified(db_cursor: cursor) -> List[Tuple[int, bool]]:
    db_cursor.execute("""SELECT * FROM new_events_notified""")
    return db_cursor.fetchall()


def get_message_from_event_row(
    event_row: Tag, db_cursor: cursor, ids_new_events_notified: List[int], ids_events_sub_opening_notified: List[int]
) -> Optional[str]:
    div_limits = [div for div in event_row.find_all("div") if div.get("class") == ["limit"]]

    if len(div_limits) > 1:
        raise ValueError(f"Unexpected number of limits found ({len(div_limits)}) in event: {event_row}")

    if len(div_limits) == 0:
        return None

    event_info = parse_event_info(event_row)
    if event_info.id_ in ids_new_events_notified:
        # We already fired a notification for this new event, check if we need to notify of subs opening.
        if event_info.date_sub_opening <= date.today() and event_info.id_ not in ids_events_sub_opening_notified:

            # Update db
            db_cursor.execute(
                "UPDATE new_events_notified SET sub_opening_notified = true WHERE id = %s", [event_info.id_]
            )

            message = build_sub_opened_message(event_info)
            return message
    else:
        # Subscriptions are not opened yet so we log it.

        # Add a row in events database.
        db_cursor.execute("INSERT INTO new_events_notified VALUES (%s, %s);", [event_info.id_, "false"])

        message = build_new_event_message(event_info)
        return message

    return None


def get_all_pages_event_rows() -> List[Tag]:
    """
    Call badnet API and parse resulting HTML code in order to retrieve list of tournaments.
    """

    # TODO Note that as a page contains 10 events, if number of tournaments is a multiple of 10,
    #  we will probably perform an invalid request by requesting an invalid page. Downside is that we will miss some events
    #  if one day the endpoint returns more or less than 10 events.
    page = 0
    event_rows: List[Tag] = []
    page_events_rows: List[Tag] = []

    while page == 0 or (len(page_events_rows) % 10 == 0 and len(page_events_rows) == 10):
        html = call_list_events_endpoint(page=page)
        parsed_html = BeautifulSoup(html, features="lxml")
        page_events_rows = parsed_html.find_all("a", class_="row")
        logging.info(f"{page=} and {len(page_events_rows)=}")
        event_rows.extend(page_events_rows)
        page += 1

    return event_rows


def process_events(db_conn):
    """
    Retrieve events (tournaments) from badnet, and if they have not been already handled, send a signal message indicating:
    - New tournaments which subscriptions WILL open later.
    - Tournaments for which subscriptions JUST opened (ie, on the current day).
    """

    db_cursor = db_conn.cursor()
    new_events_notified = get_new_events_notified(db_cursor)

    ids_new_events_notified = [event_id for event_id, _ in new_events_notified]
    ids_events_sub_opening_notified = [
        event_id for event_id, sub_opening_notified in new_events_notified if sub_opening_notified
    ]

    event_rows = get_all_pages_event_rows()

    messages = []
    for event_row in event_rows:
        try:
            message = get_message_from_event_row(
                event_row, db_cursor, ids_new_events_notified, ids_events_sub_opening_notified
            )
            messages.append(message)
        except Exception:
            logging.exception(
                f"Unexepected error occured in get_message_from_event_row, this should be investigated. Exception was: \n {traceback.format_exc()} \n with following event_row: \n {event_row} \n\n\n"
            )

    messages = [message for message in messages if message is not None]
    if len(messages) == 0:
        messages = ["No new tournament neither tournament subscription opening today!"]
    send_signal_messages(messages)

    db_cursor.close()


# TODO Might there be some events that get published on Badnet which subs are already opened?
#  In this case we would send a single message for both "new tournament + subs opened"
