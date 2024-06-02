from dataclasses import dataclass

import boto3


@dataclass
class DbConfig:
    db_name: str
    host_name: str
    user: str
    password: str
    port: str


_ssm = boto3.client("ssm", region_name="eu-north-1")

EVENTS_DB_CONFIG = DbConfig(
    db_name=_ssm.get_parameter(Name="prod_name_badnet_db")["Parameter"]["Value"],
    user=_ssm.get_parameter(Name="prod_username_badnet_db")["Parameter"]["Value"],
    password=_ssm.get_parameter(Name="prod_password_badnet_db", WithDecryption=True)["Parameter"]["Value"],
    port=_ssm.get_parameter(Name="prod_port_badnet_db")["Parameter"]["Value"],
    host_name=_ssm.get_parameter(Name="prod_host_badnet_db")["Parameter"]["Value"],
)
