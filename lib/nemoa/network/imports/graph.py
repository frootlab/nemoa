# -*- coding: utf-8 -*-

__author__ = 'Patrick Michl'
__email__ = 'frootlab@gmail.com'
__license__ = 'GPLv3'

import networkx

def filetypes():
    """Get supported graph description filetypes for network import."""

    d = {
        'gml': 'Graph Modelling Language',
        'graphml': 'Graph Markup Language',
        'xml': 'Graph Markup Language',
        'dot': 'GraphViz DOT'
    }

    return d

def load(path, **kwds):
    """Import network from graph description file."""
    from nemoa.core import npath

    # extract filetype from path
    filetype = npath.fileext(path).lower()

    # test if filetype is supported
    if filetype not in filetypes():
        raise ValueError(f"filetype '{filetype}' is not supported")

    if filetype == 'gml': return Gml(**kwds).load(path)
    if filetype in ['graphml', 'xml']: return Graphml(**kwds).load(path)
    if filetype == 'dot': return Dot(**kwds).load(path)

    return False

def _graph_decode(G):
    """ """
    from nemoa.core import nbytes

    # no encoding
    if not G.graph.get('coding', None) or G.graph['coding'].lower() == 'none':
        return G

    # base64 encoding
    if G.graph['coding'] == 'base64':
        G.graph['params'] = nbytes.unpack(G.graph['params'], encoding='base64')

        for node in G.nodes():
            G.node[node]['params'] = nbytes.unpack(
                G.node[node]['params'], encoding='base64')

        for edge in G.edges():
            G.edges[edge]['params'] = nbytes.unpack(
                G.edges[edge]['params'], encoding='base64')

        G.graph['coding'] == 'none'

        return graph

    raise ValueError(f"unsupported coding '{coding}'")

def _graph_to_dict(G):
    """ """

    d = {
        'graph': G.graph,
        'nodes': G.nodes(data = True),
        'edges': networkx.to_dict_of_dicts(G)
    }

    return d

class Graphml:
    """Import network from GraphML file."""

    settings = None
    default = {}

    def __init__(self, **kwds):
        """ """

        from nemoa.core import ndict

        self.settings = ndict.merge(kwds, self.default)

    def load(self, path):
        """ """

        from nemoa.core import ndict

        G = networkx.read_graphml(path)
        d = ndict.strkeys(_graph_to_dict(_graph_decode(G)))

        return {'config': d['graph']['params'], 'graph': d }

class Gml:
    """Import network from GML file."""

    settings = None
    default = {}

    def __init__(self, **kwds):
        """ """

        from nemoa.core import ndict

        self.settings = ndict.merge(kwds, self.default)

    def load(self, path):
        """ """

        from nemoa.core import ndict

        G = networkx.read_gml(path, relabel = True)
        d = ndict.strkeys(_graph_to_dict(_graph_decode(G)))

        return {'config': d['graph']['params'], 'graph': d }
