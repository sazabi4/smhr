#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" The stellar parameters tab in Spectroscopy Made Hard """

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

__all__ = ["StellarParametersTab"]

import logging
import matplotlib.gridspec
import numpy as np
import sys
from PySide import QtCore, QtGui
from matplotlib.ticker import MaxNLocator
from time import time

import mpl, style_utils
from smh.photospheres import available as available_photospheres
from smh.photospheres.abundances import asplund_2009 as solar_composition
from smh.spectral_models import (ProfileFittingModel, SpectralSynthesisModel)
from smh import utils
from linelist_manager import TransitionsDialog

from spectral_models_table import SpectralModelsTableViewBase, SpectralModelsFilterProxyModel, SpectralModelsTableModelBase

logger = logging.getLogger(__name__)

if sys.platform == "darwin":
        
    # See http://successfulsoftware.net/2013/10/23/fixing-qt-4-for-mac-os-x-10-9-mavericks/
    substitutes = [
        (".Lucida Grande UI", "Lucida Grande"),
        (".Helvetica Neue DeskInterface", "Helvetica Neue")
    ]
    for substitute in substitutes:
        QtGui.QFont.insertSubstitution(*substitute)


DOUBLE_CLICK_INTERVAL = 0.1 # MAGIC HACK
PICKER_TOLERANCE = 100 # MAGIC HACK


