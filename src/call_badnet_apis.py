import json
import logging

import boto3
import requests  # type: ignore


def call_list_events_endpoint(page: int):
    ssm = boto3.client("ssm", region_name="eu-north-1")
    cookies = json.loads(
        ssm.get_parameter(Name="cookies_badnet_list_events", WithDecryption=True)["Parameter"]["Value"]
    )

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Accept": "text/html, */*; q=0.01",
        "Accept-Language": "fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://badnet.fr",
        "Connection": "keep-alive",
        "Referer": "https://badnet.fr/recherche-competitions",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

    data = {
        "ic_ancre": "b-search-events-result",
        "ic_t": "search_results",
        "ic_a": "851969",
        "defaut_to": "",
        "defaut_from": "",
        "hasplaces": "0",
        "opensoon": "1",
        "open": "0",
        "parabad": "0",
        "veterans": "1",
        "seniors": "1",
        "jeunes": "0",
        "coming": "1",
        "saison": "0",
        "passed": "0",
        "mixte": "0",
        "double": "0",
        "single": "0",
        "p": "0",
        "d": "0",
        "r": "0",
        "n": "0",
        "date": "",
        "rayon": "25",
        "city": "",
        "location": "",
        "departement": "-1",
        "type_isnight": "1",
        "type_promobad": "1",
        "type_team": "1",
        "type_indiv": "1",
        "type_event": "70",
        "ligue": "12",
        "page": str(page),
        "ic_ajax": "1",
        "ic_width": "1540",
        "ic_height": "805",
        "ic_language": "fr",
        "ic_colordepth": "24",
        "ic_timezoneoffset": "-60",
        "ic_java": "false",
    }

    logging.info(f"call_list_events_endpoint: Before requesting https://badnet.fr/index.php with {data=}")
    response = requests.post("https://badnet.fr/index.php", cookies=cookies, headers=headers, data=data, timeout=5)

    if response.status_code != 200:
        raise ValueError(
            f"Request failed: POST to https://badnet.fr/index.php with {headers=} and {data=}, got response: {response.content=})"
        )

    logging.info(
        f"call_list_events_endpoint: Request done, response {response.content=} and status: {response.status_code=}"
    )
    return response.content.decode("utf_8")


def call_event_id_endpoint(event_id: int):
    ssm = boto3.client("ssm", region_name="eu-north-1")
    cookies = json.loads(ssm.get_parameter(Name="cookies_badnet_event_id", WithDecryption=True)["Parameter"]["Value"])

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Accept": "text/html, */*; q=0.01",
        "Accept-Language": "fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://badnet.fr",
        "Connection": "keep-alive",
        "Referer": f"https://badnet.fr/tournoi/public?eventid={event_id}",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

    data = {
        "ic_a": "852480",
        "inside_page": "",
        "mustache": "1",
        "in_process": "true",
        "ic_width": "1540",
        "ic_height": "883",
        "ic_language": "fr",
        "ic_colordepth": "24",
        "ic_timezoneoffset": "-60",
        "ic_java": "false",
        "eventid": str(event_id),
        "ic_ajax": "1",
    }

    logging.info(f"call_event_id_endpoint: Before requesting https://badnet.fr/index.php with {data=}")
    response = requests.post("https://badnet.fr/index.php", cookies=cookies, headers=headers, data=data, timeout=5)

    if response.status_code != 200:
        raise ValueError(
            f"Request failed: POST to https://badnet.fr/index.php with {headers=} and {data=}, got response: {response.content=})"
        )

    logging.info("call_event_id_endpoint: Request done")
    return response.content.decode("utf_8")
