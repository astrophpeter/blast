# Modelus to manage to processing of tasks for transients
import datetime
import glob
import math
import shutil
from abc import ABC
from abc import abstractmethod
from time import process_time

import numpy as np
from astropy.io import fits
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .cutouts import download_and_save_cutouts
from .ghost import run_ghost
from .host_utils import construct_aperture
from .host_utils import do_aperture_photometry
from .host_utils import get_dust_maps
from .host_utils import query_ned
from .host_utils import query_sdss
from .models import Aperture
from .models import AperturePhotometry
from .models import Cutout
from .models import ProspectorResult
from .models import Status
from .models import Task
from .models import TaskRegister
from .models import TaskRegisterSnapshot
from .models import Transient
from .prospector import build_model
from .prospector import build_obs
from .prospector import fit_model
from .transient_name_server import get_daily_tns_staging_csv
from .transient_name_server import get_tns_credentials
from .transient_name_server import get_transients_from_tns
from .transient_name_server import tns_staging_blast_transient
from .transient_name_server import tns_staging_file_date_name
from .transient_name_server import update_blast_transient


class TaskRunner(ABC):
    """
    Abstract base class for a task runner.

    Attributes:
        processing_status (models.Status): Status of the task while runner is
            running a task.
        task_register (model.TaskRegister): Register of task for the runner to
            process.
        failed_status (model.Status): Status of the task is if the runner fails.
        prerequisites (dict): Prerequisite tasks and statuses required for the
            runner to process.
        task (str): Name of the task the runner alters the status of.
    """

    def __init__(self):
        """
        Initialized method which sets up the task runner.
        """
        self.processing_status = Status.objects.get(message__exact="processing")
        self.task_register = TaskRegister.objects.all()
        self.prerequisites = self._prerequisites()
        self.task = Task.objects.get(name__exact=self._task_name())

    def find_register_items_meeting_prerequisites(self):
        """
        Finds the register items meeting the prerequisites.

        Returns:
            (QuerySet): Task register items meeting prerequisites.
        """

        current_transients = Transient.objects.all()

        for task_name, status_message in self.prerequisites.items():
            task = Task.objects.get(name__exact=task_name)
            status = Status.objects.get(message__exact=status_message)

            current_transients = current_transients & Transient.objects.filter(
                taskregister__task=task, taskregister__status=status
            )

        return self.task_register.filter(
            transient__in=list(current_transients), task=self.task
        )

    def _select_highest_priority(self, register):
        """
        Select highest priority task by finding the one with the oldest
        transient timestamp.

        Args:
            register (QuerySet): register of tasks to select from.
        Returns:
            register item (model.TaskRegister): highest priority register item.
        """
        return register.order_by("transient__public_timestamp")[0]

    def select_register_item(self):
        """
        Selects register item to be processed by task runner.

        Returns:
            register item (models.TaskRegister): returns item is one exists,
                returns None otherwise.
        """
        register = self.find_register_items_meeting_prerequisites()
        return self._select_highest_priority(register) if register.exists() else None

    def _get_status(self, status_message):
        return 0.0

    def _overwrite_or_create_object(self, model, unique_object_query, object_data):
        """
        Overwrites or creates new objects in the blast database.

        Parameters
        ----------
        model: blast model of the object that needs to be updated
        unique_object_query: query to be passed to model.objects.get that will
            uniquely identify the object of interest
        object_data: data to be saved or over written for the object.
        Returns
        -------
        None

        """

        try:
            object = model.objects.get(**unique_object_query)
            object.delete()
            model.objects.create(**object_data)
        except model.DoesNotExist:
            model.objects.create(**object_data)

    @property
    def task_frequency_seconds(self):
        return 60.0

    @property
    def task_function_name(self):
        return "host.tasks." + self._task_name().replace(" ", "_").lower()

    def run_process(self):
        """
        Runs task runner process.
        """
        task_register_item = self.select_register_item()

        if task_register_item is not None:
            update_status(task_register_item, self.processing_status)
            transient = task_register_item.transient

            start_time = process_time()
            try:
                status_message = self._run_process(transient)
            except:
                status_message = self._failed_status_message()
                raise
            finally:
                end_time = process_time()
                status = Status.objects.get(message__exact=status_message)
                update_status(task_register_item, status)
                processing_time = round(end_time - start_time, 2)
                task_register_item.last_processing_time_seconds = processing_time
                task_register_item.save()

    def _run_process(self, transient):
        """
        Run process function to be implemented by child classes.

        Args:
            transient (models.Transient): transient for the task runner to
                process
        Returns:
            runner status (models.Status): status of the task after the task
                runner has completed.
        """
        pass

    def _prerequisites(self):
        """
        Task prerequisites to be implemented by child classes.

        Returns:
            prerequisites (dict): key is the name of the task, value is the task
                status.
        """
        pass

    def _task_name(self):
        """
        Name of the task the task runner works on.

        Returns:
            task name (str): Name of the task the task runner is to work on.
        """
        pass

    def _failed_status_message(self):
        """
        Message of the failed status.

        Returns:
            failed message (str): Name of the message of the failed status.
        """
        pass

    def celery_task(self):
        """
        Returns the shared celery task
        """

        @shared_task
        def task():
            self.run_process()

        return task


class GhostRunner(TaskRunner):
    """
    TaskRunner to run the GHOST matching algorithm.
    """

    def _prerequisites(self):
        """
        Only prerequisite is that the host match task is not processed.
        """
        return {"Host Match": "not processed"}

    def _task_name(self):
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


