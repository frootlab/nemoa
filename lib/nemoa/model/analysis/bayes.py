# -*- coding: utf-8 -*-
"""Bayesian Network (BN) analysis.

This module includes various functions for the analysis of directed graphical
models with acyclic graphs, generally known as Bayesian networks. These models
e.g. include linear models (LM) and feedforward neural networks (ANN) like
Deep belief networks (DBN).

The supported categories of analysis functions are:

    (1) "Sampler": Matrix valued statistical inference functions
        Return numpy ndarray of shape (d, t), where d is the size of the sample
        and t the number of target observables within the model.
    (2) "Response statistics": Vectorial statistical inference functions,
        regarding the response variables
        Return numpy array of shape (1, t), where t is the number of
        target observables within the model.
    (3) "Objective functions": Scalar statistical inference functions, that can
        be used for the determination of local optima.
        Return scalar value
    (4) "Association measures": Matrix valued statistical association measures
        Return numpy ndarray of shape (s, t), where s is the number of
        source observables and t the number of target observables within the
        model.

"""

__author__  = 'Patrick Michl'
__email__   = 'patrick.michl@gmail.com'
__license__ = 'GPLv3'

import nemoa
import numpy

#
# (1) Sampler for Bayesian Networks
#

from nemoa.common.decorators import sampler

@sampler(
    name    = 'forward',
    title   = 'Forward Sampling',
    classes = ['LM', 'ANN']
)
def get_forward_sample(model, *args, **kwargs):
    """Forward sampled values of target observables.

    Args:
        data: numpy ndarray containing data of the source observables within the
            first layer in mapping

    Kwargs:
        mapping: n-tuple of strings that consecutively identify the layers
            within the mapping from the source observable layer (first argument)
            to the target observable layer (last argument).
        block: list of strings containing labels of source observables, which
            are 'ignored' by replacing their values by their means and therefore
            do not contribute to the variance of the sampled target values.
        mode (int, optional): Sampling mode:
            0: Prediction of target observables:
               Returns consecutively forward sampled exact relizations of
               target observables, as required for predictions
            1: Monte Carlo sampling of target observables:
               Returns consecutively forward sampled random realizations of
               target observables, as required for probabilistic learning
            2: Mean Field propagation of target observables:
               Returns consecutively forward sampled expectations of
               target observables, as required for mean field propagation
        expect_last (bool, optional): return Mean Field propagation for the last
            sampling step instead of relizations to reduce noise in
            probabilistic learning.

    Returns:
        Numpy ndarray of shape (d, t) where d is the size of the sample
        and t the number of target observables within the model.

    """

    mode = kwargs.pop('mode', 0)

    if mode == 0:
        return model.system._get_unitvalues(*args, **kwargs)
    elif mode == 1:
        return model.system._get_unitsamples(*args, **kwargs)
    elif mode == 2:
        return model.system._get_unitexpect(*args, **kwargs)

    return None

@sampler(
    name    = 'ancestral_residual',
    title   = 'Ancestral Residual Sampler',
    classes = ['LM', 'ANN']
)
def get_forward_residuals(model, data, mapping = None, block = None):
    """Reconstruction residuals of target observables.

    Args:
        data: 2-tuple of numpy arrays containing source and target
            data corresponding to the first and the last argument
            of the mapping

    Kwargs:
        mapping: n-tuple of strings containing the mapping
            from source unit layer (first argument of tuple)
            to target unit layer (last argument of tuple)
        block: list of strings containing labels of source units
            that are 'blocked' by setting their values to the means
            of their values.

    Returns:
        Numpy ndarray of shape (d, t).

    """

    d_src, d_tgt = data

    # set mapping: src layer to tgt layer (if not set)
    if mapping == None: mapping = model.system._get_mapping()

    # set unit values to mean (optional)
    if isinstance(block, list):
        d_src = numpy.copy(d_src)
        for i in block: d_src[:, i] = numpy.mean(d_src[:, i])

    # calculate prediction for response variables
    m_out = get_forward_sample(d_src, mapping)

    # calculate residuals
    return d_tgt - m_out

#
# (2) Sample statistics for Bayesian Networks
#

from nemoa.common.decorators import statistics

