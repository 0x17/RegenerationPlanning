import sys

import gurobipy as gp
from gurobipy import GRB

import generator

from instance_helpers import values_from_instance, sets_from_instance

from gurobi_utils import binvar, posvar


def nonzero_times_in_result(var):
    return {k[:-1]: k[-1] for k, v in var.items() if v.x > 0.0}


def extend_exogenous_data_with_dummy_external_good(I, K, ekt, eks, eksreal, due, c):
    I += [len(I)]

    def add_entry_for_external_good(param1d):
        return [param1d[i - 1] if i > 0 else -1 for i in I]

    def add_row_for_external_good(param2d):
        return [[param2d[i - 1][k] if i > 0 else -1 for k in K] for i in I]

    ekt, eks, eksreal = map(add_row_for_external_good, [ekt, eks, eksreal])
    due, c = map(add_entry_for_external_good, [due, c])

    return I, ekt, eks, eksreal, due, c


def solve(instance, origin_restricted = False):
    I, K, S, T = sets_from_instance(instance)
    ekt, eks, eksreal, due, c, rd, rc, hc, d, bd, bc = values_from_instance(instance)
    I, ekt, eks, eksreal, due, c = extend_exogenous_data_with_dummy_external_good(I, K, ekt, eks, eksreal, due, c)

    # first good i=0 is external (dummy) good
    # first component k=0 is fan. disassembly: outside -> inside (fan is first), reassembly: inside -> outside (fan is last)
    # first damage pattern s=0 is 'good as new', increasing pattern means increased damage
    i_external_good, k_fan_component, s_good_as_new = 0, 0, 0
    internal_items = I[1:]

    try:
        m = gp.Model("regeneration-planning-mip")

        def ub_for_y(i, k, s, t):
            return GRB.INFINITY if 0 < t < len(T) else 0.0

        def ub_for_z(i, k, s, t):
            return 0.0 if t == len(T) or s == 0 or (origin_restricted and i == i_external_good) else GRB.INFINITY

        z = binvar(m, 'z', [I, K, S, T], ub=ub_for_z)  # repair internal
        w = binvar(m, 'w', [K, S, T])  # order

        x = binvar(m, 'x', [I, K, T])  # provisioning
        xint = binvar(m, 'xint', [I, K, T])  # provision internal
        xext = binvar(m, 'xext', [I, K, T])  # provision external

        Y = posvar(m, 'Y', [I, K, S, T], ub=ub_for_y)  # inventory levels
        v = posvar(m, 'v', [I])  # delays

        def setup_objective():
            delay_costs = gp.quicksum(c[i] * v[i] for i in internal_items)
            housing_costs = gp.quicksum(hc[k][s] * Y[(i, k, s, t)] for i in I for k in K for s in S for t in T)
            order_costs = gp.quicksum(bc[k][s] * w[(k, s, t)] for k in K for s in S for t in T)
            m.setObjective(delay_costs + housing_costs + order_costs, GRB.MINIMIZE)

        def add_core_constraints():
            def provision_time_for_component(i, k): return gp.quicksum(x[(i, k, t)] * t for t in T)

            def provision_time_of_fan(i): return provision_time_for_component(i, k_fan_component)

            m.addConstrs((v[i] >= rd[k_fan_component] + provision_time_of_fan(i) - due[i]
                          for i in internal_items), 'delay')

            m.addConstrs((provision_time_for_component(i, k - 1) >= rd[k] + provision_time_for_component(i, k)
                          for i in internal_items for k in K[1:]), 'reassembly_sequence')

            def in_time_window_for_repair(k, s, t, tau):
                return t - d[k][s] + 1 <= tau <= t

            m.addConstrs((gp.quicksum(z[(i, k, s, tau)] for i in I for s in S for tau in T if in_time_window_for_repair(k, s, t, tau)) <= rc[k]
                          for k in K for t in T), 'capacity')

            def repair_count(i, k):
                return gp.quicksum(z[(i, k, s, t)] for s in S for t in T)

            m.addConstrs((repair_count(i, k) <= 1
                          for i in internal_items for k in K), 'repair_internal_max_once')

            m.addConstrs((gp.quicksum(x[(i, k, t)] for t in T) == 1
                          for i in internal_items for k in K), 'provision_each_internal_once')

            m.addConstrs((x[(i, k, t)] == xint[(i, k, t)] + xext[(i, k, t)]
                          for i in internal_items for k in K for t in T), 'linkx')

        def add_balance_equations():
            def repair_arrivals(i, k, t):
                return gp.quicksum(z[(i, k, s, tau)] for s in S for tau in T if tau == t - d[k][s])

            m.addConstrs((Y[(i, k, s_good_as_new, t + 1)] ==
                          Y[(i, k, s_good_as_new, t)] +
                          repair_arrivals(i, k, t) -
                          xint[(i, k, t)]
                          for i in internal_items for k in K for t in T[:-1]), 'balance_sa_internal')

            m.addConstrs((Y[(i_external_good, k, s_good_as_new, t + 1)] ==
                          Y[(i_external_good, k, s_good_as_new, t)] +
                          gp.quicksum(w[(k, s_good_as_new, tau)] for tau in T if tau == t - bd[k][s_good_as_new]) +
                          repair_arrivals(i_external_good, k, t) -
                          gp.quicksum(xext[(i, k, t)] for i in internal_items)
                          for k in K for t in T[:-1]), 'balance_sa_external')

            def disassembly_arrival_count(i, k, s, t):
                return int(eks[i][k] == s and ekt[i][k] == t)

            m.addConstrs((Y[(i, k, s, t + 1)] ==
                          Y[(i, k, s, t)] +
                          disassembly_arrival_count(i, k, s, t) -
                          z[(i, k, s, t)]
                          for i in internal_items for k in K for s in S[1:] for t in T[:-1]), 'balance_nsa_internal')

            m.addConstrs((Y[(i_external_good, k, s, t + 1)] ==
                          Y[(i_external_good, k, s, t)] +
                          gp.quicksum(w[(k, s, tau)] for tau in T if tau == t - bd[k][s]) -
                          z[(i_external_good, k, s, t)]
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
    print(f'\nCosts of this regeneration plan are in total {res_dict["total_costs"]} monetary units')

    def inc(tpl):
        return tuple(v + 1 for v in tpl)

    def named(index_names, tpl):
        assert (len(index_names) == len(tpl))
        return '(' + ';'.join(f'{index_names[ix]}={v}' for ix, v in enumerate(tpl)) + ')'

    def print_result_line(caption, res_dict_key, index_names_str, sep=', ', with_arrival=None):
        newline = '\n'
        index_names = list(index_names_str)

        def arrival_str(arrival_data_func, tpl):
            i, k = tpl
            eks, ekt = arrival_data_func(i, k)
            return f' arrival(s={eks},t={ekt})'

        print(f'\n{caption}:{sep if sep == newline else " "}{sep.join("piece " + str(named(index_names, inc(k))) + (arrival_str(with_arrival, k) if with_arrival is not None else "") + " at period " + str(v) for k, v in res_dict[res_dict_key].items())}')

    print_result_line('Repairs', 'repair_starts', 'iks')
    print_result_line('Orders', 'order_starts', 'ks')
    print_result_line('Provisioning times', 'ready_times', 'ik', sep='\n', with_arrival=lambda i, k: (instance['eks'][i-1][k], instance['ekt'][i-1][k]))

    print('')

    for i in range(instance['ngoods']):
        print(f'Delay of good {i + 1} is {res_dict["delays"][i]} time units')


def main(args):
    instance = generator.generate_instance(23, 2, 2, 2, 30)
    res = solve(instance)
    print_results(instance, res)


if __name__ == '__main__':
    main(sys.argv)
