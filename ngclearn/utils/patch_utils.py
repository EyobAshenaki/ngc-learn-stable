import numpy as np
from jax import numpy as jnp
from sklearn.feature_extraction.image import extract_patches_2d

def generate_patch_set(x_batch, patch_size=(8, 8), max_patches=50, center=True): ## scikit
    """
    Generates a set of patches from an array/list of image arrays (via
    random sampling with replacement). This uses scikit-learn's patch creation
    function to generate a set of (px x py) patches.
    Note: this routine also subtracts each patch's mean from itself.

    Args:
        x_batch: the array of image arrays to sample from

        patch_size: a 2-tuple of the form (pH = patch height, pW = patch width)

        max_patches: maximum number of patches to extract/generate from source images

        center: centers each patch by subtracting the patch mean (per-patch)

    Returns:
        an array (D x (pH * pW)), where each row is a flattened patch sample
    """
    _x_batch = np.array(x_batch)
    px = py = int(np.sqrt(_x_batch.shape[1])) # get image shape of the data
    p_batch = None
    for s in range(_x_batch.shape[0]):
        xs = _x_batch[s, :]
        xs = xs.reshape(px, py)
        patches = extract_patches_2d(xs, patch_size, max_patches=max_patches)#, random_state=69)
        patches = np.reshape(patches, (len(patches), -1)) # flatten each patch in set
        if s > 0:
            p_batch = np.concatenate((p_batch,patches),axis=0)
        else:
            p_batch = patches
    if center == True:
        mu = np.mean(p_batch,axis=1,keepdims=True)
        p_batch = p_batch - mu
    return jnp.array(p_batch)

def generate_pacthify_patch_set(x_batch_, patch_size=(5, 5), center=True): ## patchify
    ## this is a patchify-specific function (only use if you have patchify installed...)
    import patchify as ptch
    """
    Generates a set of patches from an array/list of image arrays (via
    random sampling with replacement). This uses the patchify library to create
    a of non-random non-overlapping or overlapping (w/ controllable stride) patches.
    Note: this routine also subtracts each patch's mean from itself.

    Args:
        x_batch_: the array of image arrays to sample from

        patch_size: a 2-tuple of the form (pH = patch height, pW = patch width)

        center: centers each patch by subtracting the patch mean (per-patch)

    Returns:
        an array (D x (pH * pW)), where each row is a flattened patch sample
    """
    x_batch = np.array(x_batch_)
    px = py = int(np.sqrt(x_batch.shape[1])) # get image shape of the data
    x_batch = np.expand_dims(x_batch.reshape(px, py), axis=2)
    pch_x = patch_size[0]
    pch_y = patch_size[1]
    pX = np.squeeze( ptch.patchify(x_batch, (pch_x,pch_y,1), step=pch_x) ) # step = stride
    patchBatch = []
    for i in range(pX.shape[0]):
        for j in range(pX.shape[1]):
            _p = np.reshape(pX[i,j,:,:], (1, pch_x * pch_y))
            patchBatch.append(_p)
    patchBatch = jnp.concatenate(patchBatch, axis=0)
    if center == True:
        mu = np.mean(patchBatch, axis=1,keepdims=True)
        patchBatch = patchBatch - mu
    return patchBatch
