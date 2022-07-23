#!/usr/bin/env bash

rm -r data/ghost_output/*
rm -r data/database/*
rm -r data/test_database/*
rm -r data/tns_staging/*
rm -r app/static/*
rm -r app/rabbitmq_data/*

mv data/cutout_cdn/2010ag/ data/
mv data/cutout_cdn/2010ai/ data/
mv data/cutout_cdn/2010h/ data/
rm -r data/cutout_cdn/*
mv data/2010ag/ data/cutout_cdn/
mv data/2010ai/ data/cutout_cdn/
mv data/2010h/ data/cutout_cdn/
