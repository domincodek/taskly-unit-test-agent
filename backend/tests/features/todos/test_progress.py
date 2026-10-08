__agent__ = "taskly-unit-test-agent"

from app.features.todos.progress import remaining_count, completion_percent, open_label

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

def test_open_label_case_0():
    assert open_label([]) == 'All tasks are complete.'

def test_open_label_case_1():
    assert open_label([False]) == '1 still open'

def test_open_label_case_2():
    assert open_label([False, True]) == '1 still open'