@nemoa.common.decorators.inference(
    name    = 'errorvector',
    title   = 'Reconstruction Error',
    classes = ['LM', 'ANN'],
    plot    = 'bar'
)
def get_error_vector(model, data, norm = 'MSE', **kwargs):
    """Reconstruction error of regressands.

    The reconstruction error is defined by:
        error := norm(residuals)

    Args:
        data: 2-tuple of numpy arrays containing source and target
            data corresponding to the first and the last layer in
            the mapping
        mapping: n-tuple of strings containing the mapping
            from source unit layer (first argument of tuple)
            to target unit layer (last argument of tuple)
        block: list of strings containing labels of source units
            that are blocked by setting the values to their means
        norm: used norm to calculate data reconstuction error from
            residuals. see nemoa.common.ndarray.meannorm for a list
            of provided norms

    """

    from nemoa.common.ndarray import meannorm

    res = get_residuals(data, **kwargs)
    error = meannorm(res, norm = norm)

    return error

@nemoa.common.decorators.algorithm(
    name     = 'accuracyvector',
    category = 'units',
    args     = 'all',
    retfmt   = 'scalar',
    formater = lambda val: '%.3f' % (val),
    plot     = 'diagram'
)
def get_accuracy_vector(model, data, norm = 'MSE', **kwargs):
    """Unit reconstruction accuracy.

    The unit reconstruction accuracy is defined by:
        accuracy := 1 - norm(residuals) / norm(data).

    Args:
        data: 2-tuple of numpy arrays containing source and target
            data corresponding to the first and the last layer
            in the mapping
        mapping: n-tuple of strings containing the mapping
            from source unit layer (first argument of tuple)
            to target unit layer (last argument of tuple)
        block: list of strings containing labels of source units
            that are blocked by setting the values to their means
        norm: used norm to calculate accuracy
            see nemoa.common.ndarray.meannorm for a list of provided
            norms

    """

    from nemoa.common.ndarray import meannorm

    res = get_residuals(data, **kwargs)
    normres = meannorm(res, norm = norm)
    normdat = meannorm(data[1], norm = norm)

    return 1. - normres / normdat

@nemoa.common.decorators.algorithm(
    name     = 'precisionvector',
    category = 'units',
    args     = 'all',
    retfmt   = 'scalar',
    formater = lambda val: '%.3f' % (val),
    plot     = 'diagram'
)
def get_precision_vector(model, data, norm = 'SD', **kwargs):
    """Unit reconstruction precision.

    The unit reconstruction precision is defined by:
        precision := 1 - dev(residuals) / dev(data).

    Args:
        data: 2-tuple of numpy arrays containing source and target
            data corresponding to the first and the last layer
            in the mapping
        mapping: n-tuple of strings containing the mapping
            from source unit layer (first argument of tuple)
            to target unit layer (last argument of tuple)
        block: list of strings containing labels of source units
            that are blocked by setting the values to their means
        norm: used norm to calculate deviation for precision
            see nemoa.common.ndarray.devnorm for a list of provided
            norms

    """

    from nemoa.common.ndarray import devnorm

    res = get_residuals(data, **kwargs)
    devres = devnorm(res, norm = norm)
    devdat = devnorm(data[1], norm = norm)

    return 1. - devres / devdat

@nemoa.common.decorators.inference(
    name     = 'mean',
    title    = 'Reconstructed Mean Values',
    category = 'units',
    plot     = 'bar'
)
def get_mean_vector(model, data, mapping = None, block = None):
    """Predicted mean values of response variables.

    Args:
        data: numpy array containing source data corresponding to
            the source unit layer (first argument of the mapping)
        mapping: n-tuple of strings containing the mapping
            from source unit layer (first argument of tuple)
            to target unit layer (last argument of tuple)
        block: list of strings containing labels of source units
            that are 'blocked' by setting their values to the means
            of their values.

    Returns:
        Numpy array of shape (targets).

    """

    if mapping == None: mapping = model.system._get_mapping()
    if block == None:
        model_out = unit_expect(data[0], mapping)
    else:
        data_in_copy = numpy.copy(data)
        for i in block:
            data_in_copy[:,i] = numpy.mean(data_in_copy[:,i])
        model_out = unit_expect(data_in_copy, mapping)

    return model_out.mean(axis = 0)

