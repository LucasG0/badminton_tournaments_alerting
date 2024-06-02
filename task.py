import logging
import random
import subprocess
import time

import boto3

from src.db_config import EVENTS_DB_CONFIG
from src.process_events import connect_events_db, process_events

logging.basicConfig(format="%(asctime)s %(levelname)-8s %(message)s", level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S")

DB_INSTANCE_IDENTIFIER = "badnet-events"

# Create an RDS client
RDS_CLIENT = boto3.client("rds", region_name="eu-north-1")


if __name__ == "__main__":
    time_before_task = random.randint(0, 1800)
    logging.info(f"Sleeping for {time_before_task} seconds before running task")
    time.sleep(time_before_task)

    # Git pull
    result = subprocess.run(
        "cd /home/ec2-user/badminton_tournaments_alerting && git pull",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    logging.info("Successfully performed git pull")

    if result.returncode != 0:
        raise ValueError(f"`git pull` failed with error: {result.stderr}")

    # Process Badnet tournaments and maybe send alerts as signal messages
    db_conn = connect_events_db(EVENTS_DB_CONFIG)
    process_events(db_conn)
    db_conn.commit()
    db_conn.close()

    logging.info("Events processed")
