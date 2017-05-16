# -*- coding: utf-8 -*-

__author__  = 'Patrick Michl'
__email__   = 'patrick.michl@gmail.com'
__license__ = 'GPLv3'

import nemoa
import numpy
import networkx
import os
import importlib
import matplotlib.pyplot

def filetypes():
    """Get supported image filetypes for network export."""
    return matplotlib.pyplot.gcf().canvas.get_supported_filetypes()

def show(network, plot = None, **kwargs):

    # get class for plotting from attribute 'plot'
    if not plot: plot = 'graph'
    class_name = plot.lower().title()
    module_name = save.__module__
    try:
        module = importlib.import_module(module_name)
        if not hasattr(module, class_name):raise ImportError()
    except ImportError:
        return nemoa.log('error', """could not plot graph '%s':
            plot type '%s' is not supported.""" % (network.name, plot))

    # create plot instance
    plot = getattr(module, class_name)(**kwargs)

    # create plot
    if plot.create(network):

        # output
        matplotlib.pyplot.show()

    # clear figures and release memory
    matplotlib.pyplot.clf()

    return True

def save(network, path = None, filetype = None, plot = None, **kwargs):

    # test if filetype is supported by matplotlib
    if not filetype in filetypes():
        return nemoa.log('error', """could not create plot:
            filetype '%s' is not supported by matplotlib.""" %
            (filetype))

    # get class for plotting from attribute 'plot'
    if not plot: plot = 'graph'
    class_name = plot.lower().title()
    module_name = save.__module__
    try:
        module = importlib.import_module(module_name)
        if not hasattr(module, class_name): raise ImportError()
    except ImportError:
        return nemoa.log('error', """could not plot network '%s':
            plot type '%s' is not supported.""" % (network.name, plot))

    # create plot instance
    plot = getattr(module, class_name)(**kwargs)

    # create plot
    if plot.create(network):

        # output
        matplotlib.pyplot.savefig(path, dpi = plot.settings['dpi'])

    # clear figures and release memory
    matplotlib.pyplot.clf()

    return path

class Graph(nemoa.common.classes.Plot):

    settings = None
    default = {
        'fileformat': 'pdf',
        'figure_size': (10., 6.),
        'dpi': None,
        'bg_color': 'none',
        'usetex': False,
        'show_title': True,
        'title': None,
        'title_fontsize': 14.0,
        'show_legend': True,
        'legend_fontsize': 9.0,
        'graph_layout': 'layer',
        'node_caption': 'accuracy',
        'node_groupby': None,
        'node_color': True,
        'edge_color': False,
        'edge_caption': None,
        'edge_weight': 'intensity',
        'edge_threshold': 0.,
        'edge_transform': 'softstep',
        'edge_sign_normalize': True }

    def create(self, network):

        import nemoa.common.graph as nmgraph
        import nemoa.common.plot  as nmplot
        import nemoa.common.math  as nmmath

        # copy graph from system structure of model
        graph = network.get('graph', type = 'graph')

        # copy graph attributes from graph 'params'
        params = graph.graph.get('params', {})
        if 'directed' in params:
            graph.graph['directed'] = params['directed']

        # create edge attribute 'weight'
        edgeattr = self.settings.get('edge_weight', None)
        normalize = self.settings.get('edge_normalize', None)
        threshold = self.settings.get('edge_threshold', None)
        transform = self.settings.get('edge_transform', None)

        # calculate mean weight for normalization (optional)
        if bool(normalize):
            absmean = numpy.absolute(numpy.mean(
                [data['params'].get(edgeattr, 0.) \
                for (u, v, data) in graph.edges(data = True)]))
            if absmean == 0.: normalize = None

        for (u, v, data) in graph.edges(data = True):
            weight = data['params'].get(edgeattr, None)
            if weight == None:
                if 'weight' in data: data.pop('weight')
                continue

            # threshold weights (optional)
            if bool(threshold) and threshold > numpy.absolute(weight):
                graph.remove_edge(u, v)
                continue

            # create edge attribute 'color' (optional)
            if self.settings.get('edge_color', False):
                if weight > 0: graph.edge[u][v]['color'] = \
                    self.settings.get('edge_poscolor', 'green')
                else: graph.edge[u][v]['color'] = \
                    self.settings.get('edge_negcolor', 'red')

            # create edge attribute 'caption' (optional)
            if self.settings['edge_caption']:
                caption = ' $' + ('%.2g' % (weight)) + '$'
                graph.edge[u][v]['caption'] = caption

            # normalize weights (optional)
            if bool(normalize): weight /= absmean

            # transform weights (optional)
            if transform == 'softstep':
                weight = nmmath.softstep(weight)

            graph.edge[u][v]['weight'] = weight

        # normalize signs of weights (optional)
        if self.settings['edge_sign_normalize']:
            number_of_layers = len(graph.graph['params']['layer'])
            if number_of_layers % 2 == 1:
                sign_sum = numpy.sum(
                    [numpy.sign(graph.edge[u][v].get('weight', 0))
                    for (u, v) in graph.edges()])
                if sign_sum < 0:
                    for (u, v) in graph.edges():
                        if 'weight' in graph.edge[u][v]:
                            graph.edge[u][v]['weight'] *= -1

        nodes = {n: data for n, data in graph.nodes(data = True)}

        # copy node attributes 'label' and 'visible' from unit params
        for node, data in graph.nodes(data = True):
            params = data.get('params', {})
            data.update({
                'label': params.get('label', str(node)),
                'visible': params.get('visible', True),
                'layer': params.get('layer', None),
                'layer_id': params.get('layer_id', None),
                'layer_sub_id': params.get('layer_sub_id', None)})

        # update node attribute 'group'
        groupby = self.settings.get('node_groupby', None)
        if not groupby == None:
            for node, data in graph.nodes(data = True):
                node_params = data.get('params', {})
                data['group'] = node_params.get(groupby)
        else:
            is_layer = nmgraph.is_layered(graph)
            is_directed = nmgraph.is_directed(graph)
            if is_layer and not is_directed:
                for node, data in graph.nodes(data = True):
                    gid = int(data.get('visible', True))
                    data['group'] = {0: 'latent', 1: 'observable'}[gid]
            elif is_layer and is_directed:
                layers = nmgraph.get_layers(graph)
                ilayer, olayer = layers[0], layers[-1]
                for node, data in graph.nodes(data = True):
                    gid = int(node in ilayer) \
                        + 2 * int(node in olayer)
                    data['group'] = {0: 'latent', 1: 'source',
                        2: 'target', 3: 'transit'}[gid]
            else:
                for node, data in graph.nodes(data = True):
                    gid = int(data.get('visible', True))
                    data['group'] = {0: 'latent', 1: 'observable'}[gid]

        # update node attributes for layout
        groups = nmgraph.get_groups(graph, attribute = 'group')
        for group in sorted(groups.keys()):
            if group == None: continue
            layout = nmgraph.get_node_layout(group)
            group_label = layout.get('label', {
                True: str(groupby),
                False: 'not ' + str(groupby)}[group] \
                if isinstance(group, bool) else str(group).title())
            for node in groups.get(group, []):
                node_params = nodes[node].get('params')
                graph.node[node].update({
                    'label': node_params.get('label', str(node)),
                    'group': group_label })
                graph.node[node].update(layout)

        # prepare parameters
        if self.settings.get('title') == None:
            self.settings['title'] = network.fullname

        # plot graph
        return nmplot.graph(graph, **self.settings)
