#!/usr/bin/env python
# -*- coding: utf-8 -*-

import nemoa, nemoa.plot.base, numpy, networkx, matplotlib
import matplotlib.pyplot
import matplotlib.ticker as ticker
from matplotlib.patches import FancyArrowPatch, Circle

class structure(nemoa.plot.base.plot):

    @staticmethod
    def _default():
        return {
            'output': 'file',
            'fileformat': 'pdf',
            'dpi': 300,
            'showTitle': True,
            'title': None,
            'backgroundColor': 'none',
            'graphCaption': True,
            'nodeCaption': 'accuracy',
            'nodeSort': 'weight',
            'edges': 'interaction',
            'edgeCaption': False,
            'edgeThreshold': 0.1,
            'edgeContrastBoost': 1.0,
            'edgeZoom': 1.0
        }

    def _create(self, model):

        # create figure and axis objects
        fig = matplotlib.pyplot.figure()
        fig.patch.set_facecolor(self.settings['backgroundColor'])
        ax  = fig.add_subplot(111)
        ax.axis('off')
        ax.autoscale()

        # use captions
        if self.settings['nodeCaption']:

            # get and check node caption relation
            method = self.settings['nodeCaption']
            fPath  = ('system', 'units', method)
            fAbout = model.about(*(fPath + ('name', )))

            if hasattr(fAbout, 'title'):
                fName = model.about(*(fPath + ('name', ))).title()
                fFormat = model.about(*(fPath + ('format', )))
                nCaption = model.eval(*fPath)
                caption  = 'Average ' + fName + ': $\mathrm{%.1f' \
                    % (100 * float(sum([nCaption[u] \
                    for u in nCaption.keys()])) / len(nCaption)) + '\%}$'
            else:
                self.settings['nodeCaption'] = None
                caption = None

        # get unit labels
        units = model.units()
        xLen = max([len(u) for u in units])
        yLen = len(units)

        # calculate sizes
        zoom  = 1.0
        scale = min(250.0 / xLen, 150.0 / yLen, 30.0)
        graphNodeSize = scale ** 2
        graphFontSize = 0.4 * scale
        graphCaptionFactor = 0.5 + 0.003 * scale
        graphLineWidth = 0.3

        # sort units (optional)
        if isinstance(self.settings['nodeSort'], str):
            sortUnits = list(units)
            sortParam = self.settings['nodeSort']
            for gid, group in enumerate(sortUnits):
                if not gid: continue
                sort = []
                for uid, u in enumerate(group):
                    sort.append((numpy.sum([float(puid) \
                        * numpy.abs(model.link((pu, u))['params'][sortParam]) \
                        for puid, pu in enumerate(sortUnits[gid - 1])]), u))
                sortGroup = [pu[1] for pu in sorted(sort, key = lambda x: x[0])]
                sortUnits[gid] = sortGroup
            units = tuple(sortUnits)

        # calculate node positions for stacked graph layout
        pos = {}
        posCap = {}
        for gid, group in enumerate(units):
            for uid, unit in enumerate(group):
                x = (uid + 0.5) / len(group)
                y = 1.0 - gid / (yLen - 1.0)
                c = (1.0 - gid) * graphCaptionFactor + 0.5
                pos[unit] = (x, y)
                posCap[unit] = (x, c)

        # graph
        G = model.network.graph

        # draw labeled nodes
        for gid, group in enumerate(units):
            for uid, unit in enumerate(group):
                attr = model.unit(unit)
                type = attr['params']['type']
                typeid = attr['params']['type_id']
                isVisible = attr['params']['visible']
                labelStr = attr['label'] if isVisible else 'n%d' % (uid + 1)
                label = nemoa.common.strToUnitStr(labelStr)

                color = {
                    True: {
                        'bg':   (0.27, 0.51, 0.70, 1.0),
                        'font': (0.0, 0.0, 0.0, 1.0) },
                    False: {
                        'bg':   (0.8, 0.8, 0.8, 1.0),
                        'font': (0.0, 0.0, 0.0, 1.0) }
                }[isVisible]

                # draw node
                networkx.draw_networkx_nodes(
                    G, pos,
                    node_size  = graphNodeSize,
                    linewidths = graphLineWidth,
                    nodelist   = [unit],
                    node_shape = 'o',
                    node_color = color['bg'])

                # draw node label
                nodeFontSize = \
                    2.0 * graphFontSize / numpy.sqrt(max(len(unit) - 1, 1))
                networkx.draw_networkx_labels(
                    G, pos,
                    font_size = nodeFontSize,
                    labels = {unit: label},
                    font_weight = 'normal',
                    font_color = color['font'])

                # draw node caption
                if self.settings['nodeCaption'] and isVisible:
                    if not unit in nCaption: continue
                    networkx.draw_networkx_labels(
                        G, posCap, font_size = 0.75 * graphFontSize,
                        labels = {unit: ' $' + '%d' % (100 * nCaption[unit]) + '\%$'},
                        font_weight = 'normal')

        # draw labeled edges
        for (v, h) in G.edges():

            # get weight
            attr = model.system.getLink((v, h))
            if not attr: attr = model.system.getLink((h, v))
            if not attr: continue

            weight = attr[self.settings['edges']]

            # boost edge contrast
            if self.settings['edgeContrastBoost'] > 0.0:
                weight = nemoa.common.func.boost(weight,
                    factor = self.settings['edgeContrastBoost'])

            # check if weight satisfies threshold
            if not numpy.abs(weight) > self.settings['edgeThreshold']: continue

            # get edge color and line width (from weight)
            if self.settings['edges'] == 'adjacency':
                color = 'black'
                edgeLineWidth = graphLineWidth * self.settings['edgeZoom']
            else:
                color = 'green' if weight > 0.0 else 'red'
                edgeLineWidth = \
                    weight * graphLineWidth * self.settings['edgeZoom']

            # draw edges
            networkx.draw_networkx_edges(
                G, pos,
                width = edgeLineWidth,
                edgelist = [(v, h)],
                edge_color = color,
                arrows = False,
                alpha = 1.0)

            # draw edge labels
            if not self.settings['edgeCaption']: continue
            size = graphFontSize / 1.5
            label = ' $' + ('%.2g' % (numpy.abs(weight))) + '$'
            networkx.draw_networkx_edge_labels(
                G, pos,
                edge_labels = {(v, h): label},
                font_color = color,
                clip_on = False,
                font_size = size,
                font_weight = 'normal')

        # draw caption
        if self.settings['graphCaption']:
            if self.settings['nodeCaption']:

                # draw caption
                if caption == None:
                    if edges == 'weight':
                        label_text = r'$\mathbf{Network:}\,\mathrm{%s}$' % (model.network.graph)
                    elif edges == 'adjacency':
                        label_text = r'$\mathbf{Network:}\,\mathrm{%s}$' % (model.network.graph)
                    matplotlib.pyplot.figtext(.5, .11, label_text, fontsize = 9, ha = 'center')
                else:
                    matplotlib.pyplot.figtext(.5, .11, caption, fontsize = 9, ha = 'center')

        return True



