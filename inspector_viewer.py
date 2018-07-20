"""
Colormap of a scalar value field with cross sections that can be animated

A complex example showing interaction between a Traits-based interactive model,
interactive plot parameters, and multiple Chaco components.

Renders a colormapped image of a scalar value field, and a cross section
chosen by a line interactor.

Animation must be disabled (unchecked) before the model can be edited.
"""

# Standard library imports
from optparse import OptionParser
import sys
import random

# Major library imports
from numpy import array, linspace, meshgrid, nanmin, nanmax, errstate
import numpy as np
# Enthought library imports
from chaco.api import ArrayPlotData, ColorBar, ContourLinePlot, \
    ContourPolyPlot, DataRange1D, VPlotContainer, \
    DataRange2D, GridMapper, GridDataSource, \
    HPlotContainer, ImageData, LinearMapper, \
    OverlayPlotContainer, Plot, PlotAxis
from chaco import default_colormaps
from enable.component_editor import ComponentEditor
from chaco.tools.api import LineInspector, PanTool, ZoomTool
from traits.api import Array, Callable, CFloat, CInt, Enum, Event, Float, \
    HasTraits, Int, Instance, Str, Trait, on_trait_change, Button, Bool, \
    DelegatesTo
from traitsui.api import Group, HGroup, Item, View, UItem, spring

from pyface.timer.api import Timer

# Remove the most boring colormaps from consideration:
colormaps = list(default_colormaps.color_map_name_dict.keys())
for boring in 'bone gray yarg gist_gray gist_yarg Greys'.split():
    colormaps.remove(boring)



