import datetime
import glob
import shutil

from django.conf import settings
from django.utils import timezone

from .base_tasks import initialise_all_tasks_status
from .base_tasks import SystemTaskRunner
from .models import TaskRegisterSnapshot
from .models import Transient
from .transient_name_server import get_daily_tns_staging_csv
from .transient_name_server import get_tns_credentials
from .transient_name_server import get_transients_from_tns
from .transient_name_server import tns_staging_blast_transient
from .transient_name_server import tns_staging_file_date_name
from .transient_name_server import update_blast_transient


class TNSDataIngestion(SystemTaskRunner):
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

    @property
    def task_name(self):
        return "TNS data ingestion"

    @property
    def task_initially_enabled(self):
        return False


class InitializeTransientTasks(SystemTaskRunner):
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

    @property
    def task_name(self):
        return "Initialize transient task"


class IngestMissedTNSTransients(SystemTaskRunner):
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

    @property
    def task_name(self):
        return "Ingest missed TNS transients"

    @property
    def task_initially_enabled(self):
        return False


class DeleteGHOSTFiles(SystemTaskRunner):
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

    @property
    def task_name(self):
        return "Delete GHOST files"


class SnapshotTaskRegister(SystemTaskRunner):
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

    @property
    def task_name(self):
        return "Snapshot task register"
