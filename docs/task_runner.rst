.. toctree::
   :maxdepth: 2

Task Runners
++++++++++++

This page walks you through how to write a TaskRunner. A TaskRunner performs a
given computational task on a transient ingested into the blast database. An
example of task that a TaskRunner would perform would be finding a Host
galaxy match for a given transient.

All TaskRunners should inherit from the TaskRunner class. This abstract base
class takes care of all the house keeping associated with running as task in
blast, allowing you to just write the task code.

There are four class methods that need to be implemented in a TaskRunner, we
will briefly run through them.

Process method
--------------

The _run_process method is where your task's code should go. This method
should contain all the necessary computations and saves to the database for your
task to be completed. It takes a Transient object as an argument and must return
a status string which indicates the status of the task after computation. As an
example, let's implement a simple task that just prints 'processing' and
then returns the processed Status.

.. code:: python

    from .models import Status

    def _run_process(transient):
        print('processing')
        return "processed"

Prerequisites
-------------

The TaskRunner needs to also specify which tasks need to be completed before it
should be run. This is done through implementing the _prerequisites method. This
function tasks no arguments and should return a dictionary with the name and
status of prerequisite task. For example, if before running your task you need
the Host match task and the Cutout download task to be completed, it would look
like this.

.. code:: python

    def _prerequisites():
        return {"Host match": "processed", "Cutout download": "processed"}

This will mean that your TaskRunner will only run on transients in the blast
database meeting the prerequisites.

Task name
---------

The TaskRunner needs to specific which task it operates on. This is done through
implementing the _task_name method. This methods takes no arguments and returns
a string which is the name of the task. Let's say we are implement a task runner
that matches a transient to a host galaxy, this TaskRunner will alter the status
of the Host match Task,

.. code:: python

    def _task_name():
        return "Host match"

Failed Status
-------------

The TaskRunner needs to specify what status happens if your _run_process code
throws and exception and fails. This is done by implementing the
_failed_status_message method.  This method takes no arguments and returns a
string which is the message of the failed status. Let's say we want the failed
status to be the Status with the message 'failed',

.. code:: python

    def _failed_status_message()
        return "failed"

Full example class
------------------

Putting this all together, the example TaskRunner class would be,

.. code:: python

    from .processing import TaskRunner
    from .models import Status

    class ExampleTaskRunner(TaskRunner):
        """An Example TaskRunner"""

        def _run_process(transient):
            print('processing')
            return "processed"

        def _prerequisites():
            return {"Host match": "processed", "Cutout download": "processed"}

        def _task_name():
            return "Host match"

        def failed_status_message()
            return "failed"
