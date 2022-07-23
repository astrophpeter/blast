import math

import numpy as np
from astropy.io import fits

from .base_tasks import TransientTaskRunner
from .cutouts import download_and_save_cutouts
from .ghost import run_ghost
from .host_utils import construct_aperture
from .host_utils import do_aperture_photometry
from .host_utils import query_ned
from .host_utils import query_sdss
from .models import Aperture
from .models import AperturePhotometry
from .models import Cutout
from .prospector import build_model
from .prospector import build_obs
from .prospector import fit_model


class Ghost(TransientTaskRunner):
    """
    TaskRunner to run the GHOST matching algorithm.
    """

    def _prerequisites(self):
        """
        Only prerequisite is that the host match task is not processed.
        """
        return {"Host Match": "not processed"}

    @property
    def task_name(self):
        """
        Task status to be altered is host match.
        """
        return "Host match"

    def _failed_status_message(self):
        """
        Failed status is no GHOST match status.
        """
        return "no GHOST match"

    def _run_process(self, transient):
        """
        Run the GHOST matching algorithm.
        """
        host = run_ghost(transient)

        if host is not None:
            host.save()
            transient.host = host
            transient.save()
            status_message = "processed"
        else:
            status_message = "no ghost match"

        return status_message


class ImageDownload(TransientTaskRunner):
    """Task runner to download cutout images"""

    def _prerequisites(self):
        """
        No prerequisites
        """
        return {"Cutout download": "not processed"}

    @property
    def task_name(self):
        """
        Task status to be altered is host match.
        """
        return "Cutout download"

    def _failed_status_message(self):
        """
        Failed status is no GHOST match status.
        """
        return "failed"

    def _run_process(self, transient):
        """
        Download cutout images
        """
        download_and_save_cutouts(transient)
        return "processed"


class GlobalApertureConstruction(TransientTaskRunner):
    """Task runner to construct apertures from the cutout download"""

    def _prerequisites(self):
        """
        Need both the Cutout and Host match to be processed
        """
        return {
            "Cutout download": "processed",
            "Host Match": "processed",
            "Global aperture construction": "not processed",
        }

    @property
    def task_name(self):
        """
        Task status to be altered is host match.
        """
        return "Global aperture construction"

    def _failed_status_message(self):
        """
        Failed status if not aperture is found
        """
        return "failed"

    def _select_cutout_aperture(self, cutouts):
        """
        Select cutout for aperture
        """
        filter_names = [
            "PanSTARRS_g",
            "PanSTARRS_r",
            "PanSTARRS_i",
            "SDSS_r",
            "SDSS_i",
            "SDSS_g",
            "DES_r",
            "DES_i",
            "DES_g",
            "2MASS_H",
        ]

        choice = 0
        filter_choice = filter_names[choice]

        while not cutouts.filter(filter__name=filter_choice).exists():
            choice += 1
            filter_choice = filter_names[choice]

        return cutouts.filter(filter__name=filter_choice)

    def _run_process(self, transient):
        """Code goes here"""

        cutouts = Cutout.objects.filter(transient=transient)
        aperture_cutout = self._select_cutout_aperture(cutouts)

        image = fits.open(aperture_cutout[0].fits.name)
        aperture = construct_aperture(image, transient.host.sky_coord)

        query = {"name": f"{aperture_cutout[0].name}_global"}
        data = {
            "name": f"{aperture_cutout[0].name}_global",
            "cutout": aperture_cutout[0],
            "orientation_deg": (180 / np.pi) * aperture.theta.value,
            "ra_deg": aperture.positions.ra.degree,
            "dec_deg": aperture.positions.dec.degree,
            "semi_major_axis_arcsec": aperture.a.value,
            "semi_minor_axis_arcsec": aperture.b.value,
            "transient": transient,
            "type": "global",
        }

        self._overwrite_or_create_object(Aperture, query, data)
        return "processed"


