# Generated by Django 3.2.9 on 2022-10-30 18:10
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ("host", "0009_alter_aperturephotometry_flux"),
    ]

    operations = [
        migrations.AddField(
            model_name="aperturephotometry",
            name="is_validated",
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="filter",
            name="image_fwhm_arcsec",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
