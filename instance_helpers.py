def sets_from_instance(instance):
    return (list(range(instance[k])) for k in ['ngoods', 'ncomponents', 'ndamagepatterns', 'nperiods'])


def values_from_instance(instance):
    return (instance[k] for k in ['ekt', 'eks', 'eksreal', 'due', 'c', 'rd', 'rc', 'hc', 'd', 'bd', 'bc'])