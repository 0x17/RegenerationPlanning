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

        print(f'\n{caption}:{sep if sep == newline else " "}' +
              f'{sep.join("piece " + str(named(index_names, inc(k))) + (arrival_str(with_arrival, k) if with_arrival is not None else "") + " at period " + str(v) for k, v in res_dict[res_dict_key].items())}')

    print_result_line('Repairs', 'repair_starts', 'iks')
    print_result_line('Orders', 'order_starts', 'ks')
    print_result_line('Provisioning times', 'ready_times', 'ik', sep='\n', with_arrival=lambda i, k: (instance['eks'][i][k], instance['ekt'][i][k]))

    print('')

    for i in range(instance['ngoods']):
        print(f'Delay of good {i} is {res_dict["delays"][i]} time units')

    print('')

    for i in range(instance['ngoods']):
        for k in range(instance['ncomponents']):
            ekt, eks = instance['ekt'][i][k], instance['eks'][i][k]
            action = 'repair' if any(i == i2 and k == k2 for i2, k2, s in res_dict['repair_starts']) else 'order'
            action_start = res_dict['repair_starts'][(i, k, eks)] if action == 'repair' else 0
            provision_ready = res_dict['ready_times'][(i, k)]
            print(f'Item ({i},{k}) arrives at {ekt} with damage pattern {eks} and was provisioned using {action} starting at {action_start} with provisioning time at period {provision_ready}')

