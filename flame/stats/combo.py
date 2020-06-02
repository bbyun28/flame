#! -*- coding: utf-8 -*-

# Description    Set of combination models
##
# Authors:       Manuel Pastor (manuel.pastor@upf.edu)
##
# Copyright 2019 Manuel Pastor
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

import numpy as np
import copy
import yaml
import os
from sklearn.metrics import mean_squared_error
from sklearn.metrics import confusion_matrix
from sklearn.metrics import matthews_corrcoef
from scipy import stats
from flame.stats.base_model import BaseEstimator
from flame.util import get_logger

LOG = get_logger(__name__)
SIMULATION_SIZE = 500

class Combo (BaseEstimator):
    """
       Generic class for combining results of multiple models
    """
    def __init__(self, X, Y, parameters, conveyor):
        # Initialize parent class
        try:
            BaseEstimator.__init__(self, X, Y, parameters, conveyor)
            LOG.debug('Initialize BaseEstimator parent class')
        except Exception as e:
            LOG.error(f'Error initializing BaseEstimator parent'
                    f'class with exception: {e}')
            raise e

        self.method_name = ''


    def build(self):
        '''nothing to build, just return a some model information '''

        results = []
        results.append(('nobj', 'number of objects', self.nobj))
        results.append(('nvarx', 'number of predictor variables', self.nvarx))
        results.append(('model', 'model type', 'combination:'+self.method_name))

        return True, results

    def predict(self, X):
        ''' the method used to combine the results, this is a dummy method '''
        return 0

    def project(self, Xb):
        '''return the median of the input parameters'''

        Yp = self.predict(Xb)
        if Yp is None:
            self.conveyor.setError('prediction error') 
            return

        self.conveyor.addVal(Yp, 'values', 'Prediction',
                        'result', 'objs',
                        'Results of the prediction', 'main')

    def validate(self):
        ''' validate the model and return a set of results. This version does not performs CV '''

         # Make a copy of the original matrices
        X = self.X.copy()
        Y = self.Y.copy()

        # Get predicted Y
        Yp = self.predict(X)
        if Yp is None:
            return False, 'prediction error'

        info = []

        if self.param.getVal('quantitative'):
            # Compute  mean of predicted Y
            Ym = np.mean(Y)

            # Compute Goodness of the fit metric (adjusted Y)
            try:
                SSY0 = np.sum(np.square(Ym-Y))
                SSY = np.sum(np.square(Yp-Y))

                self.scoringR = np.mean(
                    mean_squared_error(Y, Yp)) 
                self.SDEC = np.sqrt(SSY/self.nobj)
                if SSY0 == 0.00:
                    self.R2 = 0.0
                else:
                    self.R2 = 1.00 - (SSY/SSY0)

                info.append(('scoringR', 'Scoring R', self.scoringR))
                info.append(('R2', 'Determination coefficient', self.R2))
                info.append(('SDEC', 'Standard Deviation Error of the Calculations', self.SDEC))

                info.append(('scoringP', 'Scoring P', self.scoringR))
                info.append(('Q2', 'Determination coefficient in cross-validation', self.R2))
                info.append(('SDEP', 'Standard Deviation Error of the Predictions', self.SDEC))

                LOG.debug(f'Goodness of the fit calculated: {self.scoringR}')
            except Exception as e:
                return False, f'Error computing goodness of the fit with exception {e}'
                
        else:
            # Get confusion matrix for predicted Y
            try:
                self.TNpred, self.FPpred,self.FNpred, self.TPpred = confusion_matrix(Y, Yp, labels=[0, 1]).ravel()

                self.sensitivityPred = 0.000
                if (self.TPpred + self.FNpred) > 0:
                    self.sensitivityPred = (self.TPpred / (self.TPpred + self.FNpred))
                
                self.specificityPred = 0.000
                if (self.TNpred + self.FPpred) > 0:
                    self.specificityPred = (self.TNpred / (self.TNpred + self.FPpred))

                self.mccp = matthews_corrcoef(Y, Yp)

                # TODO: it is not too clear if the results of validation in ensemble models is internal or
                # external. Both sets are added to avoid problems with the GUI but this requires futher
                # clarification
                info.append(('TP', 'True positives', self.TPpred))
                info.append(('TN', 'True negatives', self.TNpred))
                info.append(('FP', 'False positives', self.FPpred))
                info.append(('FN', 'False negatives', self.FNpred))
                info.append(('Sensitivity', 'Sensitivity in fitting', self.sensitivityPred))
                info.append(('Specificity', 'Specificity in fitting', self.specificityPred))
                info.append(('MCC', 'Matthews Correlation Coefficient', self.mccp))

                info.append(('TP_f', 'True positives', self.TPpred))
                info.append(('TN_f', 'True negatives', self.TNpred))
                info.append(('FP_f', 'False positives', self.FPpred))
                info.append(('FN_f', 'False negatives', self.FNpred))
                info.append(('Sensitivity_f', 'Sensitivity in fitting', self.sensitivityPred))
                info.append(('Specificity_f', 'Specificity in fitting', self.specificityPred))
                info.append(('MCC_f', 'Matthews Correlation Coefficient', self.mccp))

                LOG.debug('Computed class prediction for estimator instances')
            except Exception as e:
                return False, f'Error computing class prediction of Yexp with exception: {e}'

        # info.append (('Y_adj', 'Adjusted Y values', Yp) )          

        results = {}
        results ['quality'] = info
        results ['Y_adj'] = Yp
        results ['Y_pred'] = Yp

        return True, results

    def save_model(self):
        return True, 'OK'

    def load_model(self):
        return True, 'OK'


    def getConfidence (self):

        CI_names = self.conveyor.getVal('ensemble_confidence_names')
        if  CI_names is not None and len(CI_names)==(2 * self.nvarx):

            CI_vals = self.conveyor.getVal('ensemble_confidence')

            # conformal confidence of the top model
            cs_top = self.param.getVal('conformalSignificance') 
            
            # conformal confidence default is 0.8
            if cs_top is None:
                cs_top = 0.2  # fallback!!! we asume a default confidence of 80%

            cs_top_left  = cs_top /2.0
            cs_top_right = 1.0 - cs_top_left

            # gather array of confidences for low models
            cs_low = self.conveyor.getVal('ensemble_significance')
            if cs_low is None:
                cs_low = [cs_top for i in range(self.nvarx)]
            elif None in cs_low:
                cs_low = [cs_top for i in range(self.nvarx)]

            zcoeff = []
            for iconf in cs_low:
                cs_low_right = (1.0 - (iconf/2.0) )
                z = stats.norm.ppf (cs_low_right)
                zcoeff.append (1.0 / (z*2.0) ) 

            return True, (CI_vals, zcoeff, cs_top_left, cs_top_right)
        
        else:

            return False, None

    

