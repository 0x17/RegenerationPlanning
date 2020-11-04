import itertools
import sys

import gurobipy as gp
from gurobipy import GRB

import generator

from instance_helpers import values_from_instance, sets_from_instance
from utils import strs


def common_var(model, name, ranges, vtype, lb=0, ub=GRB.INFINITY):
    def ub_fn(x):
        return ub if not hasattr(ub, '__call__') else (ub(*x) if isinstance(x, tuple) else ub(x))

    if len(ranges) == 1:
        return [model.addVar(vtype=vtype, lb=lb, ub=ub_fn(i), name=f'{name}_{i}') for i in ranges[0]]
    return {tuple: model.addVar(vtype=vtype, lb=lb, ub=ub_fn(tuple), name=name + '_' + '_'.join(strs(tuple))) for tuple in itertools.product(*ranges)}


def binvar(model, name, ranges, ub=1.0):
    return common_var(model, name, ranges, GRB.BINARY, ub=ub)


def posvar(model, name, ranges, ub=GRB.INFINITY):
    return common_var(model, name, ranges, GRB.CONTINUOUS, ub=ub)


def nonzero_times_in_result(var):
    return {k[:-1]: k[-1] for k, v in var.items() if v.x > 0.0}


def extend_exogenous_data_with_dummy_external_good(I, K, ekt, eks, due, c):
    I += [len(I)]

    def add_entry_for_external_good(param1d):
        return [param1d[i - 1] if i > 0 else -1 for i in I]

    def add_row_for_external_good(param2d):
        return [[param2d[i - 1][k] if i > 0 else -1 for k in K] for i in I]

    ekt, eks = map(add_row_for_external_good, [ekt, eks])
    due, c = map(add_entry_for_external_good, [due, c])

    return I, ekt, eks, due, c


