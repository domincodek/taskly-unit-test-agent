__agent__ = "taskly-unit-test-agent"

from app.features.todos.progress import remaining_count, completion_percent

def test_remaining_count_case_0():
    assert remaining_count([]) == 0

def test_remaining_count_case_1():
    assert remaining_count([False]) == 1

def test_remaining_count_case_2():
    assert remaining_count([False, True]) == 1

def test_completion_percent_case_0():
    assert completion_percent([]) == 0

def test_completion_percent_case_1():
    assert completion_percent([False]) == 0

def test_completion_percent_case_2():
    assert completion_percent([False, True]) == 50
