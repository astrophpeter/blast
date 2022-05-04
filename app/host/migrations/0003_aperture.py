# Generated by Django 3.2.9 on 2022-05-03 17:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('host', '0002_auto_20220302_0126'),
    ]

    operations = [
        migrations.CreateModel(
            name='Aperture',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ra_deg', models.FloatField()),
                ('dec_deg', models.FloatField()),
                ('orientation', models.FloatField()),
                ('semi_major_axis_arcsec', models.FloatField()),
                ('semi_minor_axis_arcsec', models.FloatField()),
                ('type', models.CharField(max_length=20)),
                ('filter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='host.filter')),
                ('host', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='host.host')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]