@nemoa.common.decorators.algorithm(
    name     = 'variance',
    category = 'units',
    args     = 'input',
    retfmt   = 'scalar',
    formater = lambda val: '%.3f' % (val),
    plot     = 'diagram'
)
def get_variance_vector(model, data, mapping = None, block = None):
    """Return variance of reconstructed unit values.

    Args:
        data: numpy array containing source data corresponding to
            the first layer in the mapping
        mapping: n-tuple of strings containing the mapping
            from source unit layer (first argument of tuple)
            to target unit layer (last argument of tuple)
        block: list of strings containing labels of source units
            that are blocked by setting the values to their means
    """

    if mapping == None: mapping = model.system._get_mapping()
    if block == None:
        model_out = get_sample_ancestral(data, mapping)
    else:
        data_in_copy = numpy.copy(data)
        for i in block:
            data_in_copy[:,i] = numpy.mean(data_in_copy[:,i])
        model_out = get_sample_ancestral(data_in_copy, mapping)

    return model_out.var(axis = 0)

#
# (3) Objective Functions for Bayesian Networks
#

from nemoa.common.decorators import objective

@objective(
    name    = 'error',
    title   = 'Mean Reconstruction Error',
    classes = ['LM', 'ANN'],
    optimum = 'min'
)
def get_error(model, *args, **kwargs):
    """Return mean error of regressands."""
    return numpy.mean(get_error_vector(model, *args, **kwargs))

@objective(
    name    = 'accuracy',
    title   = 'Mean Reconstruction Accuracy',
    classes = ['LM', 'ANN'],
    optimum = 'max'
)
def get_accuracy(model, *args, **kwargs):
    """Return mean accuracy of regressands."""
    return numpy.mean(get_accuracy_vector(model, *args, **kwargs))

@objective(
    name    = 'precision',
    title   = 'Mean Reconstruction Pricision',
    classes = ['LM', 'ANN'],
    optimum = 'max'
)
def get_precision(model, *args, **kwargs):
    """Return mean precision of regressands."""
    return numpy.mean(get_precision_vector(model, *args, **kwargs))

#
# (4) Association Measures for Bayesian Networks
#

from nemoa.common.decorators import association

@nemoa.common.decorators.algorithm(
    name     = 'correlation',
    category = 'relation',
    directed = False,
    signed   = True,
    normal   = True,
    args     = 'all',
    retfmt   = 'scalar',
    plot     = 'heatmap',
    formater = lambda val: '%.3f' % (val)
)
def correlation(model, data, mapping = None, **kwargs):
    """Data correlation between source and target units.

    Undirected data based relation describing the 'linearity'
    between variables (units).

    Args:
        data: 2-tuple with numpy arrays: input data and output data
        mapping: tuple of strings containing the mapping
            from input layer (first argument of tuple)
            to output layer (last argument of tuple)

    Returns:
        Numpy array of shape (source, target) containing pairwise
        correlation between source and target units.

    """

    # 2do: allow correlation between hidden units

    # calculate symmetric correlation matrix
    corr = numpy.corrcoef(numpy.hstack(data).T)

    # create asymmetric output matrix
    mapping = model.system._get_mapping()
    srcunits = model.system._get_units(layer = mapping[0])
    tgtunits = model.system._get_units(layer = mapping[-1])
    units = srcunits + tgtunits
    relation = numpy.zeros(shape = (len(srcunits), len(tgtunits)))
    for i, u1 in enumerate(srcunits):
        k = units.index(u1)
        for j, u2 in enumerate(tgtunits):
            l = units.index(u2)
            relation[i, j] = corr[k, l]

    return relation


