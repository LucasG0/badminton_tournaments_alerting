# badminton_tournaments_alerting

The purpose of this project is to send a Signal alert each time a new badminton tournament is announced in Ile de France, as well as on the day registration opens, in order to sign up quickly and avoid being placed on a waiting list.

This project is hosted on AWS EC2 and scheduled to run twice a day. AWS RDS is used to store tournaments ids having already been handled,
in order to avoid sending duplicated alerts. Secrets are stored in AWS Parameter Store. Messages are sent to a Signal account using https://github.com/bbernhard/signal-cli-rest-api.
