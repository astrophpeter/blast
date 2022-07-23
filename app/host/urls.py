import os

from django.urls import path

from . import views

base_path = os.environ.get("BASE_PATH", "").strip("/")
if base_path != "":
    base_path = f"""{base_path}/"""
urlpatterns = [
    path(f"""{base_path}transients/""", views.transient_list),
    path(f"""{base_path}analytics/""", views.analytics),
    path(f"""{base_path}transients/<slug:slug>/""", views.results),
    path(f"""{base_path}acknowledgements/""", views.acknowledgements),
    path(f"""{base_path}""", views.home),
    path(f"""{base_path}flower/""", views.flower_view),
]
