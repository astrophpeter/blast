from abc import ABC
from abc import abstractmethod
from time import process_time

from django.utils import timezone

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
        pass

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
    def task_initially_enabled(self):
        """Will the task be run on start up"""
        return True

    @property
    def task_function_name(self):
        return "host.tasks." + self.task_name.replace(" ", "_").lower()

    @abstractmethod
    def run_process(self):
        """
        Runs task runner process.
        """
        pass

    @property
    def task_name(self):
        """
        Name of the task the task runner works on.

        Returns:
            task name (str): Name of the task the task runner is to work on.
        """
        pass

    @property
    def task_type(self):
        pass


class TransientTaskRunner(TaskRunner):
    def __init__(self):
        """
        Initialized method which sets up the task runner.
        """
        self.processing_status = Status.objects.get(message__exact="processing")
        self.task_register = TaskRegister.objects.all()
        self.prerequisites = self._prerequisites()
        # self.task = Task.objects.get(name__exact=self.task_name)

    def find_register_items_meeting_prerequisites(self):
        """
        Finds the register items meeting the prerequisites.

        Returns:
            (QuerySet): Task register items meeting prerequisites.
        """
        task = Task.objects.get(name__exact=self.task_name)
        current_transients = Transient.objects.all()

        for task_name, status_message in self.prerequisites.items():
            task = Task.objects.get(name__exact=task_name)
            status = Status.objects.get(message__exact=status_message)

            current_transients = current_transients & Transient.objects.filter(
                taskregister__task=task, taskregister__status=status
            )

        return self.task_register.filter(
            transient__in=list(current_transients), task=task
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

    def _update_status(self, task_status, updated_status):
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
        # self.task = Task.objects.get(name__exact=self.task_name)

        task_register_item = self.select_register_item()

        if task_register_item is not None:
            self._update_status(task_register_item, self.processing_status)
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
                self._update_status(task_register_item, status)
                processing_time = round(end_time - start_time, 2)
                task_register_item.last_processing_time_seconds = processing_time
                task_register_item.save()

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
    def _failed_status_message(self):
        """
        Message of the failed status.

        Returns:
            failed message (str): Name of the message of the failed status.
        """
        pass

    @property
    def task_type(self):
        return "transient"


class SystemTaskRunner(TaskRunner):
    @property
    def task_type(self):
        return "system"


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
