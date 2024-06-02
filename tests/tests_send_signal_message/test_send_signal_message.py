from src.message_sender import send_signal_messages


def test_send_signal_message():
    # If no error is raised, it means messages have been correctly sent
    send_signal_messages(["Message 1 sent from a unit test!", "Message 2 sent from a unit test!"])
