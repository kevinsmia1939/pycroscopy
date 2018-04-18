# -*- coding: utf-8 -*-
"""
Created on Thu Sep  7 21:14:25 2017

@author: Suhas Somnath, Chris Smith
"""

import sys
import numpy as np
from collections import Iterable

from .dtype_utils import contains_integers

__all__ = ['clean_string_att', 'get_aux_dset_slicing', 'make_indices_matrix', 'INDICES_DTYPE', 'VALUES_DTYPE',
           'Dimension']

if sys.version_info.major == 3:
    unicode = str

INDICES_DTYPE = np.uint32
VALUES_DTYPE = np.float32


class Dimension(object):
    def __init__(self, name, units, values):
        """
        Simple object that describes a dimension in a dataset by its name, units, and values
        Parameters
        ----------
        name : str / unicode
            Name of the dimension. For example 'Bias'
        units : str / unicode
            Units for this dimension. For example: 'V'
        values : array-like, or int
            Values over which this dimension was varied. A linearly increasing set of values will be generated if an
            integer is provided instead of an array.
        """
        if not isinstance(name, (str, unicode)):
            raise TypeError('name should be a string')
        name = name.strip()
        if len(name) < 1:
            raise ValueError('name should not be an empty string')
        if not isinstance(units, (str, unicode)):
            raise TypeError('units should be a string')
        if isinstance(values, int):
            if values < 1:
                raise ValueError('values should at least be specified as a positive integer')
            values = np.arange(values)
        if not isinstance(values, (np.ndarray, list, tuple)):
            raise TypeError('values should be array-like')
        self.name = name
        self.units = units
        self.values = values

    def __repr__(self):
        return '{} ({}) : {}'.format(self.name, self.units, self.values)


def get_aux_dset_slicing(dim_names, last_ind=None, is_spectroscopic=False):
    """
    Returns a dictionary of slice objects to help in creating region references in the position or spectroscopic
    indices and values datasets

    Parameters
    ------------
    dim_names : iterable
        List of strings denoting the names of the position axes or spectroscopic dimensions arranged in the same order
        that matches the dimensions in the indices / values dataset
    last_ind : (Optional) unsigned int, default = None
        Last pixel in the positon or spectroscopic matrix. Useful in experiments where the
        parameters have changed (eg. BEPS new data format) during the experiment.
    is_spectroscopic : bool, optional. default = True
        set to True for position datasets and False for spectroscopic datasets
    Returns
    ------------
    slice_dict : dictionary
        Dictionary of tuples containing slice objects corresponding to
        each position axis.
    """
    if not isinstance(dim_names, Iterable):
        raise TypeError('dim_names should be and Iterable')
    if not len(dim_names) > 0:
        raise ValueError('dim_names should not be empty')
    if not np.all([isinstance(x, (str, unicode)) for x in dim_names]):
        raise TypeError('dim_names should contain strings')

    slice_dict = dict()
    for spat_ind, curr_dim_name in enumerate(dim_names):
        val = (slice(last_ind), slice(spat_ind, spat_ind + 1))
        if is_spectroscopic:
            val = val[::-1]
        slice_dict[str(curr_dim_name)] = val
    return slice_dict


def make_indices_matrix(num_steps, is_position=True):
    """
    Makes an ancillary indices matrix given the number of steps in each dimension. In other words, this function builds
    a matrix whose rows correspond to unique combinations of the multiple dimensions provided.

    Parameters
    ------------
    num_steps : List / numpy array
        Number of steps in each spatial or spectral dimension
        Note that the axes must be ordered from fastest varying to slowest varying
    is_position : bool, optional, default = True
        Whether the returned matrix is meant for position (True) indices (tall and skinny) or spectroscopic (False)
        indices (short and wide)

    Returns
    --------------
    indices_matrix : 2D unsigned int numpy array
        arranged as [steps, spatial dimension]
    """
    if not isinstance(num_steps, (tuple, list, np.ndarray)):
        raise TypeError('num_steps should be a list / tuple / numpy array')
    if not contains_integers(num_steps, min_val=1 + int(len(num_steps) > 0)):
        raise ValueError('num_steps should contain integers greater than equal to 1 (empty dimension) or 2')

    num_steps = np.array(num_steps)
    spat_dims = max(1, len(np.where(num_steps > 1)[0]))

    indices_matrix = np.zeros(shape=(np.prod(num_steps), spat_dims), dtype=INDICES_DTYPE)
    dim_ind = 0

    for indx, curr_steps in enumerate(num_steps):
        if curr_steps > 1:

            part1 = np.prod(num_steps[:indx+1])

            if indx > 0:
                part2 = np.prod(num_steps[:indx])
            else:
                part2 = 1

            if indx+1 == len(num_steps):
                part3 = 1
            else:
                part3 = np.prod(num_steps[indx+1:])

            indices_matrix[:, dim_ind] = np.tile(np.floor(np.arange(part1)/part2), part3)
            dim_ind += 1

    if not is_position:
        indices_matrix = indices_matrix.T

    return indices_matrix