class ImageDownloadRunner(TaskRunner):
    """Task runner to dowload cutout images"""

    def _prerequisites(self):
        """
        No prerequisites
        """
        return {"Cutout download": "not processed"}

    def _task_name(self):
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


class GlobalApertureConstructionRunner(TaskRunner):
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

    def _task_name(self):
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


class LocalAperturePhotometry(TaskRunner):
    """Task Runner to perform local aperture photometry around host"""

    def _prerequisites(self):
        """
        Need both the Cutout and Host match to be processed
        """
        return {
            "Cutout download": "processed",
            "Local aperture photometry": "not processed",
        }

    def _task_name(self):
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


class GlobalAperturePhotometry(TaskRunner):
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

    def _task_name(self):
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


class TransientInformation(TaskRunner):
    """Task Runner to gather information about the Transient"""

    def _prerequisites(self):
        return {"Transient information": "not processed"}

    def _task_name(self):
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


class HostInformation(TaskRunner):
    """Task Runner to gather host information from NED"""

    def _prerequisites(self):
        """
        Need both the Cutout and Host match to be processed
        """
        return {"Host match": "processed", "Host information": "not processed"}

    def _task_name(self):
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


class HostSEDFitting(TaskRunner):
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

    def _task_name(self):
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


class TNSDataIngestion(TaskRunner):
    def __init__(self):
        pass

    def run_process(self, interval_minutes=100):
        now = timezone.now()
        time_delta = datetime.timedelta(minutes=interval_minutes)
        tns_credentials = get_tns_credentials()
        recent_transients = get_transients_from_tns(
            now - time_delta, tns_credentials=tns_credentials
        )
        saved_transients = Transient.objects.all()

        for transient in recent_transients:
            try:
                saved_transients.get(name__exact=transient.name)
            except Transient.DoesNotExist:
                transient.save()

    def _task_name(self):
        return "TNS data ingestion"


class InitializeTransientTasks(TaskRunner):
    def __init__(self):
        pass

    def run_process(self):
        """
        Initializes all task in the database to not processed for new transients.
        """

        uninitialized_transients = Transient.objects.filter(
            tasks_initialized__exact="False"
        )
        for transient in uninitialized_transients:
            initialise_all_tasks_status(transient)
            transient.tasks_initialized = "True"
            transient.save()

    def _task_name(self):
        return "Initialize transient task"


class IngestMissedTNSTransients(TaskRunner):
    def __init__(self):
        pass

    def run_process(self):
        """
        Gets missed transients from tns and update them using the daily staging csv
        """
        yesterday = timezone.now() - datetime.timedelta(days=1)
        date_string = tns_staging_file_date_name(yesterday)
        data = get_daily_tns_staging_csv(
            date_string,
            tns_credentials=get_tns_credentials(),
            save_dir=settings.TNS_STAGING_ROOT,
        )
        saved_transients = Transient.objects.all()

        for _, transient in data.iterrows():
            # if transient exists update it
            try:
                blast_transient = saved_transients.get(name__exact=transient["name"])
                update_blast_transient(blast_transient, transient)
            # if transient does not exist add it
            except Transient.DoesNotExist:
                blast_transient = tns_staging_blast_transient(transient)
                blast_transient.save()

    def _task_name(self):
        return "Ingest missed TNS transients"


class DeleteGHOSTFiles(TaskRunner):
    def __init__(self):
        pass

    def run_process(self):
        """
        Removes GHOST files
        """
        dir_list = glob.glob("transients_*/")

        for dir in dir_list:
            try:
                shutil.rmtree(dir)
            except OSError as e:
                print("Error: %s : %s" % (dir, e.strerror))

        dir_list = glob.glob("quiverMaps/")

        for dir in dir_list:
            try:
                shutil.rmtree(dir)
            except OSError as e:
                print("Error: %s : %s" % (dir, e.strerror))

    def _task_name(self):
        return "Delete GHOST files"


class SnapshotTaskRegister(TaskRunner):
    def __init__(self):
        pass

    def run_process(self, interval_minutes=100):
        """
        Takes snapshot of task register for diagnostic purposes.
        """
        transients = Transient.objects.all()
        total, completed, waiting, not_completed = 0, 0, 0, 0

        for transient in transients:
            total += 1
            if transient.progress == 100:
                completed += 1
            if transient.progress == 0:
                waiting += 1
            if transient.progress < 100:
                not_completed += 1

        now = timezone.now()

        for aggregate, label in zip(
            [not_completed, total, completed, waiting],
            ["not completed", "total", "completed", "waiting"],
        ):
            TaskRegisterSnapshot.objects.create(
                time=now, number_of_transients=aggregate, aggregate_type=label
            )

    def _task_name(self):
        return "Snapshot task register"


def update_status(task_status, updated_status):
    """
    Update the processing status of a task.

    Parameters:
        task_status (models.TaskProcessingStatus): task processing status to be
            updated.
        updated_status (models.Status): new status to update the task with.
    Returns:
        None: Saves the new updates to the backend.
    """
    task_status.status = updated_status
    task_status.last_modified = timezone.now()
    task_status.save()


def initialise_all_tasks_status(transient):
    """
    Set all available tasks for a transient to not processed.

    Parameters:
        transient (models.Transient): Transient to have all of its task status
            initialized.
    Returns:
        None: Saves the new updates to the backend.
    """
    tasks = Task.objects.all()
    not_processed = Status.objects.get(message__exact="not processed")

    for task in tasks:
        task_status = TaskRegister(task=task, transient=transient)
        update_status(task_status, not_processed)
