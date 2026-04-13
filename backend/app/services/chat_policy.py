"""Pure helpers for chat transcript limits — easy to unit test."""


def should_rollover_before_append(*, message_count: int, incoming_messages: int, max_messages: int) -> bool:
    """Return True if appending `incoming_messages` would exceed the active thread cap."""
    return message_count + incoming_messages > max_messages
