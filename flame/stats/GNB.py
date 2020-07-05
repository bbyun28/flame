
# -*- coding: utf-8 -*-

# Description    Flame Parent Model Class
##
# Authors:       Jose Carlos Gómez (josecarlos.gomez@upf.edu)
#                Manuel Pastor (manuel.pastor@upf.edu)
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

from copy import copy

from sklearn.naive_bayes import GaussianNB

from nonconformist.base import ClassifierAdapter, RegressorAdapter
from nonconformist.acp import AggregatedCp
from nonconformist.acp import BootstrapSampler
from nonconformist.icp import IcpClassifier, IcpRegressor
from nonconformist.nc import ClassifierNc, MarginErrFunc, RegressorNc

from flame.stats.base_model import BaseEstimator
from flame.util import get_logger
LOG = get_logger(__name__)

class GNB(BaseEstimator):
    """
        This class inherits from BaseEstimator and wraps SKLEARN
        GaussianNB estimator

        ...
        
        Attributes
        ----------

        estimator_parameters : dict
            parameter values
        name : string
            name of the estimator
        
        
        Methods
        -------
        
        build(X)
            Instance the estimator optimizing it
            if tune=true.
        
    """

    def __init__(self, X, Y, parameters, conveyor):
        # Initialize parent class
        try:
            BaseEstimator.__init__(self, X, Y, parameters, conveyor)
            LOG.debug('Initializing BaseEstimator parent class')
        except Exception as e:
            self.conveyor.setError(f'Error initializing BaseEstimator parent class with exception: {e}')
            LOG.error(f'Error initializing BaseEstimator parent class with exception: {e}')
            return

        # Load estimator parameters                
        self.estimator_parameters = self.param.getDict('GNB_parameters')

        if self.param.getVal('quantitative'):
            self.conveyor.setError('GNB only applies to qualitative data')
            LOG.error('GNB only applies to qualitative data')
        else:
            self.name = "GNB-Classifier"

    def build(self):
        '''Build a new qualitative GNB model with the X and Y numpy matrices'''

        # Make a copy of data matrices
        X = self.X.copy()
        Y = self.Y.copy()

        results = []
        results.append(('nobj', 'number of objects', self.nobj))
        results.append(('nvarx', 'number of predictor variables', self.nvarx))
        results.append(('model', 'model type', 'GNB'))

        # Build estimator
        LOG.info('Building GaussianNB model')
        self.estimator = GaussianNB(**self.estimator_parameters)
        # results.append(('model', 'model type', 'GNB qualitative'))

        self.estimator.fit(X, Y)

        if not self.param.getVal('conformal'):
            return True, results

        # If conformal, then create aggregated conformal classifier
        self.estimator_temp = copy(self.estimator)
        self.estimator = AggregatedCp(
                            IcpClassifier(
                                ClassifierNc(
                                    ClassifierAdapter(self.estimator_temp),
                                    MarginErrFunc()
                                )
                            ),
                            BootstrapSampler())
        
        # Fit estimator to the data
        self.estimator.fit(X, Y)
        # results.append(('model', 'model type', 'conformal GNB qualitative'))
        
        return True, results
