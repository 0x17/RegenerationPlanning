from gurobipy import GRB
from utils import strs
import itertools


def common_var(model, name, ranges, vtype, lb=0, ub=GRB.INFINITY):
    def ub_fn(x):
        return ub if not hasattr(ub, '__call__') else (ub(*x) if isinstance(x, tuple) else ub(x))

    if len(ranges) == 1:
        return [model.addVar(vtype=vtype, lb=lb, ub=ub_fn(i), name=f'{name}_{i}') for i in ranges[0]]
    return {tpl: model.addVar(vtype=vtype, lb=lb, ub=ub_fn(tpl), name=name + '_' + '_'.join(strs(tpl))) for tpl in itertools.product(*ranges)}


def binvar(model, name, ranges, ub=1.0):
    return common_var(model, name, ranges, GRB.BINARY, ub=ub)


def posvar(model, name, ranges, ub=GRB.INFINITY):
    return common_var(model, name, ranges, GRB.CONTINUOUS, ub=ub)
