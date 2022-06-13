# Generated by Django 3.2.9 on 2022-06-10 22:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('host', '0002_auto_20220601_1914'),
    ]

    operations = [
        migrations.CreateModel(
            name='Acknowledgement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.CharField(blank=True, max_length=1000, null=True)),
                ('repository_url', models.CharField(blank=True, max_length=100, null=True)),
                ('website_url', models.CharField(blank=True, max_length=100, null=True)),
                ('paper_url', models.CharField(blank=True, max_length=100, null=True)),
                ('doi', models.CharField(blank=True, max_length=1000, null=True)),
                ('acknowledgement_text', models.CharField(blank=True, max_length=1000, null=True)),
            ],
        ),
    ]
