import glob
import os

from astro_ghost.ghostHelperFunctions import getGHOST
from astro_ghost.ghostHelperFunctions import getTransientHosts
from astropy.coordinates import SkyCoord
from django.conf import settings

from .models import Host


def run_ghost(transient, output_dir=settings.GHOST_OUTPUT_ROOT):
    """
    Finds the information about the host galaxy given the position of the supernova.
    Parameters
    ----------
    :position : :class:`~astropy.coordinates.SkyCoord`
        On Sky position of the source to be matched.
    :name : str, default='No name'
        Name of the the object.
    Returns
    -------
    :host_information : ~astropy.coordinates.SkyCoord`
        Host position
    """
    getGHOST(real=False, verbose=1)
    transient_position = SkyCoord(
        ra=transient.ra_deg, dec=transient.dec_deg, unit="deg"
    )
    host_data = getTransientHosts(
        snCoord=[transient_position],
        snName=[transient.name],
        verbose=1,
        savepath=output_dir,
        starcut="gentle",
        # ascentMatch=False,
    )

    # clean up after GHOST...
    # dir_list = glob.glob('transients_*/*/*')
    # for dir in dir_list: os.remove(dir)

    # for level in ['*/*/', '*/']:
    #    dir_list = glob.glob('transients_' + level)
    #    for dir in dir_list: os.rmdir(dir)

    if len(host_data) == 0:
        host = None
    else:
        host = Host(
            ra_deg=host_data["raMean"][0],
            dec_deg=host_data["decMean"][0],
            name=host_data["objName"][0],
        )
    return host