class PlotUI(HasTraits):
    # container for all plots
    container = Instance(HPlotContainer)

    # Plot components within this container:
    polyplot = Instance(ContourPolyPlot)
    lineplot = Instance(ContourLinePlot)
    cross_plot = Instance(Plot)
    cross_plot2 = Instance(Plot)
    colorbar = Instance(ColorBar)

    # plot data
    pd = Instance(ArrayPlotData)
    minz = Float(0)
    maxz = Float(1)
    # view options
    num_levels = Int(15)
    colormap = Enum(colormaps)

    # Traits view definitions:
    traits_view = View(
        Group(Item('container', editor=ComponentEditor(size=(800, 600)))),
        resizable=True)

    plot_edit_view = View(
        Group(Item('num_levels'),
              Item('colormap')),
        buttons=["OK", "Cancel"])

    # ---------------------------------------------------------------------------
    # Private Traits
    # ---------------------------------------------------------------------------

    _image_index = Instance(GridDataSource)
    _image_value = Instance(ImageData)

    _cmap = Trait(default_colormaps.jet, Callable)

    # ---------------------------------------------------------------------------
    # Public View interface
    # ---------------------------------------------------------------------------

    def __init__(self, *args, **kwargs):
        super(PlotUI, self).__init__(*args, **kwargs)
        # FIXME: 'with' wrapping is temporary fix for infinite range in initial
        # color map, which can cause a distracting warning print. This 'with'
        # wrapping should be unnecessary after fix in color_mapper.py.
        with errstate(invalid='ignore'):
            self.create_plot()

    def create_plot(self):

        # Create the mapper, etc
        self._image_index = GridDataSource(array(range(100)),
                                           array(range(100)),
                                           sort_order=("ascending", "ascending"))

        image_index_range = DataRange2D(self._image_index)
        self._image_index.on_trait_change(self._metadata_changed,
                                          "metadata_changed")

        self._image_value = ImageData(data=array(np.random.random((100,100))), value_depth=1)
        image_value_range = DataRange1D(self._image_value)

        # Create the contour plots
        self.polyplot = ContourPolyPlot(index=self._image_index,
                                        value=self._image_value,
                                        index_mapper=GridMapper(range=
                                                                image_index_range),
                                        color_mapper= \
                                            self._cmap(image_value_range),
                                        levels=self.num_levels)

        self.lineplot = ContourLinePlot(index=self._image_index,
                                        value=self._image_value,
                                        index_mapper=GridMapper(range=
                                                                self.polyplot.index_mapper.range),
                                        levels=self.num_levels)

        # Add a left axis to the plot
        left = PlotAxis(orientation='left',
                        title="y",
                        mapper=self.polyplot.index_mapper._ymapper,
                        component=self.polyplot)
        self.polyplot.overlays.append(left)

        # Add a bottom axis to the plot
        bottom = PlotAxis(orientation='bottom',
                          title="x",
                          mapper=self.polyplot.index_mapper._xmapper,
                          component=self.polyplot)
        self.polyplot.overlays.append(bottom)

        # Add some tools to the plot
        self.polyplot.tools.append(PanTool(self.polyplot,
                                           constrain_key="shift"))
        self.polyplot.overlays.append(ZoomTool(component=self.polyplot,
                                               tool_mode="box", always_on=False))
        self.polyplot.overlays.append(LineInspector(component=self.polyplot,
                                                    axis='index_x',
                                                    inspect_mode="indexed",
                                                    write_metadata=True,
                                                    is_listener=True,
                                                    color="white"))
        self.polyplot.overlays.append(LineInspector(component=self.polyplot,
                                                    axis='index_y',
                                                    inspect_mode="indexed",
                                                    write_metadata=True,
                                                    color="white",
                                                    is_listener=True))

        # Add these two plots to one container
        contour_container = OverlayPlotContainer(padding=20,
                                                 use_backbuffer=True,
                                                 unified_draw=True)
        contour_container.add(self.polyplot)
        contour_container.add(self.lineplot)

        # Create a colorbar
        cbar_index_mapper = LinearMapper(range=image_value_range)
        self.colorbar = ColorBar(index_mapper=cbar_index_mapper,
                                 plot=self.polyplot,
                                 padding_top=self.polyplot.padding_top,
                                 padding_bottom=self.polyplot.padding_bottom,
                                 padding_right=40,
                                 resizable='v',
                                 width=30)

        self.pd = ArrayPlotData(line_index=array(range(100)),
                                line_value=array(range(100)),
                                scatter_index=array([50]),
                                scatter_value=array([50]),
                                scatter_color=array([50]))

        self.cross_plot = Plot(self.pd, resizable="h")
        self.cross_plot.height = 100
        self.cross_plot.padding = 20
        self.cross_plot.plot(("line_index", "line_value"),
                             line_style="dot")
        self.cross_plot.plot(("scatter_index", "scatter_value", "scatter_color"),
                             type="cmap_scatter",
                             name="dot",
                             color_mapper=self._cmap(image_value_range),
                             marker="circle",
                             marker_size=2)

        self.cross_plot.index_range = self.polyplot.index_range.x_range

        self.pd.set_data("line_index2", array(range(100)))
        self.pd.set_data("line_value2", array(range(100)))
        self.pd.set_data("scatter_index2", array([50]))
        self.pd.set_data("scatter_value2", array([50]))
        self.pd.set_data("scatter_color2", array([50]))

        self.cross_plot2 = Plot(self.pd, width=140, orientation="v",
                                resizable="v", padding=20, padding_bottom=160)
        self.cross_plot2.plot(("line_index2", "line_value2"),
                              line_style="dot")
        self.cross_plot2.plot(("scatter_index2",
                               "scatter_value2",
                               "scatter_color2"),
                              type="cmap_scatter",
                              name="dot",
                              color_mapper=self._cmap(image_value_range),
                              marker="circle",
                              marker_size=2)

        self.cross_plot2.index_range = self.polyplot.index_range.y_range

        # Create a container and add components
        self.container = HPlotContainer(padding=40, fill_padding=True,
                                        bgcolor="white", use_backbuffer=False)
        inner_cont = VPlotContainer(padding=0, use_backbuffer=True)
        inner_cont.add(self.cross_plot)
        inner_cont.add(contour_container)
        self.container.add(self.colorbar)
        self.container.add(inner_cont)
        self.container.add(self.cross_plot2)

    def update(self, model):
        self.minz = model.minz
        self.maxz = model.maxz
        self.colorbar.index_mapper.range.low = self.minz
        self.colorbar.index_mapper.range.high = self.maxz
        self._image_index.set_data(model.xs, model.ys)
        self._image_value.data = model.zs
        self.pd.update_data(line_index=model.xs, line_index2=model.ys)
        self.container.invalidate_draw()
        self.container.request_redraw()

    # ---------------------------------------------------------------------------
    # Event handlers
    # ---------------------------------------------------------------------------

    def _metadata_changed(self, old, new):
        """ This function takes out a cross section from the image data, based
        on the line inspector selections, and updates the line and scatter
        plots."""

        self.cross_plot.value_range.low = self.minz
        self.cross_plot.value_range.high = self.maxz
        self.cross_plot2.value_range.low = self.minz
        self.cross_plot2.value_range.high = self.maxz
        if "selections" in self._image_index.metadata:
            x_ndx, y_ndx = self._image_index.metadata["selections"]
            if y_ndx and x_ndx:
                xdata, ydata = self._image_index.get_data()
                xdata, ydata = xdata.get_data(), ydata.get_data()
                self.pd.update_data(
                    line_value=self._image_value.data[y_ndx, :],
                    line_value2=self._image_value.data[:, x_ndx],
                    scatter_index=array([xdata[x_ndx]]),
                    scatter_index2=array([ydata[y_ndx]]),
                    scatter_value=array([self._image_value.data[y_ndx, x_ndx]]),
                    scatter_value2=array([self._image_value.data[y_ndx, x_ndx]]),
                    scatter_color=array([self._image_value.data[y_ndx, x_ndx]]),
                    scatter_color2=array([self._image_value.data[y_ndx, x_ndx]])
                )
        else:
            self.pd.update_data({"scatter_value": array([50]),
                                 "scatter_value2": array([50]), "line_value": array(range(100)),
                                 "line_value2": array(range(100))})

    def _colormap_changed(self):
        self._cmap = default_colormaps.color_map_name_dict[self.colormap]
        if self.polyplot is not None:
            value_range = self.polyplot.color_mapper.range
            self.polyplot.color_mapper = self._cmap(value_range)
            value_range = self.cross_plot.color_mapper.range
            self.cross_plot.color_mapper = self._cmap(value_range)
            # FIXME: change when we decide how best to update plots using
            # the shared colormap in plot object
            self.cross_plot.plots["dot"
            ][0].color_mapper = self._cmap(value_range)
            self.cross_plot2.plots["dot"
            ][0].color_mapper = self._cmap(value_range)
            self.container.request_redraw()

    def _num_levels_changed(self):
        if self.num_levels > 3:
            self.polyplot.levels = self.num_levels
            self.lineplot.levels = self.num_levels



if __name__ == "__main__":
    app = PlotUI()
    app.configure_traits()