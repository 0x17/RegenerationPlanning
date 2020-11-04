import sys
import utils

import generator

from instance_helpers import sets_from_instance, values_from_instance


def resource_busy(k, repair_starts, repair_durations, damage_patterns, t):
    any(val is not None and
        k == k2 and
        val <= t < val + repair_durations[k][damage_patterns[(i, k)] - 1]
        for (i, k2), val in repair_starts.items())


# generate a schedule
# input:
# - exogenous instance parameters
# - assigned sources for each item: (i,k) or extern (only consider ordering new items at first)
# - priorities for repairs
# output:
# - repair and order starts
def generate_schedule(instance, item_sources, good_priorities):
    I, K, S, T = sets_from_instance(instance)
    ekt, eks, due, c, rd, rc, hc, d, bd, bc = values_from_instance(instance)
    items = [(i, k) for i in I for k in K]

    damage_patterns = {(i, k): eks[i][k] for i, k in items}
    repair_starts = {(i, k): None for i, k in items}
    order_starts = {(i, k): None for i, k in items}

    for i in good_priorities:
        for k in K:
            src = item_sources[(i, k)]
            if src is None:
                order_starts[(i, k)] = 0
            else:
                t = ekt[i][k]
                while resource_busy(k, repair_starts, d, damage_patterns, t):
                    t += 1
                repair_starts[(i, k)] = t

    return dict(repair_starts=utils.remove_none_entries(repair_starts),
                order_starts=utils.remove_none_entries(order_starts))


def derive_costs_from_schedule(instance, repair_starts, order_starts):
    I, K, S, T = sets_from_instance(instance)
    ekt, eks, due, c, rd, rc, hc, d, bd, bc = values_from_instance(instance)
    items = [(i, k) for i in I for k in K]

    def ready_date_for_item(i, k):
        if repair_starts[(i, k)] is not None:
            return repair_starts[(i, k)] + d[k][eks[i][k] - 1]
        elif order_starts[(i, k)] is not None:
            return order_starts[(i, k)] + bd[k][0]
        else:
            return 0

    ready_dates = {(i, k): ready_date_for_item(i, k) for i, k in items}
    delay_costs = sum(max(0, ready_dates[(i, 0)] - instance['due'][i]) * instance['c'][i] for i in I)
    order_costs = sum(bc[k][instance['eks'][i][k]] for (i, k), order_st in order_starts.items())
    # TODO: Add housing costs
    return delay_costs + order_costs


def main(args):
    instance = generator.generate_instance(23, 2, 2, 2, 30)
    res = generate_schedule(instance, item_sources={(0, 0): None,
                                                    (0, 1): (1, 1),
                                                    (1, 0): (0, 0),
                                                    (1, 1): (0, 1)},
                            good_priorities=[0, 1])
    print(res)


if __name__ == '__main__':
    main(sys.argv)
