"""Unit tests and integration tests."""

from pyngspicelab.example_function import example_1

def test_myfunc():
    """Test function for example_1()."""
    test_list = [1, 2, 3]

    result = example_1(test_list)

    assert result == 6