def solve(instance):
    origin_restricted = False

    # first good i=0 is external (dummy) good
    # first component k=0 is fan. disassembly: outside -> inside (fan is first), reassembly: inside -> outside (fan is last)
    # first damage pattern s=0 is 'good as new', increasing pattern means increased damage

    I, K, S, T = sets_from_instance(instance)
    ekt, eks, due, c, rd, rc, hc, d, bd, bc = values_from_instance(instance)

    I, ekt, eks, due, c = extend_exogenous_data_with_dummy_external_good(I, K, ekt, eks, due, c)

    try:
        m = gp.Model("regeneration-planning-mip")

        def ub_for_y(i, k, s, t):
            return GRB.INFINITY if 0 < t < len(T) else 0.0

        def ub_for_z(i, k, s, t):
            return 0.0 if t == len(T) or s == 0 or (origin_restricted and s > 0) else GRB.INFINITY

        z = binvar(m, 'z', [I, K, S, T], ub=ub_for_z)  # repair internal
        w = binvar(m, 'w', [K, S, T])  # order

        x = binvar(m, 'x', [I, K, T])  # provisioning
        xint = binvar(m, 'xint', [I, K, T])  # provision internal
        xext = binvar(m, 'xext', [I, K, T])  # provision external

        Y = posvar(m, 'Y', [I, K, S, T], ub=ub_for_y)  # inventory levels
        v = posvar(m, 'v', [I])  # delays

        def setup_objective():
            delay_costs = gp.quicksum(c[i] * v[i] for i in I[1:])
            housing_costs = gp.quicksum(hc[k][s] * Y[(i, k, s, t)] for i in I for k in K for s in S for t in T)
            order_costs = gp.quicksum(bc[k][s] * w[(k, s, t)] for k in K for s in S for t in T)
            m.setObjective(delay_costs + housing_costs + order_costs, GRB.MINIMIZE)

        def add_core_constraints():
            def provision_time_for_component(i, k): return gp.quicksum(x[(i, k, t)] * t for t in T)

            def provision_time_of_fan(i): return provision_time_for_component(i, 0)

            m.addConstrs((v[i] >= rd[0] + provision_time_of_fan(i) - due[i]
                          for i in I[1:]), 'delay')

            m.addConstrs((provision_time_for_component(i, k - 1) >= rd[k] + provision_time_for_component(i, k)
                          for i in I[1:] for k in K[1:]), 'reassembly_sequence')

            # FIXME: really needed?
            def repair_start(i, k, s):
                return gp.quicksum(z[(i, k, s, t)] * t for t in T)

            m.addConstrs((repair_start(i, k, s) >= ekt[i][k]
                          for i in I[1:] for k in K for s in S if eks[i][k] == s), 'repair_after_arrival')

            def in_time_window_for_repair(k, s, t, tau):
                return t - d[k][s] + 1 <= tau <= t

            m.addConstrs((gp.quicksum(z[(i, k, s, tau)] for i in I for s in S for tau in T if in_time_window_for_repair(k, s, t, tau)) <= rc[k]
                          for k in K for t in T), 'capacity')

            def repair_count(i, k):
                return gp.quicksum(z[(i, k, s, t)] for s in S for t in T)

            m.addConstrs((repair_count(i, k) <= 1
                          for i in I[1:] for k in K), 'repair_internal_max_once')

            m.addConstrs((gp.quicksum(x[(i, k, t)] for t in T) == 1
                          for i in I[1:] for k in K), 'provision_each_internal_once')

            m.addConstrs((x[(i, k, t)] == xint[(i, k, t)] + xext[(i, k, t)]
                          for i in I[1:] for k in K for t in T), 'linkx')

        def add_balance_equations():
            m.addConstrs((Y[(i, k, 0, t + 1)] ==
                          Y[(i, k, 0, t)] +
                          gp.quicksum(z[(i, k, s, tau)] for s in S for tau in T if tau == t - d[k][s]) -
                          xint[(i, k, t)]
                          for i in I[1:] for k in K for t in T[:-1]), 'balance_sa_internal')

            m.addConstrs((Y[(0, k, 0, t + 1)] ==
                          Y[(0, k, 0, t)] +
                          gp.quicksum(w[(k, 0, tau)] for tau in T if tau == t - bd[k][0]) +
                          gp.quicksum(z[(0, k, s, tau)] for s in S for tau in T if tau == t - d[k][s]) -
                          gp.quicksum(xext[(i, k, t)] for i in I[1:])
                          for k in K for t in T[:-1]), 'balance_sa_external')

            m.addConstrs((Y[(i, k, s, t + 1)] ==
                          Y[(i, k, s, t)] +
                          (1 if eks[i][k] == s and ekt[i][k] == t else 0) -
                          z[(i, k, s, t)]
                          for i in I[1:] for k in K for s in S[1:] for t in T[:-1]), 'balance_nsa_internal')

            m.addConstrs((Y[(0, k, s, t + 1)] ==
                          Y[(0, k, s, t)] +
                          gp.quicksum(w[(k, s, tau)] for tau in T if tau == t - bd[k][s]) -
                          z[(0, k, s, t)]
                          for k in K for s in S[1:] for t in T[:-1]), 'balance_nsa_external')

        setup_objective()
        add_core_constraints()
        add_balance_equations()

        m.optimize()

        return dict(
            repair_starts=nonzero_times_in_result(z),
            order_starts=nonzero_times_in_result(w),
            ready_times=nonzero_times_in_result(x),
            delays=[v[i].x for i in I],
            sa_inventory_levels={(i, k): [Y[i, k, 0, t].x for t in T] for i in I for k in K},
            nsa_inventory_levels={(i, k, s): [Y[i, k, s, t].x for t in T] for i in I for k in K for s in S[1:]},
            total_costs=m.objVal)

    except gp.GurobiError as e:
        print(f'Error code {e.errno}: {e}')
    except AttributeError:
        print('Encountered an attribute error')


def print_results(instance, res_dict):
    print(f'Costs of this regeneration plan are in total {res_dict["total_costs"]} monetary units')

    def inc(tpl):
        return tuple(v+1 for v in tpl)

    def named(index_names, tpl):
        assert(len(index_names) == len(tpl))
        return '(' + ';'.join(f'{index_names[ix]}={v}' for ix, v in enumerate(tpl)) + ')'

    def print_result_line(caption, res_dict_key, index_names_str, sep=', '):
        newline = '\n'
        index_names = list(index_names_str)
        print(f'{caption}:{sep if sep == newline else " "}{sep.join("piece " + str(named(index_names, inc(k))) + " at " + str(v) for k, v in res_dict[res_dict_key].items())}')

    print_result_line('Repairs', 'repair_starts', 'iks')
    print_result_line('Orders', 'order_starts', 'ks')
    print_result_line('Provisioning times', 'ready_times', 'ik', sep='\n')

    for i in range(instance['ngoods']):
        print(f'Delay of good {i+1} is {res_dict["delays"][i]} time units')


def main(args):
    instance = generator.generate_instance(23, 2, 2, 2, 30)
    res = solve(instance)
    print_results(instance, res)


if __name__ == '__main__':
    main(sys.argv)