def clean_string_att(att_val):
    """
    Replaces any unicode objects within lists with their string counterparts to ensure compatibility with python 3.
    If the attribute is indeed a list of unicodes, the changes will be made in-place

    Parameters
    ----------
    att_val : object
        Attribute object

    Returns
    -------
    att_val : object
        Attribute object
    """
    try:
        if isinstance(att_val, Iterable):
            if type(att_val) in [unicode, str]:
                return att_val
            elif np.any([type(x) in [str, unicode, bytes, np.str_] for x in att_val]):
                return np.array(att_val, dtype='S')
        if type(att_val) == np.str_:
            return str(att_val)
        return att_val
    except TypeError:
        raise TypeError('Failed to clean: {}'.format(att_val))


def build_ind_val_matricies(unit_values, is_spectral=True):
    """
    Builds indices and values matrices using given unit values for each dimension.

    Parameters
    ----------
    unit_values : list / tuple
        Sequence of values vectors for each dimension
    is_spectral : bool (optional), default = True
        If true, returns matrices for spectroscopic datasets, else returns matrices for Position datasets

    Returns
    -------
    ind_mat : 2D numpy array
        Indices matrix
    val_mat : 2D numpy array
        Values matrix
    """
    if not isinstance(unit_values, (list, tuple)):
        raise TypeError('unit_values should be a list or tuple')
    if not np.all([np.array(x).ndim == 1 for x in unit_values]):
        raise ValueError('unit_values should only contain 1D array')
    lengths = [len(x) for x in unit_values]
    tile_size = [np.prod(lengths[x:]) for x in range(1, len(lengths))] + [1]
    rep_size = [1] + [np.prod(lengths[:x]) for x in range(1, len(lengths))]
    val_mat = np.zeros(shape=(len(lengths), np.prod(lengths)))
    ind_mat = np.zeros(shape=val_mat.shape, dtype=np.uint32)
    for ind, ts, rs, vec in zip(range(len(lengths)), tile_size, rep_size, unit_values):
        val_mat[ind] = np.tile(np.repeat(vec, rs), ts)
        ind_mat[ind] = np.tile(np.repeat(np.arange(len(vec)), rs), ts)
    if not is_spectral:
        val_mat = val_mat.T
        ind_mat = ind_mat.T
    return INDICES_DTYPE(ind_mat), VALUES_DTYPE(val_mat)


def create_spec_inds_from_vals(ds_spec_val_mat):
    """
    Create new Spectroscopic Indices table from the changes in the
    Spectroscopic Values

    Parameters
    ----------
    ds_spec_val_mat : array-like,
        Holds the spectroscopic values to be indexed

    Returns
    -------
    ds_spec_inds_mat : numpy array of uints the same shape as ds_spec_val_mat
        Indices corresponding to the values in ds_spec_val_mat

    """
    if not isinstance(ds_spec_val_mat, np.ndarray):
        raise TypeError('ds_spec_val_mat must be a numpy array')
    if ds_spec_val_mat.ndim != 2:
        raise ValueError('ds_spec_val_mat must be a 2D array arranged as [dimension, values]')

    ds_spec_inds_mat = np.zeros_like(ds_spec_val_mat, dtype=np.int32)

    """
    Find how quickly the spectroscopic values are changing in each row 
    and the order of row from fastest changing to slowest.
    """
    change_count = [len(np.where([row[i] != row[i - 1] for i in range(len(row))])[0]) for row in ds_spec_val_mat]
    change_sort = np.argsort(change_count)[::-1]

    """
    Determine everywhere the spectroscopic values change and build 
    index table based on those changed
    """
    indices = np.zeros(ds_spec_val_mat.shape[0])
    for jcol in range(1, ds_spec_val_mat.shape[1]):
        this_col = ds_spec_val_mat[change_sort, jcol]
        last_col = ds_spec_val_mat[change_sort, jcol - 1]

        """
        Check if current column values are different than those 
        in last column.
        """
        changed = np.where(this_col != last_col)[0]

        """
        If only one row changed, increment the index for that 
        column
        If more than one row has changed, increment the index for 
        the last row that changed and set all others to zero
        """
        if len(changed) == 1:
            indices[changed] += 1
        elif len(changed > 1):
            for change in changed[:-1]:
                indices[change] = 0
            indices[changed[-1]] += 1

        """
        Store the indices for the current column in the dataset
        """
        ds_spec_inds_mat[change_sort, jcol] = indices

    return ds_spec_inds_mat
