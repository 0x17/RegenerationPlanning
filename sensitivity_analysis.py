import sys

import generator
import model

import numpy as np

import copy

import matplotlib.pyplot as plt

import utils


def results_for_varying_parameter(base_instance, param_name, param_length, lb, ub, step, result_mapper=None):
    def res_for(v):
        instance = copy.deepcopy(base_instance)
        instance[param_name] = [v] * param_length
        return model.solve(instance, origin_restricted=False)

    xs = np.arange(lb, ub, step)
    results = [res_for(x) for x in xs]
    ys = [result_mapper(res) if result_mapper is not None else res['total_costs'] for res in results]
    return xs, ys

def plot_variations(base_instance, variation_options, plotting_options):
    colors = list('rgbcmyk')
    variation_options['base_instance'] = base_instance
    xs, ys = results_for_varying_parameter(**variation_options)
    plt.xlabel(plotting_options['xlabel'])
    plt.ylabel(plotting_options['ylabel'])
    for col_ix, caption in enumerate(plotting_options['captions']):
        plt.plot(xs, [y[col_ix] for y in ys], linestyle='--', marker='o', color=colors[col_ix], label=caption)
    plt.legend()
    plt.show()


def main(args):
    ngoods = 2
    instance = generator.generate_instance(23, ngoods, 4, 3, 120)
    #instance['due'] = [0]*ngoods

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
                                          captions=captions))


if __name__ == '__main__':
    main(sys.argv)