class StellarParametersTab(QtGui.QWidget):


    def __init__(self, parent):
        """
        Create a tab for the determination of stellar parameters by excitation
        and ionization equalibrium.

        :param parent:
            The parent widget.
        """

        super(StellarParametersTab, self).__init__(parent)
        self.parent = parent

        sp = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding, 
            QtGui.QSizePolicy.MinimumExpanding)
        sp.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sp)

        self.parent_layout = QtGui.QHBoxLayout(self)
        self.parent_layout.setContentsMargins(20, 20, 20, 0)

        lhs_layout = QtGui.QVBoxLayout()
        grid_layout = QtGui.QGridLayout()

        # Effective temperature.
        label = QtGui.QLabel(self)
        label.setText("Effective temperature (K)")
        label.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Minimum))
        grid_layout.addWidget(label, 0, 0, 1, 1)
        self.edit_teff = QtGui.QLineEdit(self)
        self.edit_teff.setMinimumSize(QtCore.QSize(40, 0))
        self.edit_teff.setMaximumSize(QtCore.QSize(50, 16777215))
        self.edit_teff.setAlignment(QtCore.Qt.AlignCenter)
        self.edit_teff.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Minimum))
        self.edit_teff.setValidator(
            QtGui.QDoubleValidator(3000, 8000, 0, self.edit_teff))
        self.edit_teff.textChanged.connect(self._check_lineedit_state)
        grid_layout.addWidget(self.edit_teff, 0, 1)
        
        # Surface gravity.
        label = QtGui.QLabel(self)
        label.setText("Surface gravity")
        label.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Minimum))

        grid_layout.addWidget(label, 1, 0, 1, 1)
        self.edit_logg = QtGui.QLineEdit(self)
        self.edit_logg.setMinimumSize(QtCore.QSize(40, 0))
        self.edit_logg.setMaximumSize(QtCore.QSize(50, 16777215))
        self.edit_logg.setAlignment(QtCore.Qt.AlignCenter)
        self.edit_logg.setValidator(
            QtGui.QDoubleValidator(-1, 6, 3, self.edit_logg))
        self.edit_logg.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Minimum))

        self.edit_logg.textChanged.connect(self._check_lineedit_state)
        grid_layout.addWidget(self.edit_logg, 1, 1)

        # Metallicity.
        label = QtGui.QLabel(self)
        label.setText("Metallicity")
        label.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Minimum))

        grid_layout.addWidget(label, 2, 0, 1, 1)
        self.edit_metallicity = QtGui.QLineEdit(self)
        self.edit_metallicity.setMinimumSize(QtCore.QSize(40, 0))
        self.edit_metallicity.setMaximumSize(QtCore.QSize(50, 16777215))
        self.edit_metallicity.setAlignment(QtCore.Qt.AlignCenter)
        self.edit_metallicity.setValidator(
            QtGui.QDoubleValidator(-5, 1, 3, self.edit_metallicity))
        self.edit_metallicity.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Minimum))

        self.edit_metallicity.textChanged.connect(self._check_lineedit_state)
        grid_layout.addWidget(self.edit_metallicity, 2, 1)


        # Microturbulence.
        label = QtGui.QLabel(self)
        label.setText("Microturbulence (km/s)")
        label.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Minimum))

        grid_layout.addWidget(label, 3, 0, 1, 1)
        self.edit_xi = QtGui.QLineEdit(self)
        self.edit_xi.setMinimumSize(QtCore.QSize(40, 0))
        self.edit_xi.setMaximumSize(QtCore.QSize(50, 16777215))
        self.edit_xi.setAlignment(QtCore.Qt.AlignCenter)
        self.edit_xi.setValidator(QtGui.QDoubleValidator(0, 5, 3, self.edit_xi))
        self.edit_xi.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Minimum))

        self.edit_xi.textChanged.connect(self._check_lineedit_state)
        grid_layout.addWidget(self.edit_xi, 3, 1)

        # Optionally TODO: alpha-enhancement.

        lhs_layout.addLayout(grid_layout)

        # Buttons for solving/measuring.        
        hbox = QtGui.QHBoxLayout()
        self.btn_measure = QtGui.QPushButton(self)
        self.btn_measure.setAutoDefault(True)
        self.btn_measure.setDefault(True)
        self.btn_measure.setText("Measure abundances")
        hbox.addWidget(self.btn_measure)

        self.btn_options = QtGui.QPushButton(self)
        self.btn_options.setText("Options..")
        hbox.addWidget(self.btn_options)

        self.btn_solve = QtGui.QPushButton(self)
        self.btn_solve.setText("Solve")
        hbox.addWidget(self.btn_solve)
        lhs_layout.addLayout(hbox)

        #line = QtGui.QFrame(self)
        #line.setFrameShape(QtGui.QFrame.HLine)
        #line.setFrameShadow(QtGui.QFrame.Sunken)
        #lhs_layout.addWidget(line)

        header = ["", u"λ\n(Å)", "Element\n", u"E. W.\n(mÅ)",
                  "log ε\n(dex)"]
        attrs = ("is_acceptable", "_repr_wavelength", "_repr_element", 
                 "equivalent_width", "abundance")

        self.table_view = SpectralModelsTableView(self)
        
        # Set up a proxymodel.
        self.proxy_spectral_models = SpectralModelsFilterProxyModel(self)
        self.proxy_spectral_models.add_filter_function(
            "use_for_stellar_parameter_inference",
            lambda model: model.use_for_stellar_parameter_inference)

        self.proxy_spectral_models.setDynamicSortFilter(True)
        self.proxy_spectral_models.setSourceModel(SpectralModelsTableModel(self, header, attrs))

        self.table_view.setModel(self.proxy_spectral_models)
        self.table_view.setSelectionBehavior(
            QtGui.QAbstractItemView.SelectRows)

        # TODO: Re-enable sorting.
        self.table_view.setSortingEnabled(False)
        self.table_view.setMaximumSize(QtCore.QSize(370, 16777215))        
        self.table_view.setSizePolicy(QtGui.QSizePolicy(
            QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.MinimumExpanding))
        
        # Keep the first colum to a fixed width, but the rest stretched.
        self.table_view.horizontalHeader().setResizeMode(
            0, QtGui.QHeaderView.Fixed)
        self.table_view.horizontalHeader().resizeSection(0, 30) # MAGIC

        for i in range(1, len(header)):
            self.table_view.horizontalHeader().setResizeMode(
                i, QtGui.QHeaderView.Stretch)
        
        lhs_layout.addWidget(self.table_view)

        _ = self.table_view.selectionModel()
        _.selectionChanged.connect(self.selected_model_changed)


        hbox = QtGui.QHBoxLayout()
        self.btn_filter = QtGui.QPushButton(self)
        self.btn_filter.setText("Hide unacceptable models")
        self.btn_quality_control = QtGui.QPushButton(self)
        self.btn_quality_control.setText("Quality control..")
        hbox.addItem(QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Preferred,
            QtGui.QSizePolicy.Minimum))
        hbox.addWidget(self.btn_filter)
        hbox.addWidget(self.btn_quality_control)

        lhs_layout.addLayout(hbox)
        self.parent_layout.addLayout(lhs_layout)


        # Matplotlib figure.
        self.figure = mpl.MPLWidget(None, tight_layout=True, autofocus=True)
        self.figure.setMinimumSize(QtCore.QSize(300, 300))
        sp = QtGui.QSizePolicy(
            QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Expanding)
        sp.setHorizontalStretch(0)
        sp.setVerticalStretch(0)
        sp.setHeightForWidth(self.figure.sizePolicy().hasHeightForWidth())
        self.figure.setSizePolicy(sp)
        #self.figure.setFocusPolicy(QtCore.Qt.StrongFocus)


        gs_top = matplotlib.gridspec.GridSpec(4, 1)
        gs_top.update(hspace=0.40)
        gs_bottom = matplotlib.gridspec.GridSpec(4, 1, 
            height_ratios=[2, 2, 1, 2])
        gs_bottom.update(hspace=0)

        self._colors = {
            26.0: "k",
            26.1: "r"
        }


        self.ax_excitation = self.figure.figure.add_subplot(gs_top[0])
        self.ax_excitation.xaxis.get_major_formatter().set_useOffset(False)
        self.ax_excitation.yaxis.set_major_locator(MaxNLocator(4))
        self.ax_excitation.set_xlabel("Excitation potential (eV)")
        self.ax_excitation.set_ylabel("[X/H]")

        self.ax_excitation_twin = self.ax_excitation.twinx()
        self.ax_excitation_twin.yaxis.set_major_locator(MaxNLocator(4))
        self.ax_excitation_twin.set_ylabel(r"$\log_\epsilon({\rm X})$")

        self.ax_line_strength = self.figure.figure.add_subplot(gs_top[1])
        self.ax_line_strength.xaxis.get_major_formatter().set_useOffset(False)
        self.ax_line_strength.yaxis.set_major_locator(MaxNLocator(4))
        self.ax_line_strength.set_xlabel(r"$\log({\rm EW}/\lambda)$")
        self.ax_line_strength.set_ylabel("[X/H]")

        self.ax_line_strength_twin = self.ax_line_strength.twinx()
        self.ax_line_strength_twin.yaxis.set_major_locator(MaxNLocator(4))
        self.ax_line_strength_twin.set_ylabel(r"$\log_\epsilon({\rm X})$")

        self.ax_residual = self.figure.figure.add_subplot(gs_bottom[2])
        self.ax_residual.axhline(0, c="#666666")
        self.ax_residual.xaxis.set_major_locator(MaxNLocator(5))
        self.ax_residual.yaxis.set_major_locator(MaxNLocator(2))
        self.ax_residual.set_xticklabels([])

        # This is a faux twin axis so that the ylabels on ax_line_strength_twin
        # and ax_excitation_twin do not disappear
        self.ax_residual_twin = self.ax_residual.twinx()
        self.ax_residual_twin.set_yticks([])
        self.ax_residual_twin.set_ylabel(r"$\,$", labelpad=20)

        self.ax_spectrum = self.figure.figure.add_subplot(gs_bottom[3])
        self.ax_spectrum.xaxis.get_major_formatter().set_useOffset(False)
        self.ax_spectrum.xaxis.set_major_locator(MaxNLocator(5))
        self.ax_spectrum.set_xlabel(u"Wavelength (Å)")
        self.ax_spectrum.set_ylabel(r"Normalized flux")

        # Some empty figure objects that we will use later.
        self._lines = {
            "excitation_slope_text": {},
            "line_strength_slope_text": {},
            "abundance_text": {},

            "excitation_trends": {},
            "line_strength_trends": {},
            "excitation_medians": {},
            "line_strength_medians": {},
            "scatter_points": [
                self.ax_excitation.scatter(
                    [], [], s=30, alpha=0.5, ),
                self.ax_line_strength.scatter(
                    [], [], s=30, alpha=0.5, ),
            ],
            "selected_point": [
                self.ax_excitation.scatter([], [],
                    edgecolor="b", facecolor="none", s=150, linewidth=3, zorder=2),
                self.ax_line_strength.scatter([], [],
                    edgecolor="b", facecolor="none", s=150, linewidth=3, zorder=2)
            ],
            "spectrum": None,
            "transitions_center_main": self.ax_spectrum.axvline(
                np.nan, c="#666666", linestyle=":"),
            "transitions_center_residual": self.ax_residual.axvline(
                np.nan, c="#666666", linestyle=":"),
            "model_masks": [],
            "nearby_lines": [],
            "model_fit": self.ax_spectrum.plot([], [], c="r")[0],
            "model_residual": self.ax_residual.plot(
                [], [], c="k", drawstyle="steps-mid")[0],
            "interactive_mask": [
                self.ax_spectrum.axvspan(xmin=np.nan, xmax=np.nan, ymin=np.nan,
                    ymax=np.nan, facecolor="r", edgecolor="none", alpha=0.25,
                    zorder=-5),
                self.ax_residual.axvspan(xmin=np.nan, xmax=np.nan, ymin=np.nan,
                    ymax=np.nan, facecolor="r", edgecolor="none", alpha=0.25,
                    zorder=-5)
            ]
        }

        self.parent_layout.addWidget(self.figure)

        # Connect buttons.
        self.btn_measure.clicked.connect(self.measure_abundances)
        self.btn_options.clicked.connect(self.options)
        self.btn_solve.clicked.connect(self.solve_parameters)
        self.btn_filter.clicked.connect(self.filter_models)
        self.btn_quality_control.clicked.connect(self.quality_control)
        self.edit_teff.returnPressed.connect(self.btn_measure.clicked)
        self.edit_logg.returnPressed.connect(self.btn_measure.clicked)
        self.edit_metallicity.returnPressed.connect(self.btn_measure.clicked)
        self.edit_xi.returnPressed.connect(self.btn_measure.clicked)

        # Connect matplotlib.
        self.figure.mpl_connect("button_press_event", self.figure_mouse_press)
        self.figure.mpl_connect("button_release_event", self.figure_mouse_release)

        return None


    def populate_widgets(self):
        """ Update the stellar parameter edit boxes from the session. """

        if not hasattr(self.parent, "session") or self.parent.session is None:
            return None

        widget_info = [
            (self.edit_teff, "{0:.0f}", "effective_temperature"),
            (self.edit_logg, "{0:.2f}", "surface_gravity"),
            (self.edit_metallicity, "{0:+.2f}", "metallicity"),
            (self.edit_xi, "{0:.2f}", "microturbulence")
        ]
        metadata = self.parent.session.metadata["stellar_parameters"]

        for widget, format, key in widget_info:
            widget.setText(format.format(metadata[key]))

        return None


    def _check_lineedit_state(self, *args, **kwargs):
        """
        Update the background color of a QLineEdit object based on whether the
        input is valid.
        """

        # TODO: Implement from
        # http://stackoverflow.com/questions/27159575/pyside-modifying-widget-colour-at-runtime-without-overwriting-stylesheet

        sender = self.sender()
        validator = sender.validator()
        state = validator.validate(sender.text(), 0)[0]
        if state == QtGui.QValidator.Acceptable:
            color = 'none' # normal background color
        elif state == QtGui.QValidator.Intermediate:
            color = '#fff79a' # yellow
        else:
            color = '#f6989d' # red
        sender.setStyleSheet('QLineEdit { background-color: %s }' % color)
    
        return None


    def filter_models(self):
        """
        Filter the view of the models used in the determination of stellar
        parameters. 
        """

        hide = self.btn_filter.text().startswith("Hide")

        if hide:
            self.proxy_spectral_models.add_filter_function(
                "is_acceptable", lambda model: model.is_acceptable)
        else:
            self.proxy_spectral_models.delete_filter_function("is_acceptable")

        text = "{} unacceptable models".format(("Hide", "Show")[hide])
        self.btn_filter.setText(text)
        return None


    def quality_control(self):
        """
        Show a dialog to specify quality control constraints for spectral models
        used in the determination of stellar parameters.
        """
        raise NotImplementedError


    def figure_mouse_pick(self, event):
        """
        Trigger for when the mouse is used to select an item in the figure.

        :param event:
            The matplotlib event.
        """
        
        ycol = "abundance"
        xcol = {
            self.ax_excitation_twin: "expot",
            self.ax_line_strength_twin: "reduced_equivalent_width"
        }[event.inaxes]

        xscale = np.ptp(event.inaxes.get_xlim())
        yscale = np.ptp(event.inaxes.get_ylim())
        distance = np.sqrt(
                ((self._state_transitions[ycol] - event.ydata)/yscale)**2 \
            +   ((self._state_transitions[xcol] - event.xdata)/xscale)**2)

        index = np.nanargmin(distance)

        # Because the state transitions are linked to the parent source model of
        # the table view, we will have to get the proxy index.
        proxy_index = self.table_view.model().mapFromSource(
            self.proxy_spectral_models.sourceModel().createIndex(index, 0)).row()

        self.table_view.selectRow(proxy_index)
        return None


    def figure_mouse_press(self, event):
        """
        Trigger for when the mouse button is pressed in the figure.

        :param event:
            The matplotlib event.
        """

        if event.inaxes \
        in (self.ax_residual, self.ax_residual_twin, self.ax_spectrum):
            self.spectrum_axis_mouse_press(event)

        elif event.inaxes \
        in (self.ax_excitation, self.ax_excitation_twin,
            self.ax_line_strength, self.ax_line_strength_twin):
            self.figure_mouse_pick(event)

        return None


    def figure_mouse_release(self, event):
        """
        Trigger for when the mouse button is released in the figure.

        :param event:
            The matplotlib event.
        """

        if event.inaxes \
        in (self.ax_residual, self.ax_residual_twin, self.ax_spectrum):
            self.spectrum_axis_mouse_release(event)
        return None


    def spectrum_axis_mouse_press(self, event):
        """
        The mouse button was pressed in the spectrum axis.

        :param event:
            The matplotlib event.
        """

        if event.dblclick:

            # Double click.
            spectral_model, proxy_index, index = self._get_selected_model(True)
            for i, (s, e) in enumerate(spectral_model.metadata["mask"][::-1]):
                if e >= event.xdata >= s:

                    mask = spectral_model.metadata["mask"]
                    index = len(mask) - 1 - i
                    del mask[index]

                    # Re-fit the current spectral_model.
                    spectral_model.fit()

                    # Update the view of the current model.
                    self.update_spectrum_figure()
    
                    # Update the data model.
                    data_model = self.proxy_spectral_models.sourceModel()
                    data_model.dataChanged.emit(
                        data_model.createIndex(proxy_index.row(), 0),
                        data_model.createIndex(proxy_index.row(),
                            data_model.columnCount(QtCore.QModelIndex())))

                    # It ought to be enough just to emit the dataChanged signal, but
                    # there is a bug when using proxy models where the data table is
                    # updated but the view is not, so we do this hack to make it
                    # work:
                    self.table_view.rowMoved(
                        proxy_index.row(), proxy_index.row(), proxy_index.row())
                    
                    break

            else:
                # No match with a masked region. 

                # TODO: Add a point that will be used for the continuum?

                # For the moment just refit the model.
                spectral_model.fit()

                # Update the view of the current model.
                self.update_spectrum_figure()

                # Update the data model.
                data_model = self.proxy_spectral_models.sourceModel()
                data_model.dataChanged.emit(
                    data_model.createIndex(proxy_index.row(), 0),
                    data_model.createIndex(proxy_index.row(),
                        data_model.columnCount(QtCore.QModelIndex())))

                # It ought to be enough just to emit the dataChanged signal, but
                # there is a bug when using proxy models where the data table is
                # updated but the view is not, so we do this hack to make it
                # work:
                self.table_view.rowMoved(
                    proxy_index.row(), proxy_index.row(), proxy_index.row())

                return None

        else:
            # Single click.
            xmin, xmax, ymin, ymax = (event.xdata, np.nan, -1e8, +1e8)
            for patch in self._lines["interactive_mask"]:
                patch.set_xy([
                    [xmin, ymin],
                    [xmin, ymax],
                    [xmax, ymax],
                    [xmax, ymin],
                    [xmin, ymin]
                ])

            # Set the signal and the time.
            self._interactive_mask_region_signal = (
                time(),
                self.figure.mpl_connect(
                    "motion_notify_event", self.update_mask_region)
            )

        return None


    def update_mask_region(self, event):
        """
        Update the visible selected masked region for the selected spectral
        model. This function is linked to a callback for when the mouse position
        moves.

        :para event:
            The matplotlib motion event to show the current mouse position.
        """

        if event.xdata is None: return

        signal_time, signal_cid = self._interactive_mask_region_signal
        if time() - signal_time > DOUBLE_CLICK_INTERVAL:

            data = self._lines["interactive_mask"][0].get_xy()

            # Update xmax.
            data[2:4, 0] = event.xdata
            for patch in self._lines["interactive_mask"]:
                patch.set_xy(data)

            self.figure.draw()

        return None



    def spectrum_axis_mouse_release(self, event):
        """
        Mouse button was released from the spectrum axis.

        :param event:
            The matplotlib event.
        """

        try:
            signal_time, signal_cid = self._interactive_mask_region_signal

        except AttributeError:
            return None

        xy = self._lines["interactive_mask"][0].get_xy()

        if event.xdata is None:
            # Out of axis; exclude based on the closest axis limit
            xdata = xy[2, 0]
        else:
            xdata = event.xdata


        # If the two mouse events were within some time interval,
        # then we should not add a mask because those signals were probably
        # part of a double-click event.
        if  time() - signal_time > DOUBLE_CLICK_INTERVAL \
        and np.abs(xy[0,0] - xdata) > 0:
            
            # Get current spectral model.
            spectral_model, proxy_index, index = self._get_selected_model(True)

            # Add mask metadata.
            spectral_model.metadata["mask"].append([xy[0,0], xy[2, 0]])

            # Re-fit the spectral model.
            spectral_model.fit()

            # Update the view of the spectral model.
            self.update_spectrum_figure()

            # Update the data model.
            data_model = self.proxy_spectral_models.sourceModel()
            data_model.dataChanged.emit(
                data_model.createIndex(proxy_index.row(), 0),
                data_model.createIndex(proxy_index.row(),
                    data_model.columnCount(QtCore.QModelIndex())))

            # It ought to be enough just to emit the dataChanged signal, but
            # there is a bug when using proxy models where the data table is
            # updated but the view is not, so we do this hack to make it
            # work:
            self.table_view.rowMoved(
                proxy_index.row(), proxy_index.row(), proxy_index.row())


        xy[:, 0] = np.nan
        for patch in self._lines["interactive_mask"]:
            patch.set_xy(xy)

        self.figure.mpl_disconnect(signal_cid)
        self.figure.draw()
        del self._interactive_mask_region_signal
        return None



    def update_stellar_parameters(self):
        """ Update the stellar parameters with the values in the GUI. """

        self.parent.session.metadata["stellar_parameters"].update({
            "effective_temperature": float(self.edit_teff.text()),
            "surface_gravity": float(self.edit_logg.text()),
            "metallicity": float(self.edit_metallicity.text()),
            "microturbulence": float(self.edit_xi.text())
        })
        return True



    def _check_for_spectral_models(self):
        """
        Check the session for any valid spectral models that are associated with
        the determination of stellar parameters.
        """

        # Are there any spectral models to be used for the determination of
        # stellar parameters?
        for sm in self.parent.session.metadata.get("spectral_models", []):
            if sm.use_for_stellar_parameter_inference: break

        else:
            reply = QtGui.QMessageBox.information(self,
                "No spectral models found",
                "No spectral models are currently associated with the "
                "determination of stellar parameters.\n\n"
                "Click 'OK' to load the transitions manager.")

            if reply == QtGui.QMessageBox.Ok:
                # Load line list manager.
                dialog = TransitionsDialog(self.parent.session,
                    callbacks=[
                        self.parent.session.index_spectral_models,
                        self.proxy_spectral_models.reset
                    ])
                dialog.exec_()

                # Do we even have any spectral models now?
                for sm in self.parent.session.metadata.get("spectral_models", []):
                    if sm.use_for_stellar_parameter_inference: break
                else:
                    return False
            else:
                return False

        return True


    def update_scatter_plots(self, redraw=False):

        if not hasattr(self, "_state_transitions"):
            if redraw:
                self.figure.draw()
            return None

        # Update figures.
        colors = [self._colors.get(s, "#FFFFFF") \
            for s in self._state_transitions["species"]]
        ex_collection, line_strength_collection = self._lines["scatter_points"]

        ex_collection.set_offsets(np.array([
            self._state_transitions["expot"],
            self._state_transitions["abundance"]]).T)
        ex_collection.set_facecolor(colors)

        line_strength_collection.set_offsets(np.array([
            self._state_transitions["reduced_equivalent_width"],
            self._state_transitions["abundance"]]).T)
        line_strength_collection.set_facecolor(colors)

        # Update limits on the excitation and line strength figures.
        style_utils.relim_axes(self.ax_excitation)
        style_utils.relim_axes(self.ax_line_strength)

        self.ax_excitation_twin.set_ylim(self.ax_excitation.get_ylim())
        self.ax_line_strength_twin.set_ylim(self.ax_line_strength.get_ylim())
        self.ax_excitation_twin.set_ylabel(r"$\log_\epsilon({\rm X})$")
        self.ax_line_strength_twin.set_ylabel(r"$\log_\epsilon({\rm X})$")


        # Scale the left hand ticks to [X/H] or [X/M]

        # How many atomic number?
        ok = np.isfinite(self._state_transitions["abundance"])
        Z = list(set(self._state_transitions["species"][ok].astype(int)))
        if len(Z) == 1:

            scaled_ticks = np.array(
                self.ax_excitation.get_yticks()) - solar_composition(Z[0])

            self.ax_excitation.set_yticklabels(scaled_ticks)
            self.ax_line_strength.set_yticklabels(scaled_ticks)

            label = "[{}/H]".format(
                self._state_transitions["element"][ok][0].split()[0])
            self.ax_excitation.set_ylabel(label)
            self.ax_line_strength.set_ylabel(label)

        else:
            raise NotImplementedError
        
        # Update trend lines.
        self.update_trend_lines()

        if redraw:
            self.figure.draw()
        return None


    def measure_abundances(self):
        """ The measure abundances button has been clicked. """

        if self.parent.session is None or not self._check_for_spectral_models():
            return None

        # Fit the spectral models if they have not been fit before.
        for model in self.parent.session.metadata["spectral_models"]:
            if model.use_for_stellar_parameter_inference \
            and model.metadata.get("fitted_result", None) is None:
                model.fit()

        # Update the session with the stellar parameters in the GUI, and then
        # calculate abundances.
        self.update_stellar_parameters()

        filtering = lambda model: model.use_for_stellar_parameter_inference
        try:
            self._state_transitions, state, \
                = self.parent.session.stellar_parameter_state(full_output=True,
                    filtering=filtering)

        except ValueError:
            logger.warn("No measured transitions to calculate abundances for.")
            return None

        # The order of transitions may differ from the order in the table view.
        # We need to re-order the transitions by hashes.
        """
        print("STATE")
        print(self._state_transitions)

        print("MODELS")
        print([each.transition["wavelength"][0] for each in self.parent.session.metadata["spectral_models"]])

        # The number of transitions should match what is shown in the view.
        assert len(self._state_transitions) == self.table_view.model().rowCount(
            QtCore.QModelIndex())
        """

        # Otherwise we're fucked:
        expected_hashes = np.array([each.transitions["hash"][0] for each in \
            self.parent.session.metadata["spectral_models"]]) 

        assert np.all(expected_hashes == self._state_transitions["hash"])

        self.update_scatter_plots()

        # Draw trend lines based on the data already there.
        self.update_trend_lines()

        # Update selected entries.
        self.selected_model_changed()

        # Update abundance column for all rows.
        data_model = self.proxy_spectral_models.sourceModel()
        # 3 is the abundance column
        data_model.dataChanged.emit(
            data_model.createIndex(0, 3),
            data_model.createIndex(
                data_model.rowCount(QtCore.QModelIndex()), 3))

        # It ought to be enough just to emit the dataChanged signal, but
        # there is a bug when using proxy models where the data table is
        # updated but the view is not, so we do this hack to make it
        # work:
        self.table_view.columnMoved(3, 3, 3)

        self.proxy_spectral_models.reset()

        return None


    def update_trend_lines(self, redraw=False):
        """
        Update the trend lines in the figures.
        """

        if not hasattr(self, "_state_transitions"):
            if redraw:
                self.figure.draw()
            return None

        states = utils.equilibrium_state(self._state_transitions,
            columns=("expot", "reduced_equivalent_width"))

        print("states", states)

        # Offsets from the edge of axes.
        x_offset = 0.0125
        y_offset = 0.10
        y_space = 0.15

        no_state = (np.nan, np.nan, np.nan, np.nan, 0)
        for i, (species, state) in enumerate(states.items()):
            if not state: continue

            color = self._colors[species]

            # Create defaults.
            if species not in self._lines["excitation_medians"]:
                self._lines["excitation_medians"][species] \
                    = self.ax_excitation.plot([], [], c=color, linestyle=":")[0]
            if species not in self._lines["line_strength_medians"]:
                self._lines["line_strength_medians"][species] \
                    = self.ax_line_strength.plot([], [], c=color, linestyle=":")[0]

            if species not in self._lines["excitation_trends"]:
                self._lines["excitation_trends"][species] \
                    = self.ax_excitation.plot([], [], c=color)[0]
            if species not in self._lines["line_strength_trends"]:
                self._lines["line_strength_trends"][species] \
                    = self.ax_line_strength.plot([], [], c=color)[0]

            # Do actual updates.
            #(m, b, np.median(y), np.std(y), len(x))
            m, b, median, sigma, N = state.get("expot", no_state)

            x = np.array(self.ax_excitation.get_xlim())
            self._lines["excitation_medians"][species].set_data(x, median)
            self._lines["excitation_trends"][species].set_data(x, m * x + b)

            m, b, median, sigma, N = state.get("reduced_equivalent_width", no_state)
            x = np.array(self.ax_line_strength.get_xlim())
            self._lines["line_strength_medians"][species].set_data(x, median)
            self._lines["line_strength_trends"][species].set_data(x, m * x + b)

            # Show text.
            # TECH DEBT:
            # If a new species is added during stellar parameter determination
            # and some text is already shown, new text could appear on top of
            # that due to the way dictionaries (the state dictionary) is hashed.
            if species not in self._lines["abundance_text"]:
                self._lines["abundance_text"][species] \
                    = self.ax_excitation.text(
                        x_offset, 1 - y_offset - i * y_space, "",
                        color=color, transform=self.ax_excitation.transAxes,
                        horizontalalignment="left", verticalalignment="center")
            
            # Only show useful text.
            text = ""   if N == 0 \
                        else r"$\log_\epsilon{{\rm ({0})}} = {1:.2f} \pm {2:.2f}$"\
                             r" $(N = {3:.0f})$".format(
                                utils.species_to_element(species).replace(" ", "\,"),
                                median, sigma, N)
            self._lines["abundance_text"][species].set_text(text)


            m, b, median, sigma, N = state.get("expot", no_state)
            if species not in self._lines["excitation_slope_text"]:
                self._lines["excitation_slope_text"][species] \
                    = self.ax_excitation.text(
                        1 - x_offset, 1 - y_offset - i * y_space, "",
                        color=color, transform=self.ax_excitation.transAxes,
                        horizontalalignment="right", verticalalignment="center")

            # Only show useful text.
            text = ""   if not np.isfinite(m) \
                        else r"${0:+.3f}$ ${{\rm dex\,eV}}^{{-1}}$".format(m)
            self._lines["excitation_slope_text"][species].set_text(text)


            m, b, median, sigma, N = state.get("reduced_equivalent_width",
                no_state)
            if species not in self._lines["line_strength_slope_text"]:
                self._lines["line_strength_slope_text"][species] \
                    = self.ax_line_strength.text(
                        1 - x_offset, 1 - y_offset - i * y_space, "",
                        color=color, transform=self.ax_line_strength.transAxes,
                        horizontalalignment="right", verticalalignment="center")

            # Only show useful text.
            text = ""   if not np.isfinite(m) else r"${0:+.3f}$".format(m)
            self._lines["line_strength_slope_text"][species].set_text(text)

        if redraw:
            self.figure.draw()

        return None



    def _get_selected_model(self, full_output=False):

        # Map the first selected row back to the source model index.
        proxy_index = self.table_view.selectionModel().selectedIndexes()[-1]
        index = self.proxy_spectral_models.mapToSource(proxy_index).row()
        model = self.parent.session.metadata["spectral_models"][index]
        return (model, proxy_index, index) if full_output else model


    def update_selected_points(self, redraw=False):
        # Show selected points.


        proxy_indices = np.unique(np.array([index for index in \
            self.table_view.selectionModel().selectedIndexes()]))

        if 1 > proxy_indices.size:
            for collection in self._lines["selected_point"]:
                collection.set_offsets(np.array([np.nan, np.nan]).T)
            if redraw:
                self.figure.draw()
            return None


        # These indices are proxy indices, which must be mapped back.
        indices = np.unique([self.table_view.model().mapToSource(index).row() \
            for index in proxy_indices])

        try:
            x_excitation = self._state_transitions["expot"][indices]
            x_strength = self._state_transitions["reduced_equivalent_width"][indices]
            y = self._state_transitions["abundance"][indices]

        except:
            x_excitation, x_strength, y = (np.nan, np.nan, np.nan)

        point_excitation, point_strength = self._lines["selected_point"]
        point_excitation.set_offsets(np.array([x_excitation, y]).T)
        point_strength.set_offsets(np.array([x_strength, y]).T)

        if redraw:
            self.figure.draw()

        return None


    def selected_model_changed(self):
        """
        The selected model was changed.
        """
        ta = time()

        # Show point on excitation/line strength plot.
        try:
            selected_model = self._get_selected_model()

        except IndexError:
            self.update_selected_points(redraw=True)
            print("Time taken B: {}".format(time() - ta))

            return None
            
        print("selected model is at ", selected_model._repr_wavelength)
        
        self.update_selected_points()

        # Show spectrum.
        self.update_spectrum_figure(redraw=True)

        print("Time taken: {}".format(time() - ta))
        return None


    def update_spectrum_figure(self, redraw=True):
        """ Update the spectrum figure. """

        try:
            selected_model = self._get_selected_model()

        except IndexError:
            # No line selected.
            if redraw:
                self.figure.draw()
            return None

        # Draw the spectrum.
        transitions = selected_model.transitions
        window = selected_model.metadata["window"]
        limits = [
            transitions["wavelength"][0] - window,
            transitions["wavelength"][-1] + window,
        ]
        spectrum = self.parent.session.normalized_spectrum
        show = (limits[1] >= spectrum.dispersion) \
             * (spectrum.dispersion >= limits[0])

        if self._lines["spectrum"] is not None:
            for i in range(len(self._lines["spectrum"])):
                self._lines["spectrum"][i].remove()
            del self._lines["spectrum"]

        sigma = 1.0/np.sqrt(spectrum.ivar[show])
        self._lines["spectrum"] = [
            # The flux values.
            self.ax_spectrum.plot(spectrum.dispersion[show],
                spectrum.flux[show], c="k", drawstyle="steps-mid")[0],

            # The uncertainty in flue.
            style_utils.fill_between_steps(self.ax_spectrum, 
                spectrum.dispersion[show],
                spectrum.flux[show] - sigma, spectrum.flux[show] + sigma, 
                facecolor="#cccccc", edgecolor="#cccccc", alpha=1),

            # The uncertainty in flux in the residuals panel.
            style_utils.fill_between_steps(self.ax_residual, 
                spectrum.dispersion[show], -sigma, +sigma, 
                facecolor="#CCCCCC", edgecolor="none", alpha=1)
        ]

        self.ax_spectrum.set_xlim(limits)
        self.ax_residual.set_xlim(limits)

        self.ax_spectrum.set_ylim(0, 1.2)
        self.ax_spectrum.set_yticks([0, 0.5, 1])
        self.ax_residual.set_ylim(-0.05, 0.05)
        
        self.figure.draw()

        # If this is a profile fitting line, show where the centroid is.
        x = transitions["wavelength"][0] \
            if isinstance(selected_model, ProfileFittingModel) else np.nan
        self._lines["transitions_center_main"].set_data([x, x], [0, 1.2])
        self._lines["transitions_center_residual"].set_data([x, x], [0, 1.2])

        # Model masks specified by the user.
        # (These should be shown regardless of whether there is a fit or not.)
        for i, (start, end) in enumerate(selected_model.metadata["mask"]):
            try:
                patches = self._lines["model_masks"][i]

            except IndexError:
                self._lines["model_masks"].append([
                    self.ax_spectrum.axvspan(np.nan, np.nan,
                        facecolor="r", edgecolor="none", alpha=0.25),
                    self.ax_residual.axvspan(np.nan, np.nan,
                        facecolor="r", edgecolor="none", alpha=0.25)
                ])
                patches = self._lines["model_masks"][-1]

            for patch in patches:
                patch.set_xy([
                    [start, -1e8],
                    [start, +1e8],
                    [end,   +1e8],
                    [end,   -1e8],
                    [start, -1e8]
                ])
                patch.set_visible(True)

        # Hide unnecessary ones.
        N = len(selected_model.metadata["mask"])
        for unused_patches in self._lines["model_masks"][N:]:
            for unused_patch in unused_patches:
                unused_patch.set_visible(False)

        # Hide previous model_errs
        try:
            self._lines["model_yerr"].set_visible(False)
            del self._lines["model_yerr"]
            # TODO: This is wrong. It doesn't actually delete them so if
            #       you ran this forever then you would get a real bad 
            #       memory leak in Python. But for now, re-calculating
            #       the PolyCollection is in the too hard basket.

        except KeyError:
            None

        # Things to show if there is a fitted result.
        try:
            (named_p_opt, cov, meta) = selected_model.metadata["fitted_result"]

            # Test for some requirements.
            _ = (meta["model_x"], meta["model_y"], meta["residual"])

        except KeyError:
            meta = {}
            self._lines["model_fit"].set_data([], [])
            self._lines["model_residual"].set_data([], [])

        else:
            assert len(meta["model_x"]) == len(meta["model_y"])
            assert len(meta["model_x"]) == len(meta["residual"])
            assert len(meta["model_x"]) == len(meta["model_yerr"])

            self._lines["model_fit"].set_data(meta["model_x"], meta["model_y"])
            self._lines["model_residual"].set_data(
                meta["model_x"], meta["residual"])

            # Model yerr.
            if np.any(np.isfinite(meta["model_yerr"])):
                self._lines["model_yerr"] = self.ax_spectrum.fill_between(
                    meta["model_x"],
                    meta["model_y"] + meta["model_yerr"],
                    meta["model_y"] - meta["model_yerr"],
                    facecolor="r", edgecolor="none", alpha=0.5)

            # Model masks due to nearby lines.
            if "nearby_lines" in meta:
                for i, (_, (start, end)) in enumerate(meta["nearby_lines"]):
                    try:
                        patches = self._lines["nearby_lines"][i]
                
                    except IndexError:
                        self._lines["nearby_lines"].append([
                            self.ax_spectrum.axvspan(np.nan, np.nan,
                                facecolor="b", edgecolor="none", alpha=0.25),
                            self.ax_residual.axvspan(np.nan, np.nan,
                                facecolor="b", edgecolor="none", alpha=0.25)
                        ])
                        patches = self._lines["nearby_lines"][-1]

                    for patch in patches:                            
                        patch.set_xy([
                            [start, -1e8],
                            [start, +1e8],
                            [end,   +1e8],
                            [end,   -1e8],
                            [start, -1e8]
                        ])
                        patch.set_visible(True)
                    

        # Hide any masked model regions due to nearby lines.
        N = len(meta.get("nearby_lines", []))
        for unused_patches in self._lines["nearby_lines"][N:]:
            for unused_patch in unused_patches:
                unused_patch.set_visible(False)

        self.figure.draw()

        return None



    def options(self):
        """ Open a GUI for the radiative transfer and solver options. """
        raise NotImplementedError


    def solve_parameters(self):
        """ Solve the stellar parameters. """
        raise NotImplementedError



