from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse
<<<<<<< HEAD
from django.contrib.auth.mixins import UserPassesTestMixin
from revproxy.views import ProxyView
from django.urls import re_path
=======
<<<<<<< HEAD
from django.shortcuts import render
=======
from django.contrib.auth.mixins import UserPassesTestMixin
from revproxy.views import ProxyView
from django.urls import re_path
>>>>>>> 4ecb7bc (factoring out .env)
>>>>>>> prospector_rebase

from .forms import ImageGetForm
from .forms import TransientSearchForm
from .models import Acknowledgement
from .models import Aperture
from .models import AperturePhotometry
from .models import Cutout
from .models import Filter
from .models import TaskRegisterSnapshot
from .models import Transient
from .plotting_utils import plot_cutout_image
from .plotting_utils import plot_pie_chart
from .plotting_utils import plot_sed
from .plotting_utils import plot_timeseries


def transient_list(request):
    transients = Transient.objects.all()

    if request.method == "POST":
        form = TransientSearchForm(request.POST)

        if form.is_valid():
            name = form.cleaned_data["name"]
            if name != "all":
                transients = Transient.objects.filter(name__contains=name)
    else:
        form = TransientSearchForm()

    transients = transients.order_by("-public_timestamp")[:100]

    context = {"transients": transients, "form": form}
    return render(request, "transient_list.html", context)


def analytics(request):

    analytics_results = {}

    for aggregate in ["total", "not completed", "completed", "waiting"]:

        transients = TaskRegisterSnapshot.objects.filter(
            aggregate_type__exact=aggregate
        )
        transients_ordered = transients.order_by("-time")

        if transients_ordered.exists():
            transients_current = transients_ordered[0]
        else:
            transients_current = None

        analytics_results[
            f"{aggregate}_transients_current".replace(" ", "_")
        ] = transients_current
        bokeh_processing_context = plot_timeseries()

    return render(
        request, "analytics.html", {**analytics_results, **bokeh_processing_context}
    )


def results(request, slug):
    transients = Transient.objects.all()
    transient = transients.get(name__exact=slug)

    global_aperture = Aperture.objects.filter(type__exact="global", transient=transient)
    local_aperture = Aperture.objects.filter(type__exact="local", transient=transient)
    local_aperture_photometry = AperturePhotometry.objects.filter(
        transient=transient, aperture__type__exact="local"
    )
    global_aperture_photometry = AperturePhotometry.objects.filter(
        transient=transient, aperture__type__exact="global"
    )

    all_cutouts = Cutout.objects.filter(transient__name__exact=slug)
    filters = [cutout.filter.name for cutout in all_cutouts]
    all_filters = Filter.objects.all()

    filter_status = {
        filter_.name: ("yes" if filter_.name in filters else "no")
        for filter_ in all_filters
    }

    if request.method == "POST":
        form = ImageGetForm(request.POST, filter_choices=filters)
        if form.is_valid():
            filter = form.cleaned_data["filters"]
            cutout = all_cutouts.filter(filter__name__exact=filter)[0]
    else:
        cutout = None
        form = ImageGetForm(filter_choices=filters)

    bokeh_context = plot_cutout_image(
        cutout=cutout,
        transient=transient,
        global_aperture=global_aperture,
        local_aperture=local_aperture,
    )
    bokeh_sed_local_context = plot_sed(
        aperture_photometry=local_aperture_photometry, type="local"
    )
    bokeh_sed_global_context = plot_sed(
        aperture_photometry=global_aperture_photometry, type="global"
    )

    if local_aperture.exists():
        local_aperture = local_aperture[0]
    else:
        local_aperture = None

    if global_aperture.exists():
        global_aperture = global_aperture[0]
    else:
        global_aperture = None

    context = {
        **{
            "transient": transient,
            "form": form,
            "local_aperture_photometry": local_aperture_photometry,
            "global_aperture_photometry": global_aperture_photometry,
            "filter_status": filter_status,
            "local_aperture": local_aperture,
            "global_aperture": global_aperture,
        },
        **bokeh_context,
        **bokeh_sed_local_context,
        **bokeh_sed_global_context,
    }

    return render(request, "results.html", context)


def acknowledgements(request):
    context = {"acknowledgements": Acknowledgement.objects.all()}
    return render(request, "acknowledgements.html", context)


def home(request):

    # analytics_results = {}

    # for aggregate in ["total", "not completed", "completed", "waiting"]:

    #    transients = TaskRegisterSnapshot.objects.filter(
    #        aggregate_type__exact=aggregate
    #    )
    #    transients_ordered = transients.order_by("-time")

    #    if transients_ordered.exists():
    #        transients_current = transients_ordered[0]
    #    else:
    #        transients_current = None

    #    analytics_results[
    #        f"{aggregate}_transients_current".replace(" ", "_")
    #    ] = transients_current
    # bokeh_processing_context = plot_timeseries()

    # bokeh_processing_context =  plot_pie_chart(analytics_results)

    return render(
        request, "index.html"
    )  # , #{**analytics_results, **bokeh_processing_context}
    # )


# @user_passes_test(lambda u: u.is_staff and u.is_superuser)
def flower_view(request):
    """passes the request back up to nginx for internal routing"""
    response = HttpResponse()
    path = request.get_full_path()
    path = path.replace('flower', 'flower-internal', 1)
    response['X-Accel-Redirect'] = path
    return response





class FlowerProxyView(UserPassesTestMixin, ProxyView):
    # `flower` is Docker container, you can use `localhost` instead
    upstream = 'http://{}:{}'.format('flower', 8888)
    url_prefix = 'flower'
    rewrite = (
        (r'^/{}$'.format(url_prefix), r'/{}/'.format(url_prefix)),
     )

    def test_func(self):
        return self.request.user.is_superuser

    @classmethod
    def as_url(cls):
        return re_path(r'^(?P<path>{}.*)$'.format(cls.url_prefix), cls.as_view())
