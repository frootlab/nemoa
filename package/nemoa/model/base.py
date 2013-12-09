#!/usr/bin/env python
# -*- coding: utf-8 -*-

import nemoa, numpy, copy, time, os

class model:
    """Base class for graphical models."""
    
    dataset = None
    network = None
    system  = None

    ####################################################################
    # Model configuration                                              #
    ####################################################################

    def __init__(self, config = {}, dataset = None, network = None, system = None, **kwargs):
        """Initialize model and configure dataset, network and system.

        Keyword Arguments:
            dataset -- dataset instance
            network -- network instance
            system  -- system instance
        """

        # initialize private scope class attributes
        self.__config = {}

        # update model name
        self.setName(kwargs['name'] if 'name' in kwargs else None)
        nemoa.log('info', """
            linking dataset, network and system instances to model""")

        self.dataset = dataset
        self.network = network
        self.system  = system

        if not self.isEmpty() and self.__checkModel():
            self.updateConfig()

    def __setConfig(self, config):
        """Set configuration from dictionary."""
        self.__config = config.copy()
        return True

    def __getConfig(self):
        """Return configuration as dictionary."""
        return self.__config.copy()

    def importConfigFromDict(self, dict):
        """check if config is valid."""
        config = {}

        # model configuration
        if 'config' in dict.keys():
            config['config'] = dict['config'].copy()
        else:
            nemoa.log('error', """
                could not set configuration:
                given dictionary does not contain configuration information!""")
            return None

        # get version of config
        version = config['config']['version']

        # dataset configuration
        if not 'dataset' in dict:
            nemoa.log('error', """
                could not configure dataset:
                given dictionary does not contain dataset information!""")
            return None
        else:
            config['dataset'] = dict['dataset'].copy()

        # network configuration
        if not 'network' in dict:
            nemoa.log('error', """
                could not configure network:
                given dictionary does not contain network information!""")
            return None
        else:
            config['network'] = dict['network'].copy()

        # system configuration
        if not 'system' in dict:
            nemoa.log('error', """
                could not configure system:
                given dictionary does not contain system information!""")
            return None
        else:
            config['system'] = dict['system'].copy()

        return config

    def __checkModel(self, allowNone = False):
        if (allowNone and self.dataset == None) \
            or not nemoa.type.isDataset(self.dataset):
            return False
        if (allowNone and self.network == None) \
            or not nemoa.type.isNetwork(self.network):
            return False
        if (allowNone and self.system == None) \
            or not nemoa.type.isSystem(self.system):
            return False
        return True

    def updateConfig(self):
        """Update model configuration."""

        # set version of model
        self.__config['version'] = nemoa.version()

        # set name of model
        if not 'name' in self.__config or not self.__config['name']:
            if not self.network.getName():
                self.setName('%s-%s' % (
                    self.dataset.getName(), self.system.getName()))
            else:
                self.setName('%s-%s-%s' % (
                    self.dataset.getName(), self.network.getName(),
                    self.system.getName()))
        return True

    def configure(self):
        """Configure model."""
        nemoa.log('info', 'configure model \'%s\'' % (self.getName()))
        nemoa.setLog(indent = '+1')
        if not 'check' in self.__config:
            self.__config['check'] = {'dataset': False, 'network': False, 'System': False}
        self.__config['check']['dataset'] = \
            self.dataset.configure(network = self.network)
        if not self.__config['check']['dataset']:
            nemoa.log('error', 'could not configure model: dataset could not be configured!')
            nemoa.setLog(indent = '-1')
            return False
        self.__config['check']['network'] = \
            self.network.configure(dataset = self.dataset, system = self.system)
        if not self.__config['check']['network']:
            nemoa.log('error', 'could not configure model: network could not be configured!')
            nemoa.setLog(indent = '-1')
            return False
        self.__config['check']['system'] = \
            self.system.configure(network = self.network, dataset = self.dataset)
        if not self.__config['check']['system']:
            nemoa.log('error', 'could not configure model: system could not be configured!')
            nemoa.setLog(indent = '-1')
            return False
        nemoa.setLog(indent = '-1')
        return True

    def __isConfigured(self):
        """Return True if model is allready configured."""
        return 'check' in self.__config \
            and self.__config['check']['dataset'] \
            and self.__config['check']['network'] \
            and self.__config['check']['system']

    ####################################################################
    # Model -> System parameter modification                           #
    ####################################################################

    def initialize(self):
        """Initialize model parameters and return self."""

        #2DO: just check if system is configured

        # check if model is empty and can not be initialized
        if (self.dataset == None or self.system == None) \
            and self.isEmpty():
            return self

        # check if model is configured
        if not self.__isConfigured():
            nemoa.log('error', """
                could not initialize model:
                model is not yet configured!""")
            return False

        # check dataset
        if not nemoa.type.isDataset(self.dataset):
            nemoa.log("error", """
                could not initialize model parameters:
                dataset is not yet configured!""")
            return False

        # check system
        if not nemoa.type.isSystem(self.system):
            nemoa.log("error", """
                could not initialize model parameters:
                system is not yet configured!""")
            return False
        elif self.system.isEmpty():
            return False

        # initialize system parameters
        self.system.initParams(self.dataset)
        return self

    def optimize(self, schedule = None, **kwargs):
        """Optimize system parameters."""

        #2DO: just check if system is initialized

        nemoa.log('title', 'optimize model')
        nemoa.setLog(indent = '+1')

        # check if model is empty
        if self.isEmpty():
            nemoa.log('warning', """
                empty models can not be optimized!""")
            nemoa.setLog(indent = '-1')
            return self

        # check if model is configured
        if not self.__isConfigured():
            nemoa.log('error', """
                could not optimize model:
                model is not yet configured!""")
            nemoa.setLog(indent = '-1')
            return False

        # get optimization schedule
        schedule = nemoa.workspace.getConfig(
            type = 'schedule', config = schedule,
            merge = ['params', self.system.getName()],
            **kwargs)
        if not schedule:
            nemoa.log('error', """
                could not optimize system parameters:
                optimization schedule is not valid!""")
            nemoa.setLog(indent = '-1')
            return self
        
        # optimization of system parameters
        nemoa.log('info', """
            starting optimization schedule: '%s'
            """ % (schedule['name']))
        nemoa.setLog(indent = '+1')

        # 2DO: find better solution for multistage optimization
        if 'stage' in schedule and len(schedule['stage']) > 0:
            for stage, params in enumerate(config['stage']):
                self.system.optimizeParams(self.dataset, **params)
        elif 'params' in schedule:
            self.system.optimizeParams(
                dataset = self.dataset, schedule = schedule)

        nemoa.setLog(indent = '-2')
        return self

    ####################################################################
    # Model interface to dataset instance                              #
    ####################################################################

    def __setDataset(self, dataset):
        """Set dataset."""
        self.dataset = dataset
        return True

    def __getDataset(self):
        """Return link to dataset instance."""
        return self.dataset

    def __confDataset(self, dataset = None, network = None, **kwargs):
        """Configure model.dataset to given dataset and network.

        Keyword Arguments:
            dataset -- dataset instance
            network -- network instance
        """
        dataset = self.dataset
        network = self.network

        # link dataset instance
        if nemoa.type.isDataset(dataset):
            self.dataset = dataset

        # check if dataset instance is valid
        if not nemoa.type.isDataset(self.dataset):
            nemoa.log('error',
            'could not configure dataset: no dataset instance available!')
            return False

        # check if dataset is empty
        if self.dataset.isEmpty():
            return True

        # prepare params
        if not network and not self.network:
            nemoa.log('error',
            'could not configure dataset: no network instance available!')
            return False

        return self.dataset.configure(network = network \
            if not network == None else self.network)

    ####################################################################
    # Model interface to network instance                              #
    ####################################################################

    def __setNetwork(self, network):
        """Set network."""
        self.network = network
        return True

    def __getNetwork(self):
        """Return link to network instance."""
        return self.network

    def __confNetwork(self, dataset = None, network = None, system = None, **kwargs):
        """Configure model.network to given network, dataset and system.

        Keyword Arguments:
            dataset -- dataset instance
            network -- network instance
        """

        # link network instance
        if nemoa.type.isNetwork(network):
            self.network = network

        # check if network instance is valid
        if not nemoa.type.isNetwork(self.network):
            nemoa.log('error', """
                could not configure network:
                no network instance available!""")
            return False

        # check if network instance is empty
        if self.network.isEmpty(): return True

        # check if dataset instance is available
        if self.dataset == None and dataset == None:
            nemoa.log('error', """
                could not configure network:
                no dataset instance available!""")
            return False
 
         # check if system instance is available
        if self.system == None and system == None:
            nemoa.log('error', """
                could not configure network:
                no system was given!""")
            return False

        # configure network 
        return self.network.configure(
            dataset = dataset if not dataset == None else self.dataset,
            system = system if not system == None else self.system)

    ####################################################################
    # Model interface to system instance                               #
    ####################################################################

    def __setSystem(self, system):
        """Set system."""
        self.system = system
        return True

    def __getSystem(self):
        """Return link to system instance."""
        return self.system

    #def __confSystem(self, dataset = None, network = None, system = None,  **kwargs):
        #"""Configure model.system to given dataset, network and system.

        #Keyword Arguments:
            #dataset -- nemoa dataset instance
            #network -- nemoa network instance
            #system -- nemoa system instance
        #"""

        ## get current system parameters
        #if nemoa.type.isSystem(system) and nemoa.type.isSystem(self.system):
            #prevModelParams = self.system._get()
        #else:
            #prevModelParams = None

        ## link system instance
        #if nemoa.type.isSystem(system):
            #self.system = system
        
        ## verify system instance
        #if not nemoa.type.isSystem(self.system): nemoa.log('error',
            #'could not configure system: no system instance available!')
            #return False

        ## verify dataset instance
        #if not (nemoa.type.isDataset(self.dataset) or nemoa.type.isDataset(dataset)):
            #nemoa.log('error', 'could not configure system: no dataset instance available!')
            #return False
        #elif not nemoa.type.isDataset(dataset): dataset = self.dataset

        ## verify network instance
        #if not (nemoa.type.isNetwork(self.network) or nemoa.type.isNetwork(network)):
            #nemoa.log('error', 'could not configure system: no network instance available!')
            #return False
        #elif not nemoa.type.isNetwork(network): network = self.network

        ## configure system
        #if not self.system.configure(network = network, dataset = dataset):
            #return False

        ## overwrite new model parameters with previous
        #if prevModelParams:
            #nemoa.log('info', 'get model parameters from previous model')
            #self.system._overwrite_conf(**modelParams)
            ##2DO create new entry in actual branch
        #else:
            #self.__config['branches']['main'] = self.system._get()

        #return True

    ####################################################################
    # Scalar model evaluation functions                                #
    ####################################################################

    def getPerformance(self):
        """Return euclidean data reconstruction performance of system."""
        dataIn = self.system._getMapping()[0]
        dataOut = self.system._getMapping()[-1]
        data = self.dataset.getData(cols = (dataIn, dataOut))
        return self.system.getPerformance(data)

    def getError(self):
        """Return data reconstruction error of system."""
        dataIn = self.system._getMapping()[0]
        dataOut = self.system._getMapping()[-1]
        data = self.dataset.getData(cols = (dataIn, dataOut))
        return self.system.getError(data)

    ####################################################################
    # Evaluation of unit relations                                     #
    ####################################################################

    def getUnitRelationMatrix(self, units = None, x = None, y = None,
        relation = 'correlation()', preprocessing = None, statistics = 10000):

        # 2DO! kick parameter "units"

        # get visible and hidden units
        # and set visble as default for unknown unit lists
        visible = self.system.getUnits(visible = True)
        hidden = self.system.getUnits(visible = False)
        if units:
            x = units
            y = units
        elif x and not y:
            units = x
            y = x
        elif not x and y:
            units = y
            x = y
        elif not x and not y:
            units = visible
            x = visible
            y = visible

        relFunc, relParams = nemoa.common.strSplitParams(relation)

        # get data and perform data preprocessing
        data = self.dataset.getData(statistics)
        if not preprocessing == None:
            plain = numpy.copy(data)
            data = self.system.getDataRepresentation(data, transformation = preprocessing)

        # get relation as matrix
        if relFunc == 'correlation':
            M = self.__getUnitCorrelationMatrix(units = units, data = data, **relParams)
        elif relFunc == 'causality':
            M = self.__getUnitCausalityMatrix(x = x, y = y, data = data, **relParams)
        else:
            return None

        # transform matrix
        if 'transform' in relParams:
            if 'C' in relParams['transform']:
                if not preprocessing == None:
                    C = self.__getUnitCorrelationMatrix(units = units, data = plain)
                else:
                    C = self.__getUnitCorrelationMatrix(units = units, data = data)
            try:
                T = eval(relParams['transform'])
            except:
                nemoa.log('warning', 'could not transform unit relation matrix: invalid syntax!')
                return M
            return T

        return M

    def getUnitRelationMatrixMuSigma(self, matrix, relation):

        # parse relation
        reType = re.search('\Acorrelation|causality', relation.lower())
        if not reType:
            nemoa.log("warning", "unknown unit relation '" + relation + "'!")
            return None
        type = reType.group()

        numRelations = matrix.size
        numUnits = matrix.shape[0]

        # create temporary array which does not contain diag entries
        A = numpy.zeros((numRelations - numUnits))
        k = 0
        for i in range(numUnits):
            for j in range(numUnits):
                if i == j:
                    continue
                A[k] = matrix[i, j]
                k += 1

        mu = numpy.mean(A)
        sigma = numpy.std(A)

        if type == 'causality':
            Amax = numpy.max(A)
            Aabs = numpy.abs(A)
            Alist = []
            for i in range(Aabs.size):
                if Aabs[i] > Amax:
                    continue
                Alist.append(Aabs[i])
            A = numpy.array(Alist)

            mu = numpy.mean(A)
            sigma = numpy.std(A)

        return mu, sigma

    def __getUnitCorrelationMatrix(self, units = None, data = None, **kwargs):

        """
        Description:
        calculate correlation matrix

        Keyword arguments:
        units -- list of strings with valid unitIDs
        """

        # create data and calulate correlation matrix
        M = numpy.corrcoef(data.T)

        # create output matrix
        C = numpy.zeros(shape = (len(units), len(units)))
        for i, u1 in enumerate(units):
            k = self.system.getUnitInfo(u1)['id']
            for j, u2 in enumerate(units):
                l = self.system.getUnitInfo(u2)['id']
                C[i, j] = M[k, l]

        return C

    def __getUnitCausalityMatrix(self, x, y,
        measure = 'relapprox', modify = 'setmean', data = None, **kwargs):
        """Return numpy array with data manipulation results.

        Keyword Arguments:
            y -- list with labels of manipulated units on y axis of matrix
            x -- list with labels of effected units on x axis of matrix+
            modify -- type of manipulation
            measure -- name of measurement function
            data -- numpy array with data to test

        Description:
            Manipulate unit values and measure effect on other units,
            respective to given data
        """

        # prepare causality matrix
        K = numpy.zeros((len(y), len(x)))

        # calculate unit values without modification
        func = self.about('system', 'units', 'measure', measure, 'name')
        nemoa.log('info', 'calculate %s effect on %s' % (modify, func))
        tStart = time.time()
        #
        #
        #
        #
        #
        #
        #
        #
        #
        #
        #
        #
        uLink  = self.getUnitEval(func = measure, data = data)
        #
        #
        ##
        ##
        #
        #
        #
        #
        #
        ##
        ##
        tStop  = time.time()
        nemoa.log("info", 'estimated duration: %.1fs' % ((tStop - tStart) * len(y)))

        for i, kUnit in enumerate(y):

            # modify unit and calculate unit values
            if modify == 'unlink':
                links = self.system.getLinks()
                self.system.unlinkUnit(kUnit)
                uUnlink = self.getUnitEval(func = measure, data = data)
                self.system.setLinks(links)
            elif modify == 'setmean':
                uID = self.system.getUnitInfo(kUnit)['id']
                uUnlink = self.getUnitEval(func = measure, data = data, block = [uID])

            # store difference in causality matrix
            for j, mUnit in enumerate(x):
                if mUnit == kUnit:
                    continue
                K[i,j] = uUnlink[mUnit] - uLink[mUnit]

        return K










    ##
    ## MODEL PARAMETER HANDLING
    ##

    #def findRelatedSampleGroups(self, **params):
        #nemoa.log("info", "find related sample groups in dataset:")

        #partition = self.dataset.createRowPartition(**params)
        #return self.dataset.getRowPartition(partition)

    #def createBranches(self, modify, method, **params):
        #nemoa.log("info", 'create model branches:')
        
        #if modify == 'dataset':
            #if method == 'filter':
                #filters = params['filter']

                ## get params from main branch
                #mainParams = self.system._get()

                ## create branches for filters
                #for filter in filters:
                    
                    #branch = self.dataset.cfg['name'] + '.' + filter

                    ## copy params from main branch
                    #self.__config['branches'][branch] = mainParams.copy()

                    ## modify params
                    #self.__config['branches'][branch]['config']['params']['samplefilter'] = filter

                    ## set modified params
                    #self.system._set(**self.__config['branches'][branch])

                    ## reinit system
                    #self.system.initParams(self.dataset)

                    ## save system params in branch
                    #self.__config['branches'][branch] = self.system._get()

                    #nemoa.log("info", "add model branch: '" + branch + "'")

                ## reset system params to main branch
                #self.system._set(**mainParams)

                #return True

        #return False

    ##
    ## RELATIONS BETWEEN SAMPLES
    ##

    #def getSampleMeasure(self, data, func = None):

        #if not func or func == 'plain':
            #return data

        #return self.system.getSampleMeasure(data, func)

    #def getSampleRelationInfo(self, relation):

        #rel  = {}
        #list = relation.lower().split('_')

        ## get relation type
        #reType = re.search('\Adistance|correlation', relation.lower())
        #if reType:
            #rel['type'] = reType.group()
        #else:
            #rel['type'] = None
            #nemoa.log("warning", "unknown sample relation '" + relation + "'!")

        ## get relation params and info
        #rel['params'] = {}
        #rel['properties'] = {}
        #if rel['type'] == 'correlation':
            #rel['properties']['symmetric'] = True
            #if len(list) > 1:
                #rel['params']['func'] = list[1]
        #elif rel['type'] == 'distance':
            #rel['properties']['symmetric'] = False
            #if len(list) > 1:
                #rel['params']['distfunc'] = list[1]
            #if len(list) > 2:
                #rel['params']['func'] = list[2]

        #return rel

    #def getSampleRelationMatrix(self, samples = '*', relation = 'distance_euclidean_hexpect'):

        #rel = self.getSampleRelationInfo(relation)

        #if rel['type'] == 'correlation':
            #return self.getSampleCorrelationMatrix(**rel['params'])
        #if rel['type'] == 'distance':
            #return self.getSampleDistanceMatrix(samples, **rel['params'])

        #return None

    #def getSampleRelationMatrixMuSigma(self, matrix, relation):

        #rel = self.getSampleRelationInfo(relation)

        #numRelations = matrix.size
        #numUnits = matrix.shape[0]

        ### TODO: correlation vs causality effect

        ## create temporary array which does not contain diag entries
        #A = numpy.zeros((numRelations - numUnits))
        #k = 0
        #for i in range(numUnits):
            #for j in range(numUnits):
                #if i == j:
                    #continue
                #A[k] = matrix[i, j]
                #k += 1

        #mu = numpy.mean(A)
        #sigma = numpy.std(A)

        #return mu, sigma

    ## calculate correlation matrix
    #def getSampleCorrelationMatrix(self, func = 'plain'):

        ## get data
        #data = self.getSampleMeasure(self.dataset.getData(), func = func)

        ## calculate correlation matrix
        #return numpy.corrcoef(data)

    ## calculate sample distance matrix
    #def getSampleDistanceMatrix(self, samples = '*', distfunc = 'euclidean', func = 'plain'):

        ## get data
        #data = self.getSampleMeasure(self.dataset.getData(), func = func)

        ## calculate distance matrix
        #D = numpy.zeros(shape = (data.shape[0], data.shape[0]))
        #for i in range(D.shape[0]):
            #for j in range(D.shape[1]):
                #if i > j:
                    #continue

                #D[i, j] = numpy.sqrt(numpy.sum((data[i,:] - data[j,:]) ** 2))
                #D[j, i] = D[i, j]

        #return D

    #
    # SYSTEM EVALUATION
    #

    def _getEval(self, data = None, statistics = 100000, **kwargs):
        """Return dictionary with units and evaluation values."""
        if data == None: # get data if not given
            data = self.dataset.getData(statistics)
        return self.system.getDataEval(data, **kwargs)

    #
    # UNIT EVALUATION
    #

    def getUnitEval(self, data = None, statistics = 10000, **kwargs):
        """Return dictionary with units and evaluation values."""
        if data == None: # get data if not given
            data = self.dataset.getData(statistics)
        return self.system.getUnitEval(data, **kwargs)

    #
    # LINK EVALUATION
    #

    def _getLinkEval(self, data= None, statistics = 10000, **kwargs):
        """Return dictionary with links and evaluation values."""
        if data == None: # get data if not given
            data = self.dataset.getData(statistics)
        return self.system.getLinkEval(data, **kwargs)

    #
    # MODEL EVALUATION
    #

    def eval(self, func = 'expect', data = None, block = [],
        k = 1, m = 1, statistics = 10000):

        # set default values to params if not set
        if data == None:
            data = self.dataset.getData(statistics)

        vEval, hEval = self.system.getUnitEval(data, func, block, k, m)
        mEval = numpy.mean(vEval)

        units = {}
        for i, v in enumerate(self.system.params['v']['label']):
            units[v] = vEval[i]
        for j, h in enumerate(self.system.params['h']['label']):
            units[h] = hEval[j]

        return mEval, units

    #
    # get / set all model parameters as dictionary
    #
    
    def _get(self, sec = None):
        dict = {
            'config': copy.deepcopy(self.__config),
            'network': self.network._get() if hasattr(self.network, '_get') else None,
            'dataset': self.dataset._get() if hasattr(self.dataset, '_get') else None,
            'system': self.system._get() if hasattr(self.system, '_get') else None
        }

        if not sec:
            return dict
        if sec in dict:
            return dict[sec]

        return None

    def _set(self, dict):
        """
        set configuration, parameters and data of model from given dictionary
        return true if no error occured
        """

        # get config from dict
        config = self.importConfigFromDict(dict)

        # check self
        if not nemoa.type.isDataset(self.dataset):
            nemoa.log('error', """
                could not configure dataset:
                model does not contain dataset instance!""")
            return False
        if not nemoa.type.isNetwork(self.network):
            nemoa.log('error', """
                could not configure network:
                model does not contain network instance!""")
            return False
        if not nemoa.type.isSystem(self.system):
            nemoa.log('error', """
                could not configure system:
                model does not contain system instance!""")
            return False

        self.__config = config['config'].copy()
        self.network._set(**config['network'])
        self.dataset._set(**config['dataset'])

        ## prepare
        if not 'update' in config['system']['config']:
            config['system']['config']['update'] = {'A': False}

        ## 2do system._set(...) shall create system
        ## and do something like self.configure ...

        # create system
        self.system = nemoa.system.new(
            config  = config['system']['config'].copy(),
            network = self.network,
            dataset = self.dataset
        )
        self.system._set(**config['system'])

        return self

    def save(self, file = None):
        """Save model settings to file and return filepath."""

        nemoa.log('title', 'save model to file')
        nemoa.setLog(indent = '+1')

        # get filename
        if file == None:
            fileName = '%s.mp' % (self.getName())
            filePath = nemoa.workspace.path('models')
            file = filePath + fileName
        file = nemoa.common.getEmptyFile(file)

        # save model parameters and configuration to file
        nemoa.common.dictToFile(self._get(), file)

        # create console message
        nemoa.log('info', """
            save model as: '%s'
            """ % (os.path.basename(file)[:-3]))

        nemoa.setLog(indent = '-1')
        return file

    def plot(self, plot, output = 'file', file = None, **kwargs):
        """Create plot of model."""

        nemoa.log('title', 'create plot of model')
        nemoa.setLog(indent = '+1')

        # check if model is configured
        if not self.__isConfigured():
            nemoa.log('error', 'could not create plot of model: model is not yet configured!')
            nemoa.setLog(indent = '-1')
            return False

        # get plot instance
        if isinstance(plot, str):
            plotName, plotParams = nemoa.common.strSplitParams(plot)
            mergeDict = plotParams
            for param in kwargs.keys():
                plotParams[param] = kwargs[param]
            objPlot = self.__getPlot(name = plotName, params = plotParams)
            if not objPlot:
                nemoa.log("warning", "could not create plot: unknown configuration '%s'" % (plotName))
                return None
        elif isinstance(plot, dict):
            objPlot = self.__getPlot(config = plot)
        else:
            objPlot = self.__getPlot()
        if not objPlot:
            return None

        # prepare filename
        if output == 'display':
            file = None
        elif output == 'file' and not file:
            file = nemoa.common.getEmptyFile(nemoa.workspace.path('plots') + \
                self.getName() + '/' + objPlot.cfg['name'] + \
                '.' + objPlot.settings['fileformat'])
            nemoa.log('info', 'create plot: ' + file)

        # create plot
        retVal = objPlot.create(self, file = file)
        
        nemoa.setLog(indent = '-1')
        return retVal

    def __getPlot(self, name = None, params = {}, config = {}, **options):
        """Return new plot instance"""

        # return empty plot instance if no configuration information was given
        if not name and not config: return nemoa.plot.new()

        # get plot configuration
        if name == None: cfgPlot = config.copy()
        else:
            cfgPlot = nemoa.workspace.get('plot', name = name, params = params)

        # create plot instance
        if not cfgPlot == None:
            nemoa.log("info", "create plot instance: '" + name + "'")
            # merge params
            for param in params.keys():
                cfgPlot['params'][param] = params[param]
            return nemoa.plot.new(config = cfgPlot)
        else:
            nemoa.log("error", "could not create plot instance: unkown plot-id '" + name + "'")
            return None

    ####################################################################
    # Generic / static model information                               #
    ####################################################################

    def getName(self):
        """Return name of model."""
        return self.__config['name'] if 'name' in self.__config else ''

    def setName(self, name):
        """Set name of model."""
        if isinstance(self.__config, dict):
            self.__config['name'] = name
            return True
        return False

    def isEmpty(self):
        """Return true if model is empty."""
        return not 'name' in self.__config or not self.__config['name']

    def groups(self):
        """Return list with unit groups."""
        return self.system.getUnitGroups()

    def units(self, group = None):
        """Return list of units in a given group.
        
        Keyword Arguments:
            group -- name of unit group
        """
        return self.system.getUnits(name = group)

    def unit(self, unit):
        """Return information about one unit.
        
        Keyword Argument:
            unit -- name of unit
        """
        return self.network.node(unit)

    def link(self, link):
        """Return information about one link
        
        Keyword Argument:
            link -- name of link
        """
        return self.network.edge(link)

    def about(self, *args):
        """Return generic information about various parts of the model.

        Arguments:
            *args -- tuple of strings, containing a breadcrump trail to
                a specific information about the model

        Examples:
            about('dataset', 'preprocessing', 'transformation')
            
            about('system', 'units', 'measure', 'error')
                Returns information about the "error" measurement
                function of the systems units.
        """
        if args[0] == 'dataset': return self.dataset.about(*args[1:])
        if args[0] == 'network': return self.network.about(*args[1:])
        if args[0] == 'system':  return self.system.about(*args[1:])
        if args[0] == 'name':    return self.getName()
        return None

#class empty(model):
    #pass