@nemoa.common.decorators.algorithm(
    name     = 'knockout',
    category = 'relation',
    directed = True,
    signed   = True,
    normal   = False,
    args     = 'all',
    retfmt   = 'scalar',
    plot     = 'heatmap',
    formater = lambda val: '%.3f' % (val)
)
def knockout(model, data, mapping = None, **kwargs):
    """Knockout effect from source to target units.

    Directed data manipulation based relation describing the
    increase of the data reconstruction error of a given output
    unit, when setting the values of a given input unit to its mean
    value.

    Knockout single source units and measure effects on target units
    respective to given data

    Args:
        data: 2-tuple with numpy arrays: input data and output data
        mapping: tuple of strings containing the mapping
            from input layer (first argument of tuple)
            to output layer (last argument of tuple)

    Returns:
        Numpy array of shape (source, target) containing pairwise
        knockout effects from source to target units.

    """

    if not mapping: mapping = model.system._get_mapping()
    in_labels = model.system._get_units(layer = mapping[0])
    out_labels = model.system._get_units(layer = mapping[-1])

    # prepare knockout matrix
    R = numpy.zeros((len(in_labels), len(out_labels)))

    # calculate unit values without knockout
    if not 'measure' in kwargs: measure = 'error'
    else: measure = kwargs['measure']
    default = model.evaluate(algorithm = measure,
        category = 'units', mapping = mapping)

    if not default: return None

    # calculate unit values with knockout
    for in_id, in_unit in enumerate(in_labels):

        # modify unit and calculate unit values
        knockout = model.evaluate(algorithm = measure,
            category = 'units', mapping = mapping, block = [in_id])

        # store difference in knockout matrix
        for out_id, out_unit in enumerate(out_labels):
            R[in_id, out_id] = \
                knockout[out_unit] - default[out_unit]

    return R

@nemoa.common.decorators.algorithm(
    name     = 'connectionweight',
    category = 'relation',
    directed = True,
    signed   = True,
    normal   = False,
    args     = 'all',
    retfmt   = 'scalar',
    plot     = 'heatmap',
    formater = lambda val: '%.3f' % (val)
)
def connectionweight(model, data, mapping = None, **kwargs):
    """Weight sum product from source to target units.

    Directed graph based relation describing the matrix product from
    source to target units (variables) given by mapping.

    Args:
        data: 2-tuple with numpy arrays: input data and output data
        mapping: tuple of strings containing the mapping
            from input layer (first argument of tuple)
            to output layer (last argument of tuple)

    Returns:
        Numpy array of shape (source, target) containing pairwise
        weight sum products from source to target units.

    """

    if not mapping: mapping = model.system._get_mapping()

    # calculate product of weight matrices
    for i in range(1, len(mapping))[::-1]:
        weights = model.system._units[mapping[i - 1]].links(
            {'layer': mapping[i]})['W']
        if i == len(mapping) - 1: wsp = weights.copy()
        else: wsp = numpy.dot(wsp.copy(), weights)

    return wsp.T

@nemoa.common.decorators.algorithm(
    name     = 'coinduction',
    category = 'relation',
    directed = True,
    signed   = False,
    normal   = False,
    args     = 'all',
    retfmt   = 'scalar',
    plot     = 'heatmap',
    formater = lambda val: '%.3f' % (val)
)
def coinduction(model, data, *args, **kwargs):
    """Coinduced deviation from source to target units."""

    # 2do: Open Problem:
    #       Normalization of CoInduction
    # Ideas:
    #       - Combine CoInduction with common distribution
    #         of induced values
    #       - Take a closer look to extreme Values

    # 2do: Proove:
    # CoInduction <=> Common distribution in 'deep' latent variables

    # algorithmic default parameters
    gauge = 0.1 # setting gauge lower than induction default
                # to increase sensitivity

    mapping = model.system._get_mapping()
    srcunits = model.system._get_units(layer = mapping[0])
    tgtunits = model.system._get_units(layer = mapping[-1])

    # prepare cooperation matrix
    coop = numpy.zeros((len(srcunits), len(srcunits)))

    # create keawords for induction measurement

    if not 'gauge' in kwargs: kwargs['gauge'] = gauge

    # calculate induction without manipulation
    ind = induction(data, *args, **kwargs)
    norm = numpy.sqrt((ind ** 2).sum(axis = 1))

    # calculate induction with manipulation
    for sid, sunit in enumerate(srcunits):

        # manipulate source unit values and calculate induction
        datamp = [numpy.copy(data[0]), data[1]]
        datamp[0][:, sid] = 10.0
        indmp = induction(datamp, *args, **kwargs)

        print(('manipulation of', sunit))
        vals = [-2., -1., -0.5, 0., 0.5, 1., 2.]
        maniparr = numpy.zeros(shape = (len(vals), data[0].shape[1]))
        for vid, val in enumerate(vals):
            datamod = [numpy.copy(data[0]), data[1]]
            datamod[0][:, sid] = val #+ datamod[0][:, sid].mean()
            indmod = induction(datamod, *args, **kwargs)
            maniparr[vid, :] = numpy.sqrt(((indmod - ind) ** 2).sum(axis = 1))
        manipvar = maniparr.var(axis = 0)
        #manipvar /= numpy.amax(manipvar)
        manipnorm = numpy.amax(manipvar)
        # 2do
        print((manipvar * 1000.))
        print((manipvar / manipnorm))

        coop[:,sid] = \
            numpy.sqrt(((indmp - ind) ** 2).sum(axis = 1))

    return coop

