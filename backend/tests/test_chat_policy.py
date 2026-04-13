from app.services.chat_policy import should_rollover_before_append


def test_no_rollover_at_498_plus_pair() -> None:
    assert not should_rollover_before_append(message_count=498, incoming_messages=2, max_messages=500)


def test_rollover_at_499_plus_pair() -> None:
    assert should_rollover_before_append(message_count=499, incoming_messages=2, max_messages=500)


def test_rollover_when_already_full() -> None:
    assert should_rollover_before_append(message_count=500, incoming_messages=2, max_messages=500)
