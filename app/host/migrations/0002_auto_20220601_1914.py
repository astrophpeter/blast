# Generated by Django 3.2.9 on 2022-06-01 19:14

from django.db import migrations, models
import django.db.models.deletion
import host.models


class Migration(migrations.Migration):

    dependencies = [
        ('host', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Aperture',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ra_deg', models.FloatField()),
                ('dec_deg', models.FloatField()),
                ('name', models.CharField(blank=True, max_length=50, null=True)),
                ('orientation_deg', models.FloatField()),
                ('semi_major_axis_arcsec', models.FloatField()),
                ('semi_minor_axis_arcsec', models.FloatField()),
                ('type', models.CharField(max_length=20)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ProspectorResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('posterior', models.FileField(blank=True, null=True, upload_to=host.models.fits_file_path)),
                ('log_mass_16', models.FloatField(blank=True, null=True)),
                ('log_mass_50', models.FloatField(blank=True, null=True)),
                ('log_mass_84', models.FloatField(blank=True, null=True)),
                ('log_ssfr_16', models.FloatField(blank=True, null=True)),
                ('log_ssfr_50', models.FloatField(blank=True, null=True)),
                ('log_ssfr_84', models.FloatField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='TaskRegisterSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time', models.DateTimeField()),
                ('number_of_transients', models.IntegerField()),
                ('aggregate_type', models.CharField(max_length=100)),
            ],
        ),
        migrations.RemoveField(
            model_name='transient',
            name='catalog_photometry_status',
        ),
        migrations.RemoveField(
            model_name='transient',
            name='host_match_status',
        ),
        migrations.RemoveField(
            model_name='transient',
            name='image_download_status',
        ),
        migrations.AddField(
            model_name='cutout',
            name='name',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='filter',
            name='image_pixel_units',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='filter',
            name='magnitude_zero_point',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='host',
            name='redshift',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='taskregister',
            name='last_processing_time_seconds',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='transient',
            name='milkyway_dust_reddening',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='transient',
            name='photometric_class',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='transient',
            name='redshift',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='transient',
            name='spectroscopic_class',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='transient',
            name='tasks_initialized',
            field=models.CharField(default='False', max_length=20),
        ),
        migrations.AlterField(
            model_name='task',
            name='name',
            field=models.CharField(max_length=100),
        ),
        migrations.CreateModel(
            name='AperturePhotometry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('flux', models.FloatField()),
                ('flux_error', models.FloatField(blank=True, null=True)),
                ('magnitude', models.FloatField(blank=True, null=True)),
                ('magnitude_error', models.FloatField(blank=True, null=True)),
                ('aperture', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='host.aperture')),
                ('filter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='host.filter')),
                ('transient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='host.transient')),
            ],
        ),
        migrations.AddField(
            model_name='aperture',
            name='cutout',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='host.cutout'),
        ),
        migrations.AddField(
            model_name='aperture',
            name='transient',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='host.transient'),
        ),
    ]