class SpectralModelsTableView(SpectralModelsTableViewBase):

    def contextMenuEvent(self, event):
        """
        Provide a context (right-click) menu for the table containing the
        spectral models to use for stellar parameter inference.

        :param event:
            The mouse event that triggered the menu.
        """

        proxy_indices = self.selectionModel().selectedRows()
        indices = np.unique([self.model().mapToSource(index).row() \
            for index in proxy_indices])

        print("proxy", proxy_indices)
        print("indices", indices)

        N = len(indices)

        menu = QtGui.QMenu(self)
        fit_models = menu.addAction(
            "Fit selected model{}..".format(["", "s"][N != 1]))
        menu.addSeparator()
        mark_as_acceptable = menu.addAction("Mark as acceptable")
        mark_as_unacceptable = menu.addAction("Mark as unacceptable")
        menu.addSeparator()

        # Common options.
        set_fitting_window = menu.addAction("Set fitting window..")

        continuum_menu = menu.addMenu("Set continuum")
        set_no_continuum = continuum_menu.addAction("No continuum",
            checkable=True)
        continuum_menu.addSeparator()
        set_continuum_order = [continuum_menu.addAction(
            "Order {}".format(i), checkable=True) for i in range(0, 10)]

        menu.addSeparator()
        menu_profile_type = menu.addMenu("Set profile type")

        set_gaussian = menu_profile_type.addAction("Gaussian")
        set_lorentzian = menu_profile_type.addAction("Lorentzian")
        set_voigt = menu_profile_type.addAction("Voigt")

        menu.addSeparator()

        enable_central_weighting = menu.addAction("Enable central weighting")
        disable_central_weighting = menu.addAction("Disable central weighting")

        menu.addSeparator()

        set_detection_sigma = menu.addAction("Set detection sigma..")
        set_detection_pixels = menu.addAction("Set detection pixels..")

        menu.addSeparator()

        set_rv_tolerance = menu.addAction("Set RV tolerance..")
        set_wl_tolerance = menu.addAction("Set WL tolerance..")

        if N == 0:
            menu.setEnabled(False)


        action = menu.exec_(self.mapToGlobal(event.pos()))

        update_spectrum_figure = False

        if action == fit_models:
            for idx in indices:
                spectral_model \
                    = self.parent.parent.session.metadata["spectral_models"][idx]
                spectral_model.fit()
            update_spectrum_figure = True


        elif action == mark_as_unacceptable:
            for idx in indices:
                spectral_model \
                    = self.parent.parent.session.metadata["spectral_models"][idx]
                spectral_model.metadata["is_acceptable"] = False


        elif action == mark_as_acceptable:
            for idx in indices:
                spectral_model \
                    = self.parent.parent.session.metadata["spectral_models"][idx]
                if "fitted_result" in spectral_model.metadata:
                    spectral_model.metadata["is_acceptable"] = True


        elif action == set_fitting_window:

            first_spectral_model = \
                self.parent.parent.session.metadata["spectral_models"][indices[0]]

            window, is_ok = QtGui.QInputDialog.getDouble(
                None, "Set fitting window", u"Fitting window (Å):", 
                value=first_spectral_model.metadata["window"],
                minValue=0.1, maxValue=1000)
            if not is_ok: return None

            for idx in indices:
                spectral_model \
                    = self.parent.parent.session.metadata["spectral_models"][idx]
                spectral_model.metadata["window"] = window

                if "fitted_result" in spectral_model.metadata:
                    spectral_model.fit()
                    update_spectrum_figure = True


        elif action == set_no_continuum:
            for idx in indices:
                spectral_model \
                    = self.parent.parent.session.metadata["spectral_models"][idx]
                spectral_model.metadata["continuum_order"] = -1

                # Re-fit if it already had a result.
                if "fitted_result" in spectral_model.metadata:
                    spectral_model.fit()
                    update_spectrum_figure = True


        elif action in set_continuum_order:            
            order = set_continuum_order.index(action)
            for idx in indices:
                spectral_model \
                    = self.parent.parent.session.metadata["spectral_models"][idx]
                spectral_model.metadata["continuum_order"] = order

                # Re-fit if it already had a result.
                if "fitted_result" in spectral_model.metadata:
                    spectral_model.fit()
                    update_spectrum_figure = True


        elif action in (set_gaussian, set_lorentzian, set_voigt):
            kind = {
                set_gaussian: "gaussian",
                set_lorentzian: "lorentzian",
                set_voigt: "voigt"
            }[action]

            for idx in indices:
                spectral_model \
                    = self.parent.parent.session.metadata["spectral_models"][idx]
                if isinstance(spectral_model, ProfileFittingModel):
                    spectral_model.metadata["profile"] = kind

                    if "fitted_result" in spectral_model.metadata:
                        spectral_model.fit()
                        update_spectrum_figure = True


        elif action in (enable_central_weighting, disable_central_weighting):
            toggle = (action == enable_central_weighting)
            for idx in indices:
                spectral_model \
                    = self.parent.parent.session.metadata["spectral_models"][idx]

                if isinstance(spectral_model, ProfileFittingModel):
                    spectral_model.metadata["central_weighting"] = toggle

                    if "fitted_result" in spectral_model.metadata:
                        spectral_model.fit()
                        update_spectrum_figure = True


        elif action == set_detection_sigma:

            # Get the first profile model
            for idx in indices:
                detection_sigma = self.parent.parent.session\
                    .metadata["spectral_models"][idx]\
                    .metadata.get("detection_sigma", None)
                if detection_sigma is not None:
                    break
            else:
                detection_sigma = 0.5

            detection_sigma, is_ok = QtGui.QInputDialog.getDouble(
                None, "Set detection sigma", u"Detection sigma:", 
                value=detection_sigma, minValue=0.1, maxValue=1000)
            if not is_ok: return None

            for idx in indices:
                spectral_model \
                    = self.parent.parent.session.metadata["spectral_models"][idx]

                if isinstance(spectral_model, ProfileFittingModel):
                    spectral_model.metadata["detection_sigma"] = detection_sigma

                    if "fitted_result" in spectral_model.metadata:
                        spectral_model.fit()
                        update_spectrum_figure = True

        elif action == set_detection_pixels:
            raise NotImplementedError

        elif action == set_rv_tolerance:
            raise NotImplementedError

        elif action == set_wl_tolerance:
            raise NotImplementedError

        if update_spectrum_figure:
            self.parent.update_spectrum_figure(redraw=True)
            

        self.parent.proxy_spectral_models.reset()

        return None


