from constants import UpdateDataMode
import numpy as np


def data_updater(old_data, new_data, mode, idx=None, axes=(0,)):
    oshp = old_data.shape
    nshp = new_data.shape

    #new_data = np.asarray(new_data)
    if mode == UpdateDataMode.REPLACE:
        if oshp==nshp:
            old_data[:] = new_data[:]
            return old_data
        else:
            return new_data

    elif old_data.ndim != new_data.ndim:
        raise ValueError('Dimensions dont match.')

    elif mode == UpdateDataMode.DEFAULT:
        raise ValueError('Data updater has no default mode.')

    elif mode == UpdateDataMode.BYINDEX:
        if idx is None:
            raise ValueError('No indexes for new data given.')
        try:
            old_data[idx] = new_data
        except:
            raise ValueError('Indexes dont match new data.')
    else:
        snew = nshp[axes]
        # Count positions along the index axis where
        # none of the numbers in the data axes are nan
        daxes = tuple(i for i in range(old_data.ndim) if i != ax)
        if daxes:
            sold = oshp[ax] - np.all(np.isnan(old_data), axis=daxes).sum()
        else:
            sold = oshp[ax] - np.all(np.isnan(old_data)).sum()

        sarr = oshp[ax]
        slices = [slice(None)]*old_data.ndim

        if mode == UpdateDataMode.ROLLING:
            if snew > sarr:
                slices[ax] = slice(-sarr,sarr)
                old_data[:] = new_data[slices]

            elif snew + sold >= sarr:
                slices[ax] = slice(max(0, sold - snew),-snew)
                slices2 = list(slices)
                slices2[ax] = slice(-snew,sarr)
                old_data[slices] = old_data[slices2]
                old_data[slices2] = new_data
            else:
                old_data[sold:sold + snew] = new_data
        elif mode == UpdateDataMode.LOOPING:
            if snew > sarr:
                slices[ax] =  slice(-sarr,snew)
                old_data[:] = new_data[slices]
            elif snew + sold > sarr:
                slices2 = list(slices)
                slices3 = list(slices)
                slices4 = list(slices)
                slices[ax] = slice(sold, sarr)
                slices2[ax] = slice(0,sarr-sold)
                slices3[ax] = slice(0,snew+sold-sarr)
                slices4[ax] = slice(sarr-sold, new_data.shape[ax])

                old_data[slices] = new_data[slices2]
                old_data[slices3] = new_data[slices4]
            else:
                slices[ax] = slice(sold, sold+snew)
                old_data[slices] = new_data

    return old_data