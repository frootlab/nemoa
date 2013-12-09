#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# This python module contains special classes of multilayer            #
# feedforward artificial neuronal networks aimed for data modeling     #
########################################################################

import nemoa.system.ann, numpy

class dbn(nemoa.system.ann.ann):
    """Deep Belief Network (DBN).

    Description:
        Used for data classification and compression / decompression

    Reference:
    
    """

    @staticmethod
    def default(key):
        """Return DBN default configuration as dictionary."""
        return {
            'params': {
                'preTraining': True,
                'fineTuning': True,
                'visible': 'auto',
                'hidden': 'auto',
                'visibleClass': 'gauss',
                'hiddenClass': 'sigmoid',
                'visibleSystem': None,
                'visibleSystemModule': 'rbm',
                'visibleSystemClass': 'grbm',
                'hiddenSystem': None,
                'hiddenSystemClass': 'rbm',
                'hiddenSystemModule': 'rbm' },
            'init': {
                'checkDataset': False,
                'ignoreUnits': [],
                'wSigma': 0.5 },
            'optimize': {
                'checkDataset': False,
                'ignoreUnits': [],
                'iterations': 1,
                'algorithm': 'rprop',
                'updates': 10000,
                'schedule': None,
                'visible': None,
                'hidden': None,
                'useAdjacency': False,
                'inspect': True,
                'inspectFunction': 'performance',
                'inspectTimeInterval': 10.0 ,
                'estimateTime': True,
                'estimateTimeWait': 15.0 }}[key]

    def _checkNetwork(self, network):
        return self._isNetworkDBNCompatible(network)

    # UNITS

    def _getUnitsFromConfig(self):
        return None

    def _getLinksFromConfig(self):
        return None

    def _getLinksFromNetwork(self, network):
        return None

    def _optimizeParams(self, dataset, schedule):
        """Optimize system parameters."""

        # pretraining neuronal network using
        # layerwise restricted boltzmann machines as subsystems
        if schedule['params']['dbn.dbn']['preTraining']:
            self._preTraining(dataset, schedule)

        # finetuning neuronal network using backpropagation
        if schedule['params']['dbn.dbn']['fineTuning']:
            self._fineTuning(dataset, schedule)

        return True

    def _preTraining(self, dataset, schedule):
        """Pretraining ANN using Restricted Boltzmann Machines."""

        nemoa.log('info', 'pretraining system')
        nemoa.setLog(indent = '+1')

        ################################################################
        # Configure subsystems for pretraining                         #
        ################################################################

        nemoa.log('info', 'configure subsystems')
        nemoa.setLog(indent = '+1')
        if not 'units' in self._params:
            nemoa.log('error', 'could not configure subsystems: no layers have been defined')
            nemoa.setLog(indent = '-1')
            return False

        # create and configure subsystems
        subSystems = []
        for layerID in range((len(self._params['units']) - 1)  / 2):
            inUnits = self._params['units'][layerID]
            outUnits = self._params['units'][layerID + 1]
            links = self._params['links'][(layerID, layerID + 1)]

            # get subsystem configuration
            sysType = 'visible' if inUnits['visible'] else 'hidden'
            sysUserConf = self._config['params'][sysType + 'System']
            if sysUserConf:
                sysConfig = nmConfig.get(type = 'system', name = sysUserConf)
                if sysConfig == None:
                    nemoa.log('error', """
                        could not configure system:
                        unknown system configuration \'%s\'
                    """ % (sysUserConf))
                    nemoa.setLog(indent = '-1')
                    return False
            else:
                sysConfig = {
                    'package': self._config['params'][sysType + 'SystemModule'],
                    'class': self._config['params'][sysType + 'SystemClass']
                }

            # update subsystem configuration
            sysConfig['name'] = '%s ↔ %s' % (inUnits['name'], outUnits['name'])
            if not 'params' in sysConfig:
                sysConfig['params'] = {}
            if inUnits['visible']:
                sysConfig['params']['visible'] = \
                    self._params['units'][0]['label'] \
                    + self._params['units'][-1]['label']
            else:
                sysConfig['params']['visible'] = inUnits['label']
            sysConfig['params']['hidden'] = outUnits['label']

            # create instance of subsystem from configuration
            system = nemoa.system.new(config = sysConfig)

            nemoa.log('info', """
                adding subsystem: \'%s\' (%s units, %s links)
                """ % (system.getName(),
                len(system.getUnits()), len(system.getLinks())))

            # link subsystem
            subSystems.append(system)

            # link linksparameters of subsystem
            links['init'] = system._params['links'][(0, 1)]

            # link layerparameters of subsystem
            if layerID == 0:
                inUnits['init'] = system.units['visible'].params
                outUnits['init'] = system.units['hidden'].params
                system._config['init']['ignoreUnits'] = []
                system._config['optimize']['ignoreUnits'] = []
            else:
                # do not link params from upper
                # upper layer should be linked with pervious subsystem
                # (higher abstraction layer)
                outUnits['init'] = system._params['units'][1]
                system._config['init']['ignoreUnits'] = ['visible']
                system._config['optimize']['ignoreUnits'] = ['visible']

        self._config['check']['subSystems'] = True
        nemoa.setLog(indent = '-1')

        ################################################################
        # Optimize subsystems                                          #
        ################################################################

        # create copy of dataset values (before transformation)
        datasetCopy = dataset._get()

        # optimize subsystems
        for sysID in range(len(subSystems)):
            nemoa.log('info', 'optimize subsystem %s (%s)' \
                % (subSystems[sysID].getName(), subSystems[sysID].getType()))
            nemoa.setLog(indent = '+1')

            # link encoder and decoder system
            system = subSystems[sysID]

            # transform dataset with previous system / fix lower stack
            if sysID > 0:
                dataset.transformData(
                    system = subSystems[sysID - 1],
                    transformation = 'hiddenvalue',
                    colLabels = subSystems[sysID - 1].getUnits(visible = False))

            # initialize system
            # in higher layers 'initVisible' = False
            # prevents the system from reinitialization
            system.initParams(dataset)

            # optimize (free) system parameter
            system.optimizeParams(dataset, schedule)

            nemoa.setLog(indent = '-1')

        # reset data to initial state (before transformation)
        dataset._set(**datasetCopy)

        ################################################################
        # Copy and enrolle parameters of subsystems to dbn             #
        ################################################################

        nemoa.log('info', 'initialize system with subsystem parameters')
        nemoa.setLog(indent = '+1')

        # keep original inputs and outputs
        mapping = self._getMapping()
        inputs = self.units[mapping[0]].params['label']
        outputs = self.units[mapping[-1]].params['label']

        # expand unit parameters to all layers
        nemoa.log('info', 'import unit and link parameters from subsystems (enrolling)')
        units = self._params['units']
        links = self._params['links']
        for id in range((len(units) - 1)  / 2):

            # copy unit parameters
            for attrib in units[id]['init'].keys():
                # keep name and visibility of layers
                if attrib in ['name', 'visible', 'id']:
                    continue
                # keep labels of hidden layers
                if attrib == 'label' and not units[id]['visible']:
                    continue
                units[id][attrib] = units[id]['init'][attrib]
                units[-(id + 1)][attrib] = units[id][attrib]
            del units[id]['init']

            # copy link parameters and transpose numpy arrays
            for attrib in links[(id, id + 1)]['init'].keys():
                if attrib in ['source', 'target']:
                    continue
                links[(id, id + 1)][attrib] = \
                    links[(id, id + 1)]['init'][attrib]
                links[(len(units) - id - 2, len(units) - id - 1)][attrib] = \
                    links[(id, id + 1)]['init'][attrib].T
            del links[(id, id + 1)]['init']

        ################################################################
        # Remove input units from output layer, vice versa             #
        ################################################################

        nemoa.log('info', 'cleanup unit and linkage parameter arrays')
        self._removeUnits(self._getMapping()[0], outputs)
        self._removeUnits(self._getMapping()[-1], inputs)

        nemoa.setLog(indent = '-2')
        return True

    def _fineTuning(self, dataset, schedule):
        """Finetuning system using a variant of backpropagation of error."""
        nemoa.log('info', 'finetuning system')
        nemoa.setLog(indent = '+1')
        if self._config['optimize']['algorithm'].lower() in ['bprop', 'backpropagation']:
            self._optimizeBProp(dataset, schedule)
        elif self._config['optimize']['algorithm'].lower() == ['rprop', 'resiliant backpropagation']:
            self._optimizeRProp(dataset, schedule)
        else:
            nemoa.log('warning', """
                unknown algorithm %s
                """ % (self._config['optimize']['algorithm']))
        nemoa.setLog(indent = '-1')
        return True