class SpectralModelsTableModel(SpectralModelsTableModelBase):
    def data(self, index, role):
        """
        Display the data.

        :param index:
            The table index.

        :param role:
            The display role.
        """

        if not index.isValid():
            return None

        column = index.column()
        spectral_model = self.spectral_models[index.row()]

        if  column == 0 \
        and role in (QtCore.Qt.DisplayRole, QtCore.Qt.CheckStateRole):
            value = spectral_model.is_acceptable
            if role == QtCore.Qt.CheckStateRole:
                return QtCore.Qt.Checked if value else QtCore.Qt.Unchecked
            else:
                return None

        elif column == 1:
            value = spectral_model._repr_wavelength

        elif column == 2:
            value = spectral_model._repr_element

        elif column == 3:
            try:
                result = spectral_model.metadata["fitted_result"][2]
                equivalent_width = result["equivalent_width"][0]
            except:
                equivalent_width = np.nan

            value = "{0:.1f}".format(1000 * equivalent_width) \
                if np.isfinite(equivalent_width) else ""

        elif column == 4:
            try:
                abundances \
                    = spectral_model.metadata["fitted_result"][2]["abundances"]

            except (IndexError, KeyError):
                value = ""

            else:
                # How many elements were measured?
                value = "; ".join(["{0:.2f}".format(abundance) \
                    for abundance in abundances])

        return value if role == QtCore.Qt.DisplayRole else None
    

    def setData(self, index, value, role=QtCore.Qt.DisplayRole):
        
        # We only allow the checkbox to be ticked or unticked here. The other
        # columns cannot be edited. 
        # This is handled by the SpectralModelsTableModelBase class.

        # If the checkbox has just been ticked by the user but the selected
        # spectral model does not have a result, we should not allow the
        # spectral model to be marked as acceptable.
        if index.column() == 0 and value and \
        "fitted_result" not in self.spectral_models[index.row()].metadata:
            return False
        
        value = super(SpectralModelsTableModel, self).setData(index, value, role)

        # If we have a cache of the state transitions, update the entries.
        if hasattr(self.parent, "_state_transitions"):
            cols = ("equivalent_width", "reduced_equivalent_width", "abundance")
            for col in cols:
                self.parent._state_transitions[col][index.row()] = np.nan
            self.parent.update_scatter_plots(redraw=False)
            self.parent.update_selected_points(redraw=False)

        # TODO: Any cheaper way to update this?
        #       layoutAboutToBeChanged() and layoutChanged() didn't work
        #       neither did rowCountChanged or rowMoved()
        self.parent.proxy_spectral_models.reset()

        # Update figures.
        self.parent.update_scatter_plots(redraw=False)
        self.parent.update_selected_points(redraw=False)
        self.parent.update_trend_lines(redraw=True)
        
        return value

