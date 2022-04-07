# Modelus to manage to processing of tasks for transients
from abc import ABC
from abc import abstractmethod

from django.utils import timezone

from .cutouts import download_and_save_cutouts
from .ghost import run_ghost
from .models import Status
from .models import Task
from .models import TaskRegister
from .models import Transient


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
        self.failed_status = Status.objects.get(
            message__exact=self._failed_status_message()
        )
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

    def run_process(self):
        """
        Runs task runner process.
        """
        task_register_item = self.select_register_item()

        if task_register_item is not None:
            update_status(task_register_item, self.processing_status)
            transient = task_register_item.transient

            try:
                status = self._run_process(transient)
                update_status(task_register_item, status)
            except:
                update_status(task_register_item, self.failed_status)

    @abstractmethod
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

    @abstractmethod
    def _prerequisites(self):
        """
        Task prerequisites to be implemented by child classes.

        Returns:
            prerequisites (dict): key is the name of the task, value is the task
                status.
        """
        pass

    @abstractmethod
    def _task_name(self):
        """
        Name of the task the task runner works on.

        Returns:
            task name (str): Name of the task the task runner is to work on.
        """
        pass

    @abstractmethod
    def _failed_status_message(self):
        """
        Message of the failed status.

        Returns:
            failed message (str): Name of the message of the failed status.
        """
        pass


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
            status = Status.objects.get(message__exact="processed")
        else:
            status = Status.objects.get(message__exact="no ghost match")

        return status


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
        status = Status.objects.get(message__exact="processed")
        download_and_save_cutouts(transient)
        return status


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
