from django.contrib import admin

from .models import Status
from .models import Task

# Register your models here.
admin.site.register(Task)
admin.site.register(Status)
