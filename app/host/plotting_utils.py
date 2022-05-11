import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
from bokeh.embed import components
from bokeh.layouts import gridplot
from bokeh.models import Circle
from bokeh.models import ColumnDataSource
from bokeh.models import Cross
from bokeh.models import Ellipse
from bokeh.models import Grid
from bokeh.models import LinearAxis
from bokeh.models import LogColorMapper
from bokeh.models import Plot
from bokeh.models import Scatter
from bokeh.plotting import figure
from host.catalog_photometry import filter_information
from host.host_utils import survey_list
from astropy.visualization import PercentileInterval, AsinhStretch


from .models import Aperture

def scale_image(image_data):

    transform = AsinhStretch() + PercentileInterval(99.5)
    scaled_data = transform(image_data)
    
    return scaled_data

def plot_image(image_data, figure):

    image_data = np.nan_to_num(image_data, nan=0)  # )=np.amin(image_data))
    image_data = image_data + abs(np.amin(image_data)) + 0.1

    scaled_image = scale_image(image_data)
    figure.image(image=[scaled_image])
    #color_mapper = LogColorMapper(palette="Greys256")
    figure.image(
        image=[scaled_image],
        x=0,
        y=0,
        dw=len(image_data),
        dh=len(image_data),
        #color_mapper=color_mapper,
        level="image",
    )


def plot_position(object, wcs, plotting_kwargs=None, plotting_func=None):
    """
    Plot position of object on a cutout.
    """
    obj_ra, obj_dec = object.ra_deg, object.dec_deg
    sky_position = SkyCoord(ra=obj_ra, dec=obj_dec, unit="deg")
    x_pixel, y_pixel = wcs.world_to_pixel(sky_position)
    plotting_func([x_pixel], [y_pixel], **plotting_kwargs)
    return None


def plot_aperture(figure, aperture, wcs, plotting_kwargs=None):
    aperture = aperture.to_pixel(wcs)
    theta_rad = (np.pi/2.0) - (np.pi/180) * aperture.theta
    x, y = aperture.positions
    plot_dict = {"x": x, "y": y, "width": aperture.a, "height": aperture.b,
                 "angle": theta_rad, "fill_color": "#cab2d6", "fill_alpha": 0.1}
    plot_dict = {**plot_dict, **plotting_kwargs}
    figure.ellipse(**plot_dict)
    return figure


def plot_image_grid(image_dict, apertures=None):

    figures = []
    for survey, image in image_dict.items():
        fig = figure(
            title=survey,
            x_axis_label="",
            y_axis_label="",
            plot_width=1000,
            plot_height=1000,
        )
        fig = plot_image(fig, image)
        if apertures is not None:
            aperture = apertures.get(survey)
            if aperture is not None:
                wcs = WCS(image[0].header)
                aperture = apertures[survey].to_pixel(wcs)
                fig = plot_aperture(fig, aperture)
        figures.append(fig)

    plot = gridplot(figures, ncols=3, width=400, height=400)
    script, div = components(plot)
    return {"bokeh_cutout_script": script, "bokeh_cutout_div": div}


def plot_cutout_image(cutout=None, transient=None, global_aperture=None,
                      local_aperture=None):

    title = cutout.filter if cutout is not None else "No cutout selected"
    fig = figure(
        title=f"{title}",
        x_axis_label="",
        y_axis_label="",
        plot_width=700,
        plot_height=700,
    )

    fig.axis.visible = False
    fig.xgrid.visible = False
    fig.ygrid.visible = False

    if cutout is not None:
        with fits.open(cutout.fits.name) as fits_file:
            image_data = fits_file[0].data
            wcs = WCS(fits_file[0].header)

        transient_kwargs = {
            "legend_label": f"{transient.name}",
            "size": 30,
            "line_width": 2,
        }
        plot_position(
            transient, wcs, plotting_kwargs=transient_kwargs, plotting_func=fig.cross
        )

        if transient.host is not None:
            host_kwargs = {
                "legend_label": f"Host: {transient.host.name}",
                "size": 25,
                "line_width": 2,
                "line_color": "red",
            }
            plot_position(
                transient.host, wcs, plotting_kwargs=host_kwargs, plotting_func=fig.x
            )
        if global_aperture.exists():
            filter_name = global_aperture[0].cutout.filter.name
            plot_aperture(fig, global_aperture[0].sky_aperture, wcs,
                          plotting_kwargs={"fill_alpha": 0.1,"line_color":"green",
                                           "legend_label": f'Global Aperture ({filter_name})'})

        if local_aperture.exists():
            plot_aperture(fig, local_aperture[0].sky_aperture, wcs,
                          plotting_kwargs={"fill_alpha": 0.1,"line_color":"blue",
                                           "legend_label": "Local Aperture"})

    else:
        image_data = np.zeros((500, 500))

    plot_image(image_data, fig)
    script, div = components(fig)
    return {"bokeh_cutout_script": script, "bokeh_cutout_div": div}


def plot_catalog_sed(photometry_table):
    """
    Plot SED from available catalog data
    """
    catalogs = survey_list("host/data/catalog_metadata.yml")
    filter_info = [filter_information(catalog) for catalog in catalogs]

    fig = figure(
        title="Spectral energy distribution",
        width=700,
        height=400,
        min_border=0,
        toolbar_location=None,
        x_axis_type="log",
        x_axis_label="Wavelength [micro-m]",
        y_axis_label="Magnitude",
    )

    wavelengths, mags, mag_errors = [], [], []

    for catalog, data in catalog_dict.items():
        filter_data = [filter for filter in filter_info if filter["name"] == catalog][0]
        wavelengths.append(filter_data["WavelengthEff"] * 0.0001)
        mags.append(data["mag"])
        mag_errors.append((data["mag_error"]))

    fig = plot_errorbar(fig, wavelengths, mags, yerr=mag_errors)

    # xaxis = LinearAxis()
    # figure.add_layout(xaxis, 'below')

    # yaxis = LinearAxis()
    # fig.add_layout(yaxis, 'left')

    # fig.add_layout(Grid(dimension=0, ticker=xaxis.ticker))
    # fig.add_layout(Grid(dimension=1, ticker=yaxis.ticker))
    script, div = components(fig)
    return {"bokeh_sed_script": script, "bokeh_sed_div": div}


def plot_errorbar(
    figure, x, y, xerr=None, yerr=None, color="red", point_kwargs={}, error_kwargs={}
):
    """
    Plot data points with error bars on a bokeh plot
    """
    figure.circle(x, y, color=color, **point_kwargs)

    if xerr:
        x_err_x = []
        x_err_y = []
        for px, py, err in zip(x, y, xerr):
            x_err_x.append((px - err, px + err))
            x_err_y.append((py, py))
        figure.multi_line(x_err_x, x_err_y, color=color, **error_kwargs)

    if yerr:
        y_err_x = []
        y_err_y = []
        for px, py, err in zip(x, y, yerr):
            y_err_x.append((px, px))
            y_err_y.append((py - err, py + err))
        figure.multi_line(y_err_x, y_err_y, color=color, **error_kwargs)
    return figure


def plot_sed(figure, photometry_dict):
    """
    Plot photometry on SED
    """