class LocalAperturePhotometry(TransientTaskRunner):
    """Task Runner to perform local aperture photometry around host"""

    def _prerequisites(self):
        """
        Need both the Cutout and Host match to be processed
        """
        return {
            "Cutout download": "processed",
            "Local aperture photometry": "not processed",
        }

    @property
    def task_name(self):
        """
        Task status to be altered is Local Aperture photometry
        """
        return "Local aperture photometry"

    def _failed_status_message(self):
        """
        Failed status if not aperture is found
        """
        return "failed"

    def _run_process(self, transient):
        """Code goes here"""

        query = {"name__exact": f"{transient.name}_local"}
        data = {
            "name": f"{transient.name}_local",
            "orientation_deg": 0.0,
            "ra_deg": transient.sky_coord.ra.degree,
            "dec_deg": transient.sky_coord.dec.degree,
            "semi_major_axis_arcsec": 1.0,
            "semi_minor_axis_arcsec": 1.0,
            "transient": transient,
            "type": "local",
        }

        self._overwrite_or_create_object(Aperture, query, data)
        aperture = Aperture.objects.get(**query)
        cutouts = Cutout.objects.filter(transient=transient)

        for cutout in cutouts:
            image = fits.open(cutout.fits.name)

            try:
                photometry = do_aperture_photometry(
                    image, aperture.sky_aperture, cutout.filter
                )

                query = {
                    "aperture": aperture,
                    "transient": transient,
                    "filter": cutout.filter,
                }

                data = {
                    "aperture": aperture,
                    "transient": transient,
                    "filter": cutout.filter,
                    "flux": photometry["flux"],
                    "flux_error": photometry["flux_error"],
                    "magnitude": photometry["magnitude"],
                    "magnitude_error": photometry["magnitude_error"],
                }

                self._overwrite_or_create_object(AperturePhotometry, query, data)
            except Exception as e:
                print(e)
        return "processed"


class GlobalAperturePhotometry(TransientTaskRunner):
    """Task Runner to perform local aperture photometry around host"""

    def _prerequisites(self):
        """
        Need both the Cutout and Host match to be processed
        """
        return {
            "Cutout download": "processed",
            "Global aperture construction": "processed",
            "Global aperture photometry": "not processed",
        }

    @property
    def task_name(self):
        """
        Task status to be altered is Local Aperture photometry
        """
        return "Global aperture photometry"

    def _failed_status_message(self):
        """
        Failed status if not aperture is found
        """
        return "failed"

    def _run_process(self, transient):
        """Code goes here"""

        aperture = Aperture.objects.filter(transient=transient, type="global")
        cutouts = Cutout.objects.filter(transient=transient)

        for cutout in cutouts:
            image = fits.open(cutout.fits.name)

            try:
                photometry = do_aperture_photometry(
                    image, aperture[0].sky_aperture, cutout.filter
                )

                query = {
                    "aperture": aperture[0],
                    "transient": transient,
                    "filter": cutout.filter,
                }

                data = {
                    "aperture": aperture[0],
                    "transient": transient,
                    "filter": cutout.filter,
                    "flux": photometry["flux"],
                    "flux_error": photometry["flux_error"],
                    "magnitude": photometry["magnitude"],
                    "magnitude_error": photometry["magnitude_error"],
                }

                self._overwrite_or_create_object(AperturePhotometry, query, data)
            except Exception as e:
                print(e)

        return "processed"


class TransientInformation(TransientTaskRunner):
    """Task Runner to gather information about the Transient"""

    def _prerequisites(self):
        return {"Transient information": "not processed"}

    @property
    def task_name(self):
        return "Transient information"

    def _failed_status_message(self):
        """
        Failed status if not aperture is found
        """
        return "failed"

    def _run_process(self, transient):
        """Code goes here"""

        # get_dust_maps(10)
        return "processed"


class HostInformation(TransientTaskRunner):
    """Task Runner to gather host information from NED"""

    def _prerequisites(self):
        """
        Need both the Cutout and Host match to be processed
        """
        return {"Host match": "processed", "Host information": "not processed"}

    @property
    def task_name(self):
        return "Host information"

    def _failed_status_message(self):
        """
        Failed status if not aperture is found
        """
        return "failed"

    def _run_process(self, transient):
        """Code goes here"""

        host = transient.host

        galaxy_ned_data = query_ned(host.sky_coord)
        galaxy_sdss_data = query_sdss(host.sky_coord)

        status_message = "processed"

        if galaxy_sdss_data["redshift"] is not None and not math.isnan(
            galaxy_sdss_data["redshift"]
        ):
            host.redshift = galaxy_sdss_data["redshift"]
        elif galaxy_ned_data["redshift"] is not None and not math.isnan(
            galaxy_ned_data["redshift"]
        ):
            host.redshift = galaxy_ned_data["redshift"]
        else:
            status_message = "no host redshift"

        host.save()
        return status_message


class HostSEDFitting(TransientTaskRunner):
    """Task Runner to run host galaxy inference with prospector"""

    def _prerequisites(self):
        """
        Need both the Cutout and Host match to be processed
        """
        return {
            "Host match": "processed",
            "Host information": "processed",
            "Global aperture photometry": "processed",
        }

    @property
    def task_name(self):
        """
        Task status to be altered is Local Aperture photometry
        """
        return "Global host SED inference"

    def _failed_status_message(self):
        """
        Failed status if not aperture is found
        """
        return "failed"

    def _run_process(self, transient):
        """Code goes here"""
        observations = build_obs(transient, "global")
        model_components = build_model(observations)
        fitting_settings = dict(
            nlive_init=400, nested_method="rwalk", nested_target_n_effective=10000
        )
        posterior = fit_model(observations, model_components, fitting_settings)

        return "processed"
