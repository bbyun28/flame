#! -*- coding: utf-8 -*-

# Description    Flame Apply class
##
# Authors:       Manuel Pastor (manuel.pastor@upf.edu), Jose Carlos Gómez (josecarlos.gomez@upf.edu)
##
# Copyright 2018 Manuel Pastor
##
# This file is part of Flame
##
# Flame is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation version 3.
##
# Flame is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
##
# You should have received a copy of the GNU General Public License
# along with Flame.  If not, see <http://www.gnu.org/licenses/>.

import os
import pickle
from flame.stats.space import Space
from flame.util import utils, get_logger

LOG = get_logger(__name__)

class Sapply:

    def __init__(self, parameters, conveyor):

        self.param = parameters
        self.conveyor = conveyor
  
        # set modelID only for search workflows. Avoid
        # for similarity implemented in predict
        if self.conveyor.getOrigin() == 'sapply':
            endpoint = self.conveyor.getMeta('endpoint')
            version  = self.conveyor.getMeta('version')
            path = utils.space_path(endpoint, version)
            meta = os.path.join(path,'space-meta.pkl')
            with open(meta, 'rb') as handle:
                modelID = pickle.load(handle)

            self.conveyor.addMeta('modelID', modelID)
            LOG.debug (f'Loaded space with modelID: {modelID}')

        self.X = self.conveyor.getVal('xmatrix')


    def preprocess(self, X):
        ''' This function loads the scaler and variable mask from a pickle file 
        and apply them to the X matrix passed as an argument'''

        # update if other fingerprints are added
        if self.param.getVal('computeMD_method') == ['morganFP']:
            return True, X

        # Run scaling for MD but never for fingerprints
        if self.param.getVal('modelAutoscaling') is None:
            return True, X

        # Load preprocessing
        prepro_file = os.path.join(self.param.getVal('model_path'),
                                    'preprocessing.pkl')
        LOG.debug(f'Loading model from pickle file, path: {prepro_file}')
        try:
            with open(prepro_file, "rb") as input_file:
                dict_prepro = pickle.load(input_file)
        except FileNotFoundError:
            return False, f'No valid preprocessing tools found at: {prepro_file}'

        # Load version
        self.version = dict_prepro['version']

        # check if the pickle was created with a compatible version
        # currently 1
        if self.version is not 1:
            return False, 'Incompatible preprocessing version'   
    
        # Load rest of info in an extensible way
        # This allows to add new variables keeping
        # Retro-compatibility
        if 'scaler' in dict_prepro.keys():
            self.scaler = dict_prepro['scaler']

        # Check consistency between parameter file and pickle info
        if self.scaler is None:
            return False, 'Inconsistency error. Scaling method defined but no Scaler loaded'

        return True, self.scaler.transform(X)  


    def run (self, cutoff, numsel, metric): 
        ''' 

        Runs prediction tasks using internally defined methods

        Most of these methods can be found at the stats folder

        '''

        # Load scaler and variable mask and preprocess the data
        success, result = self.preprocess(self.X)
        if not success:
            self.conveyor.setError(result)
            return
        self.X = result

        # instances space object
        space = Space(self.param)

        # builds space from idata results
        LOG.info('Starting space searching')
        success, search_results = space.search (self.X, cutoff, numsel, metric)
        if not success:
            self.conveyor.setError(search_results)
            return

        self.conveyor.addVal(
                    search_results,
                    'search_results',
                    'Search results',
                    'result',
                    'objs',
                    'Collection of similar compounds','main')

        LOG.info('Space search finished successfully')

        return
