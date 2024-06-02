import logging

import pytest

from src import process_events

# This test just makes sure main program runs without error while calling Badnet API,
# whether some notifications should be sent or not.
from tests.tests_build_messages.test_build_messages_badnet_mocked import (
    EVENTS_DB_TEST_CONFIG,
)


@pytest.mark.skip(
    reason="If Badnet API breaks, we should know it from prod logs. This test is just a convenient way to run the whole code against a testing DB."
)
def test_build_messages_with_badnet():

    logging.info("Connecting to RDS test instance")
    db_conn = process_events.connect_events_db(EVENTS_DB_TEST_CONFIG)
    logging.info("Starting to process events")
    process_events.process_events(db_conn)
    db_conn.close()

    # Do not commit so database remains empty
