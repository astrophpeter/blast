# Utils and wrappers for the prospector SED fitting code
import numpy as np
from prospect.fitting import fit_model
from prospect.fitting import lnprobfn
from prospect.models import SpecModel
from prospect.models.templates import TemplateLibrary
from prospect.sources import CSPSpecBasis

from .models import AperturePhotometry
from .models import Filter
from .photometric_calibration import jansky_to_maggies


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

    filters, flux_maggies, flux_maggies_error = [], [], []

    for filter in Filter.objects.all():
        try:
            datapoint = photometry.get(filter=filter)
            filters.append(filter.transmission_curve())
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
        filters=filters,
    )

    return obs_data


def build_model(observations):
    """
    Construct all model components
    """

    model_params = TemplateLibrary["parametric_sfh"]
    model_params.update(TemplateLibrary["nebular"])
    model_params["zred"]["init"] = observations["redshift"]
    model = SpecModel(model_params)
    sps = CSPSpecBasis(zcontinuous=1)
    noise_model = (None, None)

    return {"model": model, "sps": sps, "noise_model": noise_model}


def fit_model(observations, model_components, fitting_kwargs):
    """Fit the model"""
    output = fit_model(
        observations,
        model_components["model"],
        model_components["sps"],
        optimize=False,
        dynesty=True,
        lnprobfn=lnprobfn,
        noise=model_components["noise_model"],
        **fitting_kwargs,
    )
    return output


def prospector_result_to_blast(prospector_output):
    return 0.0
