import matplotlib.pyplot as plt


def print_results(instance, res_dict):
    def y_of_item(i, k):
        return 1 + i * instance['ncomponents'] + k

    items = [(i, k) for i in range(instance['ngoods']) for k in range(instance['ncomponents'])]
    arrival_points = [dict(x=instance["ekt"][i][k], y=y_of_item(i + 1, k)+0.5, label=f'a(i{i+1},k{k},s{instance["eks"][i][k]})') for i,k in items ]
    repair_points = [dict(x=t, y=y_of_item(i + 1, k), label=f'r(i{i},k{k},s{s})') for (i, k, s), t in res_dict['repair_starts'].items()]
    order_points = [dict(x=t, y=y_of_item(0, k), label=f'o(k{k},s{s})') for (k, s), t in res_dict['order_starts'].items()]
    ready_points = [dict(x=t, y=y_of_item(i + 1, k), label=f'p(i{i},i{istar},k{k})') for (i, istar, k), t in res_dict['ready_times'].items()]

    all_points = repair_points + order_points + ready_points + arrival_points
    xs, ys, labels = [p['x'] for p in all_points], [p['y'] for p in all_points], [p['label'] for p in all_points]

    plt.title('a=arrival, r=repair, o=order, p=provisioning')
    plt.scatter(xs, ys, color='#993399', marker='x')
    for i in range(len(labels)):
        yoffset = 0 if 'a' in labels[i] else (-5 if 'o' in labels[i] else 5)
        plt.annotate(labels[i], (xs[i], ys[i]), textcoords='offset points', xytext=(0, yoffset), ha='center', fontsize=3)

    #plt.show()
    plt.savefig('results/schedule.pdf')
