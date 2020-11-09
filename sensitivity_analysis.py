import copy
import json
import sys
import os

import matplotlib.pyplot as plt
import numpy as np

import generator
import model


def results_for_varying_parameter(base_instance, param_name, param_length, lb, ub, step, result_mapper=None):
    def res_for(v):
        instance = copy.deepcopy(base_instance)
        instance[param_name] = [v] * param_length
        print(f'Running solve with gurobi for param with name {param_name} and value = {v}')
        return model.solve(instance, origin_restricted=False)

    xs = list(np.arange(lb, ub, step))
    results = [res_for(x) for x in xs]
    ys = [result_mapper(res) if result_mapper is not None else res['total_costs'] for res in results]
    return xs, ys


def plot_variations(base_instance, variation_options, plotting_options, force_recompute=False):
    if not os.path.isdir('results'):
        os.mkdir('results')
    colors = list('rgbcmyk')
    cache_fn = f'results/computation_results_{variation_options["param_name"]}_{plotting_options["ylabel"]}.json'

    variation_options['base_instance'] = base_instance

    if os.path.isfile(cache_fn) and not force_recompute:
        with open(cache_fn, 'r') as fp:
            obj = json.load(fp)
            xs, ys = obj['xs'], obj['ys']
    else:
        xs, ys = results_for_varying_parameter(**variation_options)
        with open(cache_fn, 'w') as fp:
            json.dump(dict(xs=xs, ys=ys), fp)

    plt.xlabel(plotting_options['xlabel'])
    plt.ylabel(plotting_options['ylabel'])
    for col_ix, caption in enumerate(plotting_options['captions']):
        plt.plot(xs, [y[col_ix] for y in ys], linestyle='--', marker='x', markersize=4, color=colors[col_ix], label=caption)
    plt.legend()
    #plt.show()
    format = 'pdf'
    plt.savefig(cache_fn.replace('.json', f'.{format}'), format=format)
    plt.close()


def experiment_delay_costs_first(instance, ngoods):
    prefixes = ['delay', 'order', 'housing']
    captions = [f'{prefix}_costs' for prefix in prefixes]

    def res_mapper(result):
        return tuple(result[caption] for caption in captions)

    plot_variations(instance,
                    variation_options=dict(param_name='c',
                                           param_length=ngoods,
                                           lb=0, ub=10, step=0.25,
                                           result_mapper=res_mapper),
                    plotting_options=dict(xlabel='Delay cost coefficient',
                                          ylabel='Costs',
                                          captions=[f'{prefix} costs' for prefix in prefixes]),
                    force_recompute=False)


def experiment_delay_costs_second(instance, ngoods):
    def res_mapper(result):
        return (len(result['repair_starts'])), (len(result['order_starts']))

    plot_variations(instance,
                    variation_options=dict(param_name='c',
                                           param_length=ngoods,
                                           lb=0, ub=10, step=0.25,
                                           result_mapper=res_mapper),
                    plotting_options=dict(xlabel='Delay cost coefficient',
                                          ylabel='Count',
                                          captions=['number of repairs', 'number of orders']),
                    force_recompute=False)


def main(args):
    ngoods = 2
    instance = generator.generate_instance(23, ngoods, 4, 3, 120)
    # instance['due'] = [0]*ngoods
    experiment_delay_costs_first(instance, ngoods)
    experiment_delay_costs_second(instance, ngoods)


if __name__ == '__main__':
    main(sys.argv)
