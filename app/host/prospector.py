# Utils and wrappers for the prospector SED fitting code
import numpy as np
from sedpy.observate import load_filters
from sedpy.observate import Filter as SedpyFilter

import pandas as pd
from .models import AperturePhotometry
from .models import Filter
from .models import Transient
from .photometric_calibration import jansky_to_maggies
from django.conf import settings


def filter_to_sedpy_filter(filter, data_dir=settings.TRANSMISSION_CURVES_ROOT):
    """
    Converts blast filter to sedpy filter object
    """

    try:
        transmission = pd.read_csv(f'{data_dir}/{filter.name}.txt',
                                           header=None, delim_whitespace=True)
    except:
        raise ValueError('Problem loading filter transmission curve')

    wavelength, transmission = transmission[0].values,transmission[1].values
    return SedpyFilter(nick=filter.name, data=(wavelength, transmission))


def build_obs(transient, aperture_type):

    """
    This functions is required by prospector and should return
    a dictionary defined by
    https://prospect.readthedocs.io/en/latest/dataformat.html.

    """

    photometry = AperturePhotometry.objects.filter(
        transient=transient, aperture__type__exact=aperture_type
    )

    if not photometry.exists():
        raise ValueError(f"No host photometry of type {aperture_type}")

    if transient.host is None:
        raise ValueError("No host galaxy match")

    if transient.host.redshift is None:
        raise ValueError("No host galaxy redshift")

    filter_names, flux_maggies, flux_maggies_error = [], [], []

    for filter in Filter.objects.all():
        try:
            datapoint = photometry.get(filter=filter)
            filter_names.append(datapoint.kcorrect_name)
            flux_maggies.append(jansky_to_maggies(datapoint.flux))
            flux_maggies_error.append(jansky_to_maggies(datapoint.flux_error))
        except AperturePhotometry.DoesNotExist or AperturePhotometry.MultipleObjectsReturned:
            raise

    obs_data = dict(
        wavelength=None,
        spectrum=None,
        unc=None,
        redshift=transient.host.redshift,
        maggies=np.array(flux_maggies),
        maggies_unc=np.array(flux_maggies_error),
        filters=load_filters(filter_names),
    )

    return obs_data


def build_model(my, arguments):
    """
    Required by propector defined by
    https://prospect.readthedocs.io/en/latest/models.html
    """
    return 0.0


def build_sps(my, arguments):
    """
    Required by prospector defined by
    https://prospect.readthedocs.io/en/latest/usage.html
    """
    return 0.0


def build_noise(my, arguments):
    """
    Required by prospector defined by
    https://prospect.readthedocs.io/en/latest/usage.html
    """
    return 0.0
