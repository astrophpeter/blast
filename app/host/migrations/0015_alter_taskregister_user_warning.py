# Generated by Django 3.2.9 on 2023-11-19 23:10
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ("host", "0014_taskregister_user_warning"),
    ]

    operations = [
        migrations.AlterField(
            model_name="taskregister",
            name="user_warning",
            field=models.BooleanField(default=False),
        ),
    ]