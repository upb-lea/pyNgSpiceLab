"""Exemplary function."""
import numpy as np

def example_1(my_list: list[float]) -> float:
    """
    Return the sum of the list.

    :param my_list: List, e.g. [1, 2, 3]
    :return: sum of all list elements
    """
    return np.sum(my_list)


if __name__ == "__main__":
    print(example_1([1, 3, 5]))