@nemoa.common.decorators.algorithm(
    name     = 'induction',
    category = 'relation',
    directed = True,
    signed   = False,
    normal   = False,
    args     = 'all',
    retfmt   = 'scalar',
    plot     = 'heatmap',
    formater = lambda val: '%.3f' % (val)
)
def induction(model, data, mapping = None, points = 10,
    amplify = 1., gauge = 0.25, contrast = 20.0, **kwargs):
    """Induced deviation from source to target units.

    Directed data manipulation based relation describing the induced
    deviation of reconstructed values of a given output unit, when
    manipulating the values of a given input unit.

    For each sample and for each source the induced deviation on
    target units is calculated by respectively fixing one sample,
    modifying the value for one source unit (n uniformly taken
    points from it's own distribution) and measuring the deviation
    of the expected valueas of each target unit. Then calculate the
    mean of deviations over a given percentage of the strongest
    induced deviations.

    Args:
        data: 2-tuple with numpy arrays: input data and output data
        mapping: tuple of strings containing the mapping
            from source layer (first argument of tuple)
            to target layer (last argument of tuple)
        points: number of points to extrapolate induction
        amplify: amplification of the modified source values
        gauge: cutoff for strongest induced deviations
        contrast:

    Returns:
        Numpy array of shape (source, target) containing pairwise
        induced deviation from source to target units.

    """

    if not mapping: mapping = model.system._get_mapping()
    iunits = model.system._get_units(layer = mapping[0])
    ounits = model.system._get_units(layer = mapping[-1])
    R = numpy.zeros((len(iunits), len(ounits)))

    # get indices of representatives
    rids = [int((i + 0.5) * int(float(data[0].shape[0])
        / points)) for i in range(points)]

    for iid, iunit in enumerate(iunits):
        icurve = amplify * numpy.take(
            numpy.sort(data[0][:, iid]), rids)

        # create output matrix for each output
        C = {ounit: numpy.zeros((data[0].shape[0], points)) \
            for ounit in ounits}
        for pid in range(points):
            idata  = data[0].copy()
            idata[:, iid] = icurve[pid]
            oexpect = unitexpect(model, idata, mapping = mapping)
            for tid, ounit in enumerate(ounits):
                C[ounit][:, pid] = oexpect[:, tid]

        # calculate mean of standard deviations of outputs
        for oid, ounit in enumerate(ounits):

            # calculate norm by mean over part of data
            bound = int((1. - gauge) * data[0].shape[0])
            subset = numpy.sort(C[ounit].std(axis = 1))[bound:]
            norm = subset.mean() / data[1][:, oid].std()

            # calculate influence
            R[iid, oid] = norm

    # amplify contrast of induction
    A = R.copy()
    for iid, iunit in enumerate(iunits):
        for oid, ounit in enumerate(ounits):
            if ':' in ounit: inlabel = ounit.split(':')[1]
            else: inlabel = ounit
            if ':' in iunit: outlabel = iunit.split(':')[1]
            else: outlabel = iunit
            if inlabel == outlabel: A[iid, oid] = 0.0
    bound = numpy.amax(A)

    intensify = nemoa.system.commons.math.intensify
    return intensify(R, factor = contrast, bound = bound)