class median (Combo):
    """
       Simple median calculator used to combine the results of multiple models
    """
    def __init__(self, X, Y, parameters, conveyor):
        Combo.__init__(self, X, Y, parameters, conveyor)
        self.method_name = 'median'

    def predict(self, X):

       # obtain dimensions of X matrix
        self.nobj, self.nvarx = np.shape(X)

        computeCI, CIparams = self.getConfidence ()
        if computeCI:
            ############################################
            ##
            ##  Compute CI
            ##
            ############################################

            CI_vals      = CIparams[0]
            zcoeff       = CIparams[1]
            # cs_top_left  = CIparams[2]
            # cs_top_right = CIparams[3]

            w = np.zeros(self.nvarx, dtype = np.float64 )
            xmedian = []
            cilow = []
            ciupp = []

            for j in range (self.nobj):
                pred = []
                for i in range (self.nvarx):
                    cirange = CI_vals[j,i*2+1] - CI_vals[j,i*2]

                    # sd = r/(z*2)
                    sd = cirange * zcoeff[i]
                    w[i] = 1.0/np.square(sd)

                    # create a tupla with prediction ID, value and weight
                    pred.append ( (i, X[j,i], w[i]) )
                    
                # w center is the mean of all weights, it is used to 
                # find the center of the distibution
                wcenter = np.sum(w)/2.00

                # sort pred
                sorted_pred = sorted(pred, key=lambda tup: tup[1])

                # fpr even number of predictions
                if self.nvarx % 2 == 0:

                    # trivial situation
                    if self.nvarx == 2:
                        selectedA = 0
                        selectedB = 1

                    # non-trivial, sort and iterate until we overpass wcenter
                    else:
                        acc_w = 0.00
                        selectedA = sorted_pred[0][0]
                        for i,ipred in enumerate(sorted_pred):
                            selectedB = ipred[0]
                            # accumulate weights
                            acc_w += ipred[2]
                            if acc_w > wcenter:
                                break
                        selectedA = sorted_pred[i-1][0]

                    # print ('even',j, selectedA, selectedB)

                    xmedian.append(np.mean((X[j,selectedA], X[j,selectedB])))

                    # this provides the CI at the original confidence level of the lower model
                    # TODO: use the confidence of the top model to recompute these CIs
                    cilow.append(np.mean((CI_vals[j,selectedA*2], CI_vals[j,selectedB*2])))
                    ciupp.append(np.mean((CI_vals[j,(selectedA*2)+1], CI_vals[j,(selectedB*2)+1])))

                # for odd number of predictions
                else:
                    acc_w = 0.00
                    for ipred in sorted_pred:
                        selected = ipred[0]    
                        # accumulate weights
                        acc_w += ipred[2]
                        if acc_w >= wcenter:
                            break

                    # print ('odd',j, selected)

                    xmedian.append(X[j,selected])

                    # this provides the CI at the original confidence level of the lower model
                    # TODO: use the confidence of the top model to recompute these CIs
                    cilow.append(CI_vals[j,selected*2])
                    ciupp.append(CI_vals[j,(selected*2)+1])

            self.conveyor.addVal(np.array(cilow), 
                        'lower_limit', 
                        'Lower limit', 
                        'confidence',
                        'objs',
                        'Lower limit of the conformal prediction'
                    )

            self.conveyor.addVal(np.array(ciupp), 
                        'upper_limit', 
                        'Upper limit', 
                        'confidence',
                        'objs',
                        'Upper limit of the conformal prediction'
                    )

            #print (xmedian, cilow, ciupp)

            return np.array(xmedian)

        else:
            ############################################
            ##
            ##  Compute single value
            ##
            ############################################

            return np.median (X,1)

class mean (Combo):
    """
       Simple mean calculator used to combine the results of multiple models
    """
    def __init__(self, X, Y, parameters, conveyor):
        Combo.__init__(self, X, Y, parameters, conveyor)
        self.method_name = 'mean'

    def predict(self, X):

        # obtain dimensions of X matrix
        self.nobj, self.nvarx = np.shape(X)

        computeCI, CIparams = self.getConfidence ()
        if computeCI:
            ############################################
            ##
            ##  Compute CI
            ##
            ############################################

            CI_vals      = CIparams[0]
            zcoeff       = CIparams[1]
            # cs_top_left  = CIparams[2]
            cs_top_right = CIparams[3]

            # compute weigthed mean and CI for the estimator
            # as described here
            #
            #   https://en.wikipedia.org/wiki/Weighted_arithmetic_mean#Weighted_sample_variance
            #

            xmean = []
            cilow = []
            ciupp = []

            z = stats.norm.ppf (cs_top_right)
            # print ("z is:", z)

            for j in range (self.nobj):

                # weigths are assigned to every input variable x based on 1/var(x)
                w = np.zeros(self.nvarx, dtype = np.float64 )
                for i in range (self.nvarx):
                    cirange = CI_vals[j,i*2+1] - CI_vals[j,i*2]
                    sd = cirange * zcoeff[i]
                    w[i] = 1.0/np.square(sd)

                ws = np.sum(w)

                #s describes the SEM and will be used latter for obtaining the CI
                s = 1.0/np.sqrt(ws)

                xm = 0.0
                for i in range (self.nvarx):
                    xm += X[j,i]*w[i]
                xmean.append(xm/ws) 

                # print (xm, ws, xm/ws, z, s)

                cilow.append((xm/ws) -z*s)
                ciupp.append((xm/ws) +z*s)

            self.conveyor.addVal(np.array(cilow), 
                        'lower_limit', 
                        'Lower limit', 
                        'confidence',
                        'objs',
                        'Lower limit of the conformal prediction'
                    )

            self.conveyor.addVal(np.array(ciupp), 
                        'upper_limit', 
                        'Upper limit', 
                        'confidence',
                        'objs',
                        'Upper limit of the conformal prediction'
                    )
            
            return np.array(xmean)
        else:
            ############################################
            ##
            ##  Compute single value
            ##
            ############################################
            return np.mean (X,1)

class majority (Combo):
    """
       Simple majority voting calculator used to combine the results of multiple models
    """
    def __init__(self, X, Y, parameters, conveyor):
        Combo.__init__(self, X, Y, parameters, conveyor)
        self.method_name = 'majority voting'

        # majority is not compatible with conformal because the prediction results
        # are not stored as c0, c1 but as value, ensemble_c0, ensemble_c1
        if self.param.getVal('conformal'):
            self.param.setVal('conformal', False)

    def predict(self, X):

        # obtain dimensions of X matrix
        self.nobj, self.nvarx = np.shape(X)

        # check if the underlying models are conformal
        CI_vals = self.conveyor.getVal('ensemble_confidence')

        # print ('confidence: ', confidence)

        # when not all models are conformal use a simple approach
        if CI_vals is None or len(CI_vals[0]) != (2 * self.nvarx):

            ############################################
            ##
            ##  Compute single value
            ##
            ############################################
            yp = np.zeros(self.nobj, dtype=np.float64)
            for i in range(self.nobj):
                xline = X[i]
                if xline[xline>=0].size == 0:  # all uncertains
                    yp[i] = -1
                else:
                    temp = np.mean(xline[xline>=0])
                    if temp == 0.5: # equal number of positive and negatives
                        yp[i] = -1
                    elif temp > 0.5:
                        yp[i] = 1
        else:
        
            ############################################
            ##
            ##  Compute CI
            ##
            ############################################

            # if all models are conformal, simply add the classes
            # and return 0 if majority is class 0, 1 if majority is class 1
            # and -1 if there is a tie
            yp = np.zeros(self.nobj, dtype=np.float64)
            c0 = np.zeros(self.nobj, dtype=np.float64)
            c1 = np.zeros(self.nobj, dtype=np.float64)

            for i,iobj in enumerate(CI_vals):
                for j in range(self.nvarx):
                    c0[i] += iobj[j*2]
                    c1[i] += iobj[(j*2)+1] 
                if c1[i] > c0[i]:
                    yp[i] = 1
                elif c0[i] == c1[i]:
                    yp[i] = -1

            # add the sum of classes for evaluating the result
            self.conveyor.addVal(c0, 
                        'ensemble_c0', 
                        'Ensemble Class 0', 
                        'confidence',
                        'objs',
                        'Conformal class assignment'
                    )

            self.conveyor.addVal(c1, 
                        'ensemble_c1', 
                        'Ensemble Class 1', 
                        'confidence',
                        'objs',
                        'Conformal class assignment'
                    )
        return yp

