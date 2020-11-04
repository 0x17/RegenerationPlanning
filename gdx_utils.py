def set1d(db, name, count, description):
    s = db.add_set(name, 1, description)
    for i in range(count):
        s.add_record(f'{name}{i + 1}')
    return s


def sets1d(db, names, sizes, descriptions):
    return [set1d(db, name, sizes[ix], descriptions[ix]) for ix, name in enumerate(names)]


def parameter2d(db, param_id, set1id, set2id, values, description):
    param = db.add_parameter(param_id, 2, description)
    for i in range(len(values)):
        for j in range(len(values[0])):
            param.add_record([f'{set1id}{i + 1}', f'{set2id}{j + 1}']).value = values[i][j]
    return param


def parameter1d(db, param_id, set_id, values, description):
    param = db.add_parameter(param_id, 1, description)
    for i, v in enumerate(values):
        param.add_record(f'{set_id}{i + 1}').value = v
    return param


def add_params_to_database(db, obj, params_dict):
    for k, v in params_dict.items():
        set_names_str, description = v
        set_names = list(set_names_str)
        dim = len(set_names)
        if dim == 1:
            parameter1d(db, k, set_names[0], obj[k], description)
        elif dim == 2:
            parameter2d(db, k, set_names[0], set_names[1], obj[k], description)


def add_sets_to_database(db, obj, sets_dict):
    for k, v in sets_dict.items():
        cardinality_key, description = v
        set1d(db, k, obj[cardinality_key], description)
