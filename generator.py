from utils import *


def generate_instance(seed, ngoods, ncomponents, ndamagepatterns, nperiods=None):
    set_seed(seed)

    repair_duration = random_values_matrix_row_ascending_discrete(ncomponents, ndamagepatterns, min=1, max=62)
    reassembly_duration = random_values_discrete(ncomponents, min=1, max=4)
    disassembly_arrival = random_values_matrix_row_ascending_discrete(ngoods, ncomponents, min=0, max=15)

    if nperiods is None:
        upper_bound_for_total_repair_time = sum(max(repair_duration[k][s] for s in range(ndamagepatterns)) for i in range(ngoods) for k in range(ncomponents))
        upper_bound_for_total_reassembly_time = sum(max(repair_duration[k][s] for s in range(ndamagepatterns)) for i in range(ngoods) for k in range(ncomponents))
        latest_arrival_from_disassembly = max(disassembly_arrival[i][k] for i in range(ngoods) for k in range(ncomponents))

        nperiods = upper_bound_for_total_repair_time + upper_bound_for_total_reassembly_time + latest_arrival_from_disassembly

    return dict(
        # Set cardinalities
        ngoods=ngoods,
        ncomponents=ncomponents,
        ndamagepatterns=ndamagepatterns,
        nperiods=nperiods,

        # Disassembly arrival information
        # time of arrival of item i, k
        ekt=disassembly_arrival,
        # damage pattern at arrival of item i, k (predicted)
        eks=random_values_matrix_discrete(ngoods, ncomponents, min=1, max=ndamagepatterns - 1),
        # damage pattern after inspection of item i, k (actual)
        eksreal=random_values_matrix_discrete(ngoods, ncomponents, min=2, max=ndamagepatterns - 1),

        # Durations
        # reassembly duration of component k
        rd=reassembly_duration,
        # repair duration of component k with damage pattern s
        d=repair_duration,
        # order duration of component k with damage pattern s
        bd=random_values_matrix_row_ascending_discrete(ncomponents, ndamagepatterns, min=1, max=4),

        # Costs
        # housing cost of component k in damage pattern state s
        hc=[random_values_descending(ndamagepatterns, 0.0001, 2.0) for k in range(ncomponents)],
        # cost of delay per delayed period of good i
        c=random_values(ngoods, min=1, max=20),
        # order cost of component k with damage pattern s
        bc=random_values_matrix_row_ascending(ncomponents, ndamagepatterns, min=4.0, max=16.0),

        # repair capacity for component k
        rc=random_values_discrete(ncomponents, min=1, max=1),

        # due date of good i
        due=random_values_discrete(ngoods, min=0, max=4 * ncomponents)
    )


if __name__ == '__main__':
    import json

    inst = generate_instance(1, 2, 3, 3)
    print(json.dumps(inst, indent=True, sort_keys=True))
