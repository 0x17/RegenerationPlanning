import sys

import gurobipy as gp
from gurobipy import GRB

import generator
import result_plotter
from gurobi_utils import binvar, posvar
from instance_helpers import values_from_instance, sets_from_instance


def extend_exogenous_data_with_dummy_external_good(I, K, ekt, eks, eksreal, due, c):
    I += [len(I)]

    def add_entry_for_external_good(param1d):
        return [param1d[i - 1] if i > 0 else -1 for i in I]

    def add_row_for_external_good(param2d):
        return [[param2d[i - 1][k] if i > 0 else -1 for k in K] for i in I]

    ekt, eks, eksreal = map(add_row_for_external_good, [ekt, eks, eksreal])
    due, c = map(add_entry_for_external_good, [due, c])

    return I, ekt, eks, eksreal, due, c


def solve(instance, origin_restricted=False):
    I, K, S, T = sets_from_instance(instance)
    ekt, eks, eksreal, due, c, rd, rc, hc, d, bd, bc = values_from_instance(instance)

    I, ekt, eks, eksreal, due, c = extend_exogenous_data_with_dummy_external_good(I, K, ekt, eks, eksreal, due, c)

    # first good i=0 is external (dummy) good
    # first component k=0 is fan. disassembly: outside -> inside (fan is first), reassembly: inside -> outside (fan is last)
    # first damage pattern s=0 is 'good as new', increasing pattern means increased damage
    i_external_good, k_fan_component, s_good_as_new = 0, 0, 0
    internal_items = I[1:]

    def is_internal(i):
        return i != i_external_good

    try:
        m = gp.Model("regeneration-planning-mip")

        # m.params.output_flag = 0
        m.params.threads = 0

        def ub_for_y(i, k, s, t):
            return GRB.INFINITY if 0 < t < len(T) else 0.0

        def ub_for_z(i, k, s, t):
            return  float(t != len(T) and s != 0)

        def ub_for_x(i, istar, k, t):
            return float(is_internal(istar))

        def ub_for_w(k, s, t):
            return float(not origin_restricted or s == s_good_as_new)

        z = binvar(m, 'z', [I, K, S, T], ub=ub_for_z)  # repair
        w = binvar(m, 'w', [K, S, T], ub=ub_for_w)  # order

        x = binvar(m, 'x', [I, I, K, T], ub=ub_for_x)  # provisioning: origin i1 to reassembly target i2

        Y = posvar(m, 'Y', [I, K, S, T], ub=ub_for_y)  # inventory levels
        v = posvar(m, 'v', [I])  # delays

        def setup_objective():
            delay_costs = gp.quicksum(c[i] * v[i] for i in internal_items)
            housing_costs = gp.quicksum(hc[k][s] * Y[(i, k, s, t)] for i in I for k in K for s in S for t in T)
            order_costs = gp.quicksum(bc[k][s] * w[(k, s, t)] for k in K for s in S for t in T)
            m.setObjective(delay_costs + housing_costs + order_costs, GRB.MINIMIZE)

        def add_core_constraints():
            def provision_time_for_component(i, k): return gp.quicksum(x[(iorigin, i, k, t)] * t for iorigin in I for t in T)

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

            m.addConstrs((gp.quicksum(x[(i, istar, k, t)] for i in I for t in T) == 1
                          for istar in internal_items for k in K), 'provision_each_internal_once')

            if origin_restricted:
                m.addConstr(gp.quicksum(x[(i, istar, k, t)] for i in internal_items for k in K for t in T for istar in internal_items if i != istar) == 0, name='prevent_provision_from_other_internal_when_origin_restricted')

        def add_balance_equations():
            def repair_arrivals(i, k, t):
                return gp.quicksum(z[(i, k, s, tau)] for s in S for tau in T if tau == t - d[k][s])

            def order_arrivals(k, s, t):
                return gp.quicksum(w[(k, s, tau)] for tau in T if tau == t - bd[k][s])

            def provisioning_to_any_internal_target(i, k, t):
                return gp.quicksum(x[(i, i_target, k, t)] for i_target in internal_items)

            m.addConstrs((Y[(i, k, s_good_as_new, t + 1)] ==
                          Y[(i, k, s_good_as_new, t)] +
                          (order_arrivals(k, s_good_as_new, t) if i == i_external_good else 0) +
                          repair_arrivals(i, k, t) +
                          -provisioning_to_any_internal_target(i, k, t)
                          for i in I for k in K for t in T[:-1]), 'balance_sa')

            def disassembly_arrival_count(i, k, s, t):
                return int(eks[i][k] == s and ekt[i][k] == t)

            m.addConstrs((Y[(i, k, s, t + 1)] ==
                          Y[(i, k, s, t)] +
                          (disassembly_arrival_count(i, k, s, t) if is_internal(i) else 0) +
                          (order_arrivals(k, s, t) if i == i_external_good else 0) +
                          -z[(i, k, s, t)]
                          for i in I for k in K for s in S[1:] for t in T[:-1]), 'balance_nsa')

        setup_objective()
        add_core_constraints()
        add_balance_equations()

        m.optimize()

        if m.status == GRB.INFEASIBLE:
            raise Exception('No solution found!')

        def nonzero_times_in_result(var):
            return {k[:-1]: k[-1] for k, v in var.items() if v.x > 0.0}

        return dict(
            repair_starts=nonzero_times_in_result(z),
            order_starts=nonzero_times_in_result(w),
            ready_times=nonzero_times_in_result(x),
            delays=[v[i].x for i in internal_items],

            sa_inventory_levels={(i, k): [Y[i, k, 0, t].x for t in T] for i in I for k in K},
            nsa_inventory_levels={(i, k, s): [Y[i, k, s, t].x for t in T] for i in I for k in K for s in S[1:]},

            delay_costs=sum(c[i] * v[i].x for i in internal_items),
            housing_costs=sum(hc[k][s] * Y[(i, k, s, t)].x for i in I for k in K for s in S for t in T),
            order_costs=sum(bc[k][s] * w[(k, s, t)].x for k in K for s in S for t in T),
            total_costs=m.objVal)

    except gp.GurobiError as e:
        print(f'Error code {e.errno}: {e}')
    except AttributeError:
        print('Encountered an attribute error')


def main(args):
    instance = generator.generate_instance(23, 2, 3, 3, nperiods=160)
    res = solve(instance, origin_restricted=False)
    # result_printer.print_results(instance, res)
    result_plotter.print_results(instance, res)


if __name__ == '__main__':
    main(sys.argv)
