import random


def set_seed(v): random.seed(v)


def random_values_discrete(count, min, max):
    return [random.randint(min, max) for i in range(count)]


def random_values_matrix_row_ascending_discrete(nrows, ncols, min, max):
    return [list(sorted(random_values_discrete(ncols, min, max))) for i in range(nrows)]


def random_values_matrix_discrete(nrows, ncols, min, max):
    return [[random.randint(min, max) for j in range(ncols)] for i in range(nrows)]


def random_values(count, min, max):
    return [random.random() * (max - min) + min for i in range(count)]


def random_values_descending(count, min, max):
    return list(sorted(random_values(count, min, max), reverse=True))


def random_values_ascending(count, min, max):
    return list(sorted(random_values(count, min, max)))


def random_values_matrix_row_ascending(nrows, ncols, min, max):
    return [random_values_ascending(ncols, min, max) for i in range(nrows)]


def remove_none_entries(dict):
    return {k: v for k, v in dict.items() if v is not None}

def strs(coll):
    return (str(v) for v in coll)