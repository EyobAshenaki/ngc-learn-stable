"""
Copyright (C) 2021 Alexander G. Ororbia II - All Rights Reserved
You may use, distribute and modify this code under the
terms of the BSD 3-clause license.

You should have received a copy of the BSD 3-clause license with
this file. If not, please write to: ago@cs.rit.edu
"""

import os
import sys, getopt, optparse
import pickle
import tensorflow as tf
import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
#cmap = plt.cm.jet

import ngclearn.utils.io_utils as io_utils
import ngclearn.utils.transform_utils as transform

"""
################################################################################
Demo/Tutorial #4 File:
Visualizes the filters of a trained dictionary/sparse coding model.
Loads in NGC from filename "model_fname" and saves a filter plot visualization
to "output_dir".

Usage:
$ python viz_filters.py --model_fname=/path/to/modelN.ngc --output_dir=/path/to/output_dir/

@author Alexander Ororbia
################################################################################
"""

### specify output directory and model filename ###
output_dir = "gncn_t1_sc_cauchy/"
model_fname = "gncn_t1_sc_cauchy/model0.ngc"
# read in configuration file and extract necessary simulation variables/constants
options, remainder = getopt.getopt(sys.argv[1:], '', ["model_fname=","output_dir="])
for opt, arg in options:
    if opt in ("--model_fname"):
        model_fname = arg.strip()
    elif opt in ("--output_dir"):
        output_dir = arg.strip()

### load in NGC model ###
model = io_utils.deserialize(model_fname)
x_dim = model.ngc_model.getNode("z0").dim
px = py = int(np.sqrt(x_dim)) #16

with tf.device('/CPU:0'):
    ### retrieve the dictionary ###
    W1 = ( model.ngc_model.cables.get("z1-to-mu0_dense").W )
    print(W1.shape)

    n_viz_filters = 100 #W1.shape[0]
    n_rows = 10 # num rows of filters to plot
    n_cols = 10 # num columns of filters to plot

    # plot the dictionary atoms
    fig = plt.figure(figsize=(8, 8))
    plt.subplots_adjust(hspace=0.1, wspace=0.1)
    for i in range(n_viz_filters):
        plt.subplot(n_rows, n_cols, i+1)
        filter = W1[i, :]
        #filter = transform.normalize_image(filter.numpy())
        plt.imshow(np.reshape(filter, (px, py)), cmap=plt.cm.bone, interpolation='nearest')
        plt.axis("off")
    fig.suptitle("Receptive fields", fontsize=20)
    plt.subplots_adjust(top=0.9)
    plt.savefig("{0}filters.jpg".format(output_dir))
    #plt.show()