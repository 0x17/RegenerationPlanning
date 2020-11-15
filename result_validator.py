def validate_results(instance, res):
    fails = []

    def f(**d):
        fails.append(d)

    # repair of item must be *after* arrival from disassembly
    for (i, k, s), t in res['repair_starts'].items():
        if instance['eks'][i-1][k] != s:
            f(type='repair_var', text='Damage pattern does not match', item=(i, k), expected=instance['eks'][i-1][k], actual=s)
        if instance['ekt'][i-1][k] > t:
            f(type='repair_var', text='Repair of item started before disassembly arrival', item=(i, k), expected=instance['ekt'][i-1][k], actual=t)

    # provisioning of item must be *after* corresponding order or repair has arrived/finished
    for (isrc, idest, k), t in res['ready_times'].items():
        if instance['ekt'][isrc-1][k] > t:
            f(type='ready_var', text='Provision timed before disassembly arrival', item=(isrc, idest, k), expected=instance['ekt'][isrc-1][k], actual=t)
        for (i2, k2, s), t2 in res['repair_starts'].items():
            if i2 == isrc and k == k2 and t2 > t:
                f(type='ready_var', text='Provision time before repair has finished', item=(isrc, idest, k), expected=t, actual=t2)
        #for (k2, s), t2 in res['order_starts'].items():
        # order provision assignment not unique!

    # respect reassembly order when provisioning
    for (isrc, idest, k), t in res['ready_times'].items():
        for (isrc2, idest2, k2), t2 in res['ready_times'].items():
            if idest2 == idest and k == k2 - 1 and t < t2 + instance['rd'][k2]:
                f(type='reassembly_sequence', text='Reassembly order and or times not respected', items=((isrc, idest, k), (isrc2, idest2, k2)), expected=t2 + instance['rd'][k2], actual=t)

    # delay computation is correct?
    delays = [0]*instance['ngoods']
    for (isrc, idest, k), t in res['ready_times'].items():
        delays[idest-1] = max(delays[idest-1], max(0, t-instance['due'][idest-1]))

    for i in range(instance['ngoods']):
        if delays[i] != res['delays'][i]:
            f(type='delay_computation', text='Delay mismatch', good=i, expected=delays[i], actual=res['delays'][i])

    return fails