class matrix (Combo):
    """
       Lockup matrix

       TODO: 
       - implementing qualitative input and/or output
       - use conformal settings to decide to run or not the simulations to compute CI

    """
    def __init__(self, X, Y, parameters, conveyor):
        Combo.__init__(self, X, Y, parameters, conveyor)
        self.model_path = parameters.getVal('model_path')
        self.method_name = 'matrix'


    def lookup (self, x, vmatrix):
        """Uses the array x of quantitative values to lookup in the matrix of values vmatrix the
         corresponding value 
         
         The binning of the cells of vmatrix are defined by the following class variables which 
         define, for each matrix dimension: 
          - self.vzero: starting value
          - self.vsize: number of cells
          - self.vstep: width of bins 
         
         Once the variables are transformed into vmatrix indexes, a single matrix_index is computed
         since the n-dimensional vmatrix is stored as a deconvoluted monodimensional array
        """

        # transform the values of the vectors into vmatrix indexes
        # note that:
        #   values < self.vzero are set to 0
        #   values > self.vzero + self.vsize*self.vstep are set to self.vsize

        index = []
        for i in range (self.nvarx):
            cellmax = self.vzero[i]
            step = self.vstep[i]

            # if values grow, find the first j producing matrix 
            # value bigger than the x 
            if step > 0.0: 
                for j in range (int(self.vsize[i])):
                    cellmax += step
                    if x[i] < cellmax:
                        break
                        # if values shrink, find the first j producing matrix 
            # value lower than the x 
            else:          
                for j in range (int(self.vsize[i])):
                    cellmax += step
                    if x[i] > cellmax:
                        break
            index.append (j)

        # compute the index in the deconvoluted monodimensional vector where
        # the values of vmatrix are stored
        matrix_index = 0
        for i in range(self.nvarx):
            matrix_index += (index[i]*self.offset[i])

        return vmatrix[matrix_index]

    def load_data(self):
        ''' read the matrix, stored as a 1D or 2D table of floats, separted by ',' 
            and the metaiformation 
        '''
        #load input matrix metadata
        mmatrix_path = os.path.join(self.model_path,'mmatrix.yaml')
        with open(mmatrix_path, 'r') as f:
            mmatrix = yaml.safe_load(f)
        
        #load input matrix 
        vmatrix_path = os.path.join(self.model_path,'vmatrix.txt')
        with open(vmatrix_path) as f:
            vmatrix = np.loadtxt(f, delimiter=',')
            if len(np.shape(vmatrix))>1:
                vmatrix = vmatrix.flatten()

        return mmatrix, vmatrix

    def preprocess (self, X):
        ''' transform to customize input values, before looking into the table '''
        return X

    def postprocess (self, varray):
        ''' transform to customize output values, after they were extracted from the table 
            input is an array of np.arrays
            For simple predictions, it only contains a single value
            For simulations, it contains the low, up and mean values of the CI
        '''
        return varray

    def predict(self, X):
        ''' return a prediction obtained by looking up a table of preprocessed values
            The input X values are converted to the matrix indexes
            When all the X values have an associated error, run a simulation to estimate the
            output error 
        '''
        # obtain dimensions of X matrix
        self.nobj, self.nvarx = np.shape(X)

        # apply custom modifications to the input values
        X = self.preprocess (X)

        # load matrix and matrix metadata        
        mmatrix, vmatrix = self.load_data()

        # this is the array of predicted Y values 
        yarray = []

        # assign metainformation to every variable
        var_names = self.conveyor.getVal('var_nam')
        
        self.vloop = []
        self.vsize = []
        self.vzero = []
        self.vstep = []
        for i in var_names:
            vname = i.split(':')[1]
            if not vname in mmatrix:
                # raise Exception (f'matrix does not indexes model input. {vname} not found.')
                self.conveyor.setError(f'matrix does not indexes model input. {vname} not found.')
                return None

            self.vloop.append(mmatrix[vname][0]) # inner loop is 0, then 1, 2 etc...
            self.vsize.append(mmatrix[vname][1]) # number of bins in the matrix for this variable
            self.vzero.append(mmatrix[vname][2]) # origin (left side) of the first bin 
            self.vstep.append(mmatrix[vname][3]) # width of each bin, must the identical for all bins

        # check that the size of the vmatrix corresponds with the vsize
        mlen = 1
        for i in self.vsize:
            mlen *= i
        if int(mlen) != len(vmatrix):
            self.conveyor.setError('vmatrix size does not match metadata')
            return None

        # compute offset for each variable in sequential order
        # this means computing the factor for which each
        # variable value must be multiplied in order to identify
        # the position the linear vector representing 

        self.offset = []
        for i in range(self.nvarx):
            ioffset = 1.0
            for j in range(self.nvarx):
                if self.vloop[j]<self.vloop[i]:
                    ioffset*=self.vsize[j]
            self.offset.append(int(ioffset))

        # if all the original methods contain CI run a simulation to compute the CI for the 
        # output values and return the mean, the 5% percentil and 95% percentil of the values obtained 


        computeCI, CIparams = self.getConfidence ()
        if computeCI:
            ############################################
            ##
            ##  Compute CI
            ##
            ############################################

            CI_vals      = CIparams[0]
            zcoeff       = CIparams[1]
            cs_top_left  = CIparams[2]
            cs_top_right = CIparams[3]

            cilow = []
            ciupp = []
            cimean = []

            # make sure the random numbers are reproducible
            np.random.seed(2324)

            # Ylog = []
            for j in range (self.nobj):
                ymulti = []
                for m in range (SIMULATION_SIZE):
                    
                    # add random noise to the X array, using the CI to 
                    # estimate how wide is the distribution 
                    x = copy.copy(X[j])
                    for i in range (self.nvarx):
                        #ci range is the width of the CI
                        cirange = CI_vals[j,i*2+1] - CI_vals[j,i*2]

                        # the CI were estimated as +/- z * SE
                        sd = cirange * zcoeff[i]

                        # now we add normal random noise, with mean 0 and SD = sd
                        x[i]+=np.random.normal(0.0,sd)

                    # compute y using the noisy x
                    yy = self.lookup (x,vmatrix)
                    ymulti.append (yy)

                    # just for debug. this can help understand distribution of Y and relationships with 
                    # print (m, x, yy )

                ymulti_array = np.array(ymulti)
                
                # debug only
                # Ylog.append(ymulti)
                
                # obtain percentiles to estimate the left and right part of the CI 
                #
                # We make no assumptions about the distribution shape, but if it is skewed
                # the CI can be assymetric
                # TODO: check the distribution and apply log or other transforms when appropriate

                cilow.append (np.percentile(ymulti_array,cs_top_left*100 ,interpolation='linear'))
                ciupp.append (np.percentile(ymulti_array,cs_top_right*100 ,interpolation='linear'))
                cimean.append(np.percentile(ymulti_array,50,interpolation='linear'))
            
            # np.savetxt("Ylog.tsv", Ylog, delimiter="\t")

            cival = [cilow, ciupp, cimean]

            cival = self.postprocess (cival)

            # for i in range (len(cival[0])):
            #     print (f'{cival[0][i]:.2f} - {cival[2][i]:.2f} - {cival[1][i]:.2f}')

            self.conveyor.addVal(cival[0], 
                        'lower_limit', 
                        'Lower limit', 
                        'confidence',
                        'objs',
                        'Lower limit of the conformal prediction'
                    )

            self.conveyor.addVal(cival[1], 
                        'upper_limit', 
                        'Upper limit', 
                        'confidence',
                        'objs',
                        'Upper limit of the conformal prediction'
                    )

            # copy to yarray because this is what is returned in either case
            yarray = np.array(cival[2])

        else:

            ############################################
            ##
            ##  Compute single predictions
            ##
            ############################################

            # For each object look up in the vmatrix, by transforming the input X variables
            # into indexes and then extracting the corresponding values
            for j in range (self.nobj):
                yarray.append (self.lookup (X[j],vmatrix))

            # print (yarray)

            sval = [np.array(yarray)]
            yarray = self.postprocess(sval)[0] 


        return yarray
            