class relation(nemoa.plot.base.plot):

    @staticmethod
    def _default(): return {
        'output': 'file',
        'fileformat': 'pdf',
        'dpi': 300,
        'backgroundColor': 'none',
        'graphCaption': True,
        'units': (None, None),
        'preprocessing': None,
        'statistics': 10000,
        'relation': 'correlation',
        'transform': '',
        'sign': 'correlation',
        'filter': None,
        'threshold': 2.0,
        'measure': 'error',
        'nodeCaption': 'accuracy',
        'layout': 'spring',
        'edgeZoom': 1.0 }

    def _create(self, model, **params):

        # get params
        params = self.settings['params'] \
            if 'params' in self.settings else {}

        # get default units and mapping
        mapping = model.system.getMapping()
        iUnits  = model.units(group = mapping[0])[0]
        oUnits  = model.units(group = mapping[-1])[0]

        # update unit information
        if not isinstance(self.settings['units'], tuple) \
            or not isinstance(self.settings['units'][0], list) \
            or not isinstance(self.settings['units'][1], list):
            self.settings['units'] = (iUnits, oUnits)

        # calculate relation for weights
        nemoa.log('calculate edge weights: ' + self.settings['relation'])
        R = model.eval('system', 'relations', self.settings['relation'],
            preprocessing = self.settings['preprocessing'],
            measure = self.settings['measure'],
            statistics = self.settings['statistics'],
            transform = self.settings['transform'])
        if not isinstance(R, dict): return nemoa.log('error',
            'could not create relation graph: invalid weight relation!')

        # calculate relation for filter and mask
        if self.settings['filter'] == None \
            or self.settings['filter'] == self.settings['relation']:
            # create filter mask by using threshold for 'sigma'
            F = {key: key[0].split(':')[1] != key[1].split(':')[1]
                and R[key] - R['mean'] > self.settings['threshold'] * R['cstd']
                or  R[key] + R['mean'] < -self.settings['threshold'] * R['cstd']
                for key in R.keys() if isinstance(key, tuple)}
        else:
            FR = model.eval('system', 'relations', self.settings['filter'],
                preprocessing = self.settings['preprocessing'],
                measure = self.settings['measure'],
                statistics = self.settings['statistics'])
            # create filter mask by using threshold for 'sigma'
            F = {key: key[0].split(':')[1] != key[1].split(':')[1]
                and FR[key] - FR['mean'] > settings['threshold'] * FR['cstd']
                or  FR[key] + FR['mean'] < -self.settings['threshold'] * FR['cstd']
                for key in R.keys() if isinstance(key, tuple)}
            # info
            numPass = sum([int(F[key]) for key in F.keys()])
            numRel  = len(F.keys())
            if not numFilter: return nemoa.log('warning',
                'no relation passed filter!')
            nemoa.log("%i relations passed filter (%.1f%%)" % \
                (numPass, 100.0 * float(numPass) / float(numRel)))
        if not isinstance(F, dict): return nemoa.log('error',
            'could not create relation graph: invalid filter relation!')

        # calculate weights from weight relation and filter mask
        Wmax = max(abs(R['max']), abs(R['min']))
        W = {key: nemoa.common.func.boost(abs(R[key]) / Wmax)
            for key in F.keys()}

        # calculate relation for colors
        if self.settings['sign'] == None \
            or self.settings['sign'] == self.settings['relation']:
            S = {key: 2.0 * (1.0 * (R[key] > 0.0) - 0.5) * int(F[key])
                for key in F.keys()}
        else:
            SR = model.eval('system', 'relations', self.settings['sign'],
                preprocessing = self.settings['preprocessing'],
                measure = self.settings['measure'],
                statistics = self.settings['statistics'])
            S = {key: 2.0 * (1.0 * (SR[key] > 0.0) - 0.5) * int(F[key])
                for key in F.keys()}
        if not isinstance(S, dict): return nemoa.log('error',
            'could not create relation graph: invalid sign relation!')

        # calculate values for node captions
        if self.settings['nodeCaption']:

            # get and check node caption relation
            method = self.settings['nodeCaption']
            fPath  = ('system', 'units', method)
            fAbout = model.about(*fPath)

            if isinstance(fAbout, dict) and 'name' in fAbout.keys():
                fName    = model.about(*(fPath + ('name', ))).title()
                fFormat  = model.about(*(fPath + ('format', )))
                nCaption = model.eval(*fPath)
                caption  = 'Average ' + fName + ': $\mathrm{%.1f' \
                    % (100.0 * float(sum([nCaption[u] \
                    for u in nCaption.keys()])) / len(nCaption)) + '\%}$'
            else:
                nCaption = None
                caption = None

        # get title of model
        #if self.settings['graphCaption']: self.settings['title'] = model.name()
        if self.settings['graphCaption']: self.settings['title'] = \
            nemoa.common.strSplitParams(self.settings['relation'])[0].title()

        #
        # CREATE GRAPH AND FIND DISCONNECTED SUBGRAPHS
        #

        # get input and output units
        units  = self.settings['units']
        iUnits = units[0]
        oUnits = units[1]

        # create list of edges
        edges = []
        for i in iUnits:
            for o in oUnits: edges.append((i, o))

        # create graph
        G = networkx.MultiDiGraph()

        # add edges and attributes to graph
        for edge in edges:
            if not F[edge]: continue
            color = {1: 'green', 0: 'black', -1: 'red'}[S[edge]]
            G.add_edge(*edge, color = color, weight = W[edge])

        # find disconnected subgraphs
        Gsub = networkx.connected_component_subgraphs(G.to_undirected())
        numSub = len(Gsub)
        if numSub > 1: nemoa.log("%i disconnected complexes found" % (numSub))

        for sub in range(numSub):
            for node in Gsub[sub].nodes():
                mNode = model.network.node(node)
                G.node[node]['label']   = nemoa.common.strToUnitStr(mNode['label'])
                G.node[node]['type']    = mNode['params']['type']
                G.node[node]['complex'] = sub
                G.node[node]['color']   = {
                    'i': 'lightgreen',
                    'o': 'lightblue'
                }[mNode['params']['type']]

        # create plot
        return self._plotGraph(graph = G, **self.settings)

    def _plotGraph(self, graph, file = None, **params):

        if not len(graph): return nemoa.log('error',
            'could not plot graph: no relation passed filter!')

        # create figure object
        fig = matplotlib.pyplot.figure()
        fig.patch.set_facecolor(self.settings['backgroundColor'])
        ax  = fig.add_subplot(111)
        ax.axis('off')
        #ax.autoscale(enable = False)
        matplotlib.pyplot.axes().set_aspect('equal', 'box')

        # calculate positions
        if params['layout'] == 'random':
            pos = networkx.random_layout(graph)
        elif params['layout'] == 'circular':
            pos = networkx.circular_layout(graph)
        elif params['layout'] == 'shell':
            pos = networkx.shell_layout(graph)
        elif params['layout'] == 'spring':
            pos = networkx.spring_layout(graph)
        elif params['layout'] == 'fruchterman_reingold':
            pos = networkx.fruchterman_reingold_layout(graph)
        elif params['layout'] == 'spectral':
            pos = networkx.spectral_layout(graph)
        else:
            # warning unknown layout -> using spring
            pos = networkx.spring_layout(graph)

        # colors
        colors = {
            'black': (0.0, 0.0, 0.0, 1.0),
            'white': (1.0, 1.0, 1.0, 1.0),
            'red':   (1.0, 0.0, 0.0, 1.0),
            'green': (0.0, 0.5, 0.0, 1.0),
            'blue':  (0.0, 0.0, 0.7, 1.0),
            'lightgreen': (0.600, 0.800, 0.196, 0.7),
            'lightblue':  (0.439, 0.502, 0.565, 0.7) }

        # calculate sizes of nodes, fonts and lines depending on graph size
        nSizeMax = 800.0                            # maximum node size
        nCount   = float(len(graph))                # number of nodes
        nSize    = max(nSizeMax, 1500.0 / nCount)   # node size
        nRadius  = numpy.sqrt(nSize) / 480.0        # node radius
        fSizeMax = 18.0                             # maximum font size
        fSize    = fSizeMax * numpy.sqrt(nSize / nSizeMax)
        eSizeMax = 2.0                              # maximum edge size
        eSize    = eSizeMax / nCount                # edge size
        eArrSize = 10.0                             # edge arrow size

        # draw nodes
        for node, attr in graph.nodes(data = True):
            label = attr['label']

            # calculate node fontsize depending on label
            clLabel = label.replace('{', '').replace('}', '')
            if '_' in clLabel: lenLabel = len('_'.split(clLabel)[0]) \
                + 0.5 * len('_'.split(clLabel)[0])
            else: lenLabel = len(clLabel)
            nodeFontSize = fSize / numpy.sqrt(lenLabel) * 0.9

            # set backcolor (depending on type) and facecolor
            backcolor = colors[attr['color']]
            facecolor = colors['black']

            # draw node
            networkx.draw_networkx_nodes(
                graph, pos,
                node_size  = nSize,
                linewidths = eSize,
                nodelist   = [node],
                node_shape = 'o',
                node_color = backcolor)

            # draw label
            networkx.draw_networkx_labels(
                graph, pos,
                font_size   = nodeFontSize,
                labels      = {node: label},
                font_color  = facecolor,
                font_weight = 'normal')

            # patch node for edges
            c = Circle(
                pos[node],
                radius = nRadius,
                alpha  = 0.0)

            ax.add_patch(c)
            graph.node[node]['patch'] = c

        # get weights maximum an minimum
        #maxWeight = 0.0
        #minWeight = 1.0
        #for (u, v, attr) in graph.edges(data = True):
        #    if attr['weight'] > maxWeight: maxWeight = attr['weight']
        #    if attr['weight'] < minWeight: minWeight = attr['weight']

        # draw edges using 'fancy arrows'
        seen = {}
        for (u, v, attr) in graph.edges(data = True):
            n1  = graph.node[u]['patch']
            n2  = graph.node[v]['patch']
            rad = 0.15
            linewidth = eSize * attr['weight'] * params['edgeZoom'] * 5.0
            linecolor = list(colors[attr['color']]) #2DO: create gradient colors
    ##        linecolor[3] = 2.0 ** attr['weight'] / 2.0
    ##        linecolor = tuple(linecolor)

            if (u, v) in seen:
                rad = seen.get((u, v))
                rad = (rad + float(numpy.sign(rad)) * 0.2) * -1.0

            arrow = matplotlib.patches.FancyArrowPatch(
                posA   = n1.center,
                posB   = n2.center,
                patchA = n1,
                patchB = n2,
                arrowstyle = '-|>',
                connectionstyle = 'arc3,rad=%s' % rad,
                mutation_scale  = eArrSize,
                linewidth = linewidth,
                color = linecolor
            )

            seen[(u, v)] = rad
            ax.add_patch(arrow)

        return True
