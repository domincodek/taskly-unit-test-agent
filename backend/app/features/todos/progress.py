def remaining_count(completed: list[bool]) -> int:
    return sum(1 for item in completed if not item)


def completion_percent(completed: list[bool]) -> int:
    if not completed:
        return 0
    done = sum(1 for item in completed if item)
    return round(done * 100 / len(completed))


def open_label(completed: list[bool]) -> str:
    remaining = remaining_count(completed)
    if remaining == 0:
        return "All tasks are complete."
    return f"{remaining} still open"
