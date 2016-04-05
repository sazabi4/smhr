#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" The radial velocity tab view for the Spectroscopy Made Hard GUI. """

from __future__ import (division, print_function, absolute_import,
                        unicode_literals)

import numpy as np
import os
import sys
import yaml
from PySide import QtCore, QtGui

import mpl
from matplotlib import (gridspec, pyplot as plt)

from smh import (Session, specutils)

__all__ = ["RVTab"]


c = 299792458e-3 # km/s

class RVTab(QtGui.QWidget):


    def __init__(self, parent=None):
        super(RVTab, self).__init__(parent)

        self.parent = parent

        # Create the overall RV tab.
        sp = QtGui.QSizePolicy(
            QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)
        sp.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sp)

        # Create a top-level horizontal layout to contain a matplotlib figure and
        # a vertical layout of settings..
        rv_tab_layout = QtGui.QHBoxLayout(self)
        rv_tab_layout.setContentsMargins(10, 10, 10, 10)

        # This vertical layout will be for input settings.
        rv_settings_vbox = QtGui.QVBoxLayout()
        rv_settings_vbox.setSizeConstraint(QtGui.QLayout.SetMinimumSize)

        # A two-tab setting for 'template' and 'normalization' settings in the
        # radial velocity determination.
        rv_settings_tabs = QtGui.QTabWidget(self)

        sp = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sp.setHorizontalStretch(0)
        sp.setVerticalStretch(0)
        sp.setHeightForWidth(rv_settings_tabs.sizePolicy().hasHeightForWidth())

        rv_settings_tabs.setSizePolicy(sp)
        rv_settings_tabs.setMinimumSize(QtCore.QSize(300, 240))
        rv_settings_tabs.setMaximumSize(QtCore.QSize(300, 240))

        rv_settings_tabs.setMovable(True)
        rv_settings_tabs.setObjectName("rv_settings_tabs")


        # A tab containing template settings.
        template_tab = QtGui.QWidget()
        template_tab.setObjectName("tv_template_tab")

        # TODO: Should template_tab and template_tab_widget actually be one entity?
        template_tab_widget = QtGui.QWidget(template_tab)
        template_tab_widget.setGeometry(QtCore.QRect(0, 0, 300, 210))

        template_tab_layout = QtGui.QVBoxLayout(template_tab_widget)
        template_tab_layout.setSizeConstraint(QtGui.QLayout.SetDefaultConstraint)
        template_tab_layout.setContentsMargins(10, 10, 10, 10)

        # Add a label at the top of the template settings tab.
        label = QtGui.QLabel(template_tab_widget)
        label.setMaximumSize(QtCore.QSize(240, 16777215))
        label.setText("Template spectrum filename:")
        template_tab_layout.addWidget(label)

        # Inner horizontal layout for the template path and select.
        template_path_layout = QtGui.QHBoxLayout()

        # Template path line edit (read-only).
        self.template_path = QtGui.QLineEdit(template_tab_widget)
        self.template_path.setObjectName("rv_template_path")
        self.template_path.setReadOnly(True)
        template_path_layout.addWidget(self.template_path)

        # Template path select button.
        rv_select_template_btn = QtGui.QPushButton(template_tab_widget)
        rv_select_template_btn.setObjectName("rv_select_template_btn")
        rv_select_template_btn.setText("...")
        template_path_layout.addWidget(rv_select_template_btn)

        # Add this horizontal layout to the template tab.
        template_tab_layout.addLayout(template_path_layout)

        # Add a label for the wavelength regions
        label = QtGui.QLabel(template_tab_widget)
        label.setMaximumSize(QtCore.QSize(240, 16777215))
        label.setText("Wavelength region:")
        template_tab_layout.addWidget(label)

        # Wavelength region for CCF.
        wl_region_layout = QtGui.QHBoxLayout()
        self.wl_region = QtGui.QComboBox(template_tab_widget)
        self.wl_region.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToContents)
        self.wl_region.setObjectName("rv_wl_region")
        wl_region_layout.addWidget(self.wl_region)

        # Edit button for the wavelength regions.
        rv_wl_region_edit = QtGui.QPushButton(template_tab_widget)
        rv_wl_region_edit.setMaximumSize(QtCore.QSize(80, 16777215))
        rv_wl_region_edit.setObjectName("rv_wl_region_edit")
        wl_region_layout.addWidget(rv_wl_region_edit)
        template_tab_layout.addLayout(wl_region_layout)
        rv_wl_region_edit.setText("Edit list")
        
        # Add a horizontal line.
        hr = QtGui.QFrame(template_tab_widget)
        hr.setFrameShape(QtGui.QFrame.HLine)
        hr.setFrameShadow(QtGui.QFrame.Sunken)
        template_tab_layout.addWidget(hr)

        # Add a flexible spacer.
        template_tab_layout.addItem(QtGui.QSpacerItem(
            20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding))

        # Add a cross-correlate button.
        rv_cross_correlate_btn = QtGui.QPushButton(template_tab_widget)
        rv_cross_correlate_btn.setObjectName("rv_cross_correlate_btn")
        rv_cross_correlate_btn.setText("Cross-correlate")
        template_tab_layout.addWidget(rv_cross_correlate_btn)

        # End of the template tab.
        rv_settings_tabs.addTab(template_tab, "Template")

        # Start the normalization tab.
        norm_tab = QtGui.QWidget()
        norm_tab.setObjectName("rv_normalization_tab")

        norm_tab_widget = QtGui.QWidget(norm_tab)
        norm_tab_widget.setGeometry(QtCore.QRect(0, 0, 300, 210))

        norm_tab_layout = QtGui.QVBoxLayout(norm_tab_widget)
        norm_tab_layout.setContentsMargins(10, 10, 10, 10)

        # Start the grid layout for the normalization tab.
        norm_tab_grid_layout = QtGui.QGridLayout()


        # Normalization function.
        label = QtGui.QLabel(norm_tab_widget)
        label.setText("Function")
        norm_tab_grid_layout.addWidget(label, 0, 0, 1, 1)
        
        # Put the normalization function combo box in a horizontal layout with a
        # spacer.
        hbox = QtGui.QHBoxLayout()
        hbox.addItem(QtGui.QSpacerItem(
            40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum))
        self.norm_function = QtGui.QComboBox(norm_tab_widget)
        self.norm_function.setObjectName("rv_norm_function")
        hbox.addWidget(self.norm_function)
        norm_tab_grid_layout.addLayout(hbox, 0, 1, 1, 1)

        norm_functions = ("polynomial", "spline")
        for each in norm_functions:
            self.norm_function.addItem(each.title())


        # Normalization function order.
        label = QtGui.QLabel(norm_tab_widget)
        label.setText("Order")
        norm_tab_grid_layout.addWidget(label, 1, 0, 1, 1)
        
        # Put the normalization order combo box in a horizontal layout with a spacer
        hbox = QtGui.QHBoxLayout()
        hbox.addItem(QtGui.QSpacerItem(
            40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum))
        self.norm_order = QtGui.QComboBox(norm_tab_widget)
        self.norm_order.setMaximumSize(QtCore.QSize(50, 16777215))
        self.norm_order.setObjectName("rv_norm_order")
        hbox.addWidget(self.norm_order)
        norm_tab_grid_layout.addLayout(hbox, 1, 1, 1, 1)

        norm_orders = range(1, 10)
        for order in norm_orders:
            self.norm_order.addItem("{0:.0f}".format(order))


        # Maximum number of iterations.
        label = QtGui.QLabel(norm_tab_widget)
        label.setText("Maximum iterations")
        norm_tab_grid_layout.addWidget(label, 2, 0, 1, 1)

        # Put the maxium number of iterations in a horizontal layout with a spacer.
        hbox = QtGui.QHBoxLayout()
        hbox.addItem(QtGui.QSpacerItem(
            40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum))
        self.norm_max_iter = QtGui.QComboBox(norm_tab_widget)
        self.norm_max_iter.setMaximumSize(QtCore.QSize(50, 16777215))
        self.norm_max_iter.setObjectName("rv_norm_max_iter")
        hbox.addWidget(self.norm_max_iter)
        norm_tab_grid_layout.addLayout(hbox, 2, 1, 1, 1)

        norm_max_iters = range(1, 10)
        for iteration in norm_max_iters:
            self.norm_max_iter.addItem("{0:.0f}".format(iteration))


        # Low sigma clipping.
        label = QtGui.QLabel(norm_tab_widget)
        label.setText("Low sigma clip")
        norm_tab_grid_layout.addWidget(label, 3, 0, 1, 1)

        # Put the low sigma line edit box in a horizontal layout with a spacer.
        hbox = QtGui.QHBoxLayout()
        hbox.setContentsMargins(-1, -1, 5, -1)
        hbox.addItem(QtGui.QSpacerItem(
            40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum))
        self.norm_low_sigma = QtGui.QLineEdit(norm_tab_widget)
        self.norm_low_sigma.setMaximumSize(QtCore.QSize(40, 16777215))
        self.norm_low_sigma.setAlignment(QtCore.Qt.AlignCenter)
        self.norm_low_sigma.setObjectName("rv_norm_low_sigma")
        self.norm_low_sigma.setValidator(
            QtGui.QDoubleValidator(0, 1000, 2, self.norm_low_sigma))
        hbox.addWidget(self.norm_low_sigma)
        norm_tab_grid_layout.addLayout(hbox, 3, 1, 1, 1)


        # High sigma clipping.
        label = QtGui.QLabel(norm_tab_widget)
        label.setText("High sigma clip")
        norm_tab_grid_layout.addWidget(label, 4, 0, 1, 1)

        # Put the high sigma line edit box in a horizontal layout with a spacer.
        hbox = QtGui.QHBoxLayout()
        hbox.setContentsMargins(-1, -1, 5, -1)
        hbox.addItem(QtGui.QSpacerItem(
            40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum))
        self.norm_high_sigma = QtGui.QLineEdit(norm_tab_widget)
        self.norm_high_sigma.setMaximumSize(QtCore.QSize(40, 16777215))
        self.norm_high_sigma.setAlignment(QtCore.Qt.AlignCenter)
        self.norm_high_sigma.setObjectName("rv_norm_high_sigma")
        self.norm_high_sigma.setValidator(
            QtGui.QDoubleValidator(0, 1000, 2, self.norm_high_sigma))
        hbox.addWidget(self.norm_high_sigma)
        norm_tab_grid_layout.addLayout(hbox, 4, 1, 1, 1)
        

        # Knot spacing.
        label = QtGui.QLabel(norm_tab_widget)
        norm_tab_grid_layout.addWidget(label, 5, 0, 1, 1)
        label.setText(u"Knot spacing (Å)")

        # Put the knot spacing lint edit box in a horizontal layout with a spacer
        hbox = QtGui.QHBoxLayout()
        hbox.setContentsMargins(-1, -1, 5, -1)
        hbox.addItem(QtGui.QSpacerItem(
            40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum))
        self.norm_knot_spacing = QtGui.QLineEdit(norm_tab_widget)
        self.norm_knot_spacing.setMaximumSize(QtCore.QSize(40, 16777215))
        self.norm_knot_spacing.setAlignment(QtCore.Qt.AlignCenter)
        self.norm_knot_spacing.setObjectName("rv_norm_knot_spacing")
        self.norm_knot_spacing.setValidator(
            QtGui.QIntValidator(0, 10000, self.norm_knot_spacing))
        hbox.addWidget(self.norm_knot_spacing)
        norm_tab_grid_layout.addLayout(hbox, 5, 1, 1, 1)

        # End of the grid in the normalization tab.
        norm_tab_layout.addLayout(norm_tab_grid_layout)
        norm_tab_layout.addItem(QtGui.QSpacerItem(
            20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding))

        rv_settings_tabs.addTab(norm_tab, "Order normalization")
        rv_settings_vbox.addWidget(rv_settings_tabs)


        # Horizontal layout for the radial velocity measured/corrected.
        hbox = QtGui.QHBoxLayout()
        hbox.setSizeConstraint(QtGui.QLayout.SetMaximumSize)
        hbox.setContentsMargins(10, 0, 10, -1)

        label = QtGui.QLabel(self)
        label.setText("Radial velocity:")
        hbox.addWidget(label)

        # Radial velocity measured.
        self.rv_applied = QtGui.QLineEdit(self)
        sp = QtGui.QSizePolicy(QtGui.QSizePolicy.Ignored, QtGui.QSizePolicy.Fixed)
        sp.setHorizontalStretch(0)
        sp.setVerticalStretch(0)
        sp.setHeightForWidth(self.rv_applied.sizePolicy().hasHeightForWidth())
        self.rv_applied.setSizePolicy(sp)
        self.rv_applied.setMinimumSize(QtCore.QSize(50, 16777215))
        self.rv_applied.setAlignment(QtCore.Qt.AlignCenter)
        self.rv_applied.setObjectName("rv_applied")
        self.rv_applied.setValidator(
            QtGui.QDoubleValidator(-1e6, 1e6, 2, self.rv_applied))
        hbox.addWidget(self.rv_applied)

        # Units/uncertainty label.
        label = QtGui.QLabel(self)
        label.setObjectName("rv_measured_units_label")
        label.setText("km/s")
        hbox.addWidget(label)

        # Correct for radial velocity button.
        rv_correct_btn = QtGui.QPushButton(self)
        rv_correct_btn.setObjectName("rv_correct_btn")
        rv_correct_btn.setText("Correct")
        hbox.addWidget(rv_correct_btn)
        rv_settings_vbox.addLayout(hbox)


        # Add a spacer until the big button.
        rv_settings_vbox.addItem(QtGui.QSpacerItem(
            20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding))


        # The cross-correlate and correct button.
        rv_ccc_btn = QtGui.QPushButton(self)
        sp = QtGui.QSizePolicy(
            QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Fixed)
        sp.setHorizontalStretch(0)
        sp.setVerticalStretch(0)
        sp.setHeightForWidth(rv_ccc_btn.sizePolicy().hasHeightForWidth())
        rv_ccc_btn.setSizePolicy(sp)
        rv_ccc_btn.setMinimumSize(QtCore.QSize(300, 0))
        rv_ccc_btn.setMaximumSize(QtCore.QSize(300, 16777215))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        rv_ccc_btn.setFont(font)
        rv_ccc_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        rv_ccc_btn.setDefault(True)
        rv_ccc_btn.setObjectName("rv_ccc_btn")
        rv_ccc_btn.setText("Cross-correlate and correct")
        if sys.platform == "darwin":
            rv_ccc_btn.setStyleSheet('QPushButton {color: white}')

        rv_settings_vbox.addWidget(rv_ccc_btn)

        rv_tab_layout.addLayout(rv_settings_vbox)

        # Create a matplotlib widget.
        blank_widget = QtGui.QWidget(self)
        sp = QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sp.setHorizontalStretch(0)
        sp.setVerticalStretch(0)
        sp.setHeightForWidth(blank_widget.sizePolicy().hasHeightForWidth())
        blank_widget.setSizePolicy(sp)
        blank_widget.setObjectName("blank_widget")

        self.rv_plot = mpl.MPLWidget(blank_widget)
        layout = QtGui.QVBoxLayout(blank_widget)        
        layout.addWidget(self.rv_plot, 1)

        rv_tab_layout.addWidget(blank_widget)


        gs = gridspec.GridSpec(3, 1, height_ratios=[3, 1, 1])
        self.ax_order = self.rv_plot.figure.add_subplot(gs[0])
        self.ax_order_norm = self.rv_plot.figure.add_subplot(gs[1])
        self.ax_ccf = self.rv_plot.figure.add_subplot(gs[2])

        # Ticks, etc
        self.ax_order.set_xticklabels([])
        self.ax_order_norm.set_yticks([0, 1])
        self.ax_order_norm.set_ylim(0, 1.2)

        self.ax_order_norm.set_xlabel(u"Wavelength (Å)")
        self.ax_order.set_ylabel("Flux")

        # Draw an initial line for data and continuum.
        self.ax_order.plot([], [], c='k', drawstyle='steps-mid')
        self.ax_order.plot([], [], c='r', zorder=2)
        self.ax_order.set_ylim([0, 1])

        self.ax_order_norm.axhline(1, linestyle=":", c="#666666", zorder=-1)
        self.ax_order_norm.plot([], [], c='k', drawstyle='steps-mid')
        self.ax_order_norm.plot([], [], c='b') # Template.


        self.ax_ccf.plot([], [], c='k')
        self.ax_ccf.set_xlabel("Velocity (km/s)")
        self.ax_ccf.set_ylabel("CCF")
        self.ax_ccf.set_yticks([0, 0.5, 1.0])

        
        # Keep an input cache.
        self._populate_widgets()

        # Create signals for buttons.
        rv_cross_correlate_btn.clicked.connect(self.cross_correlate) 
        rv_correct_btn.clicked.connect(self.correct_radial_velocity)
        rv_ccc_btn.clicked.connect(self.cross_correlate_and_correct)

        # Create signals for when any of these things change.
        rv_select_template_btn.clicked.connect(self.select_template)
        self.wl_region.currentIndexChanged.connect(self.update_wl_region)
        self.norm_low_sigma.textChanged.connect(
            self.update_normalization_low_sigma)
        self.norm_high_sigma.textChanged.connect(
            self.update_normalization_high_sigma)
        self.norm_knot_spacing.textChanged.connect(
            self.update_normalization_knot_spacing)
        self.norm_function.currentIndexChanged.connect(
            self.update_normalization_function)
        self.norm_order.currentIndexChanged.connect(
            self.update_normalization_order)
        self.norm_max_iter.currentIndexChanged.connect(
            self.update_normalization_max_iterations)

        # Update the background to show whether certain items are valid.
        self.norm_low_sigma.textChanged.connect(self.check_state)
        self.norm_high_sigma.textChanged.connect(self.check_state)
        self.norm_knot_spacing.textChanged.connect(self.check_state)
        
        # Draw the template straight up if we can.
        self.draw_template(refresh=True)

        return None



    def check_state(self, *args, **kwargs):
        """
        Update the background color of a QLineEdit object based on whether the
        input is valid.
        """

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



    def _populate_widgets(self):
        """
        Populate widgets with values from the current SMH session, or the
        default SMH settings file.
        """



        # TODO: Put the default I/O somewhere else since it will be common to many
        #       tabs.
        with open(Session._default_settings_path, "rb") as fp:
            defaults = yaml.load(fp)["rv"]

        # Template filename.
        self.template_path.setReadOnly(False)
        self.template_path.setText(defaults["template_spectrum"])
        self.template_path.setReadOnly(True)

        # Wavelength regions.
        for each in defaults["wavelength_regions"]:
            self.wl_region.addItem(u"{0:.0f}-{1:.0f} Å".format(*each))

        # Normalization function.
        norm_functions = [self.norm_function.itemText(i).lower() \
            for i in range(self.norm_function.count())]
        self.norm_function.setCurrentIndex(norm_functions.index(
            defaults["normalization"]["function"].lower()))

        # Normalization order.
        norm_orders = [int(self.norm_order.itemText(i)) \
            for i in range(self.norm_order.count())]
        self.norm_order.setCurrentIndex(norm_orders.index(
            defaults["normalization"]["order"]))

        # Normalization maximum iterations.
        norm_max_iters = [int(self.norm_max_iter.itemText(i)) \
            for i in range(self.norm_max_iter.count())]
        self.norm_max_iter.setCurrentIndex(norm_max_iters.index(
            defaults["normalization"]["max_iterations"]))

        # Normalization low and high sigma clip:
        self.norm_low_sigma.setText(
            str(defaults["normalization"]["low_sigma_clip"]))
        self.norm_high_sigma.setText(
            str(defaults["normalization"]["high_sigma_clip"]))
        
        # Normalization knot spacing.
        self.norm_knot_spacing.setText(
            str(defaults["normalization"]["knot_spacing"]))

        # The cache allows us to store things that won't necessarily go into the
        # session, but will update views, etc. For example, previewing continua
        # before actually using it in cross-correlation, etc.
        self._cache = {
            "input": defaults.copy()
        }

        # Wavelength regions should just be a single range.
        self._cache["input"]["wavelength_region"] \
            = self._cache["input"]["wavelength_regions"][0]
        del self._cache["input"]["wavelength_regions"]
        return None


    def update_normalization_function(self):
        """ Update the normalization function. """
        self._cache["input"]["normalization"]["function"] \
            = self.norm_function.currentText()
        self.fit_and_redraw_normalized_order()


    def update_normalization_order(self):
        """ Update the normalization order. """
        self._cache["input"]["normalization"]["order"] \
            = int(self.norm_order.currentText())
        self.fit_and_redraw_normalized_order()


    def update_normalization_max_iterations(self):
        """ Update the maximum number of iterations during normalization. """
        self._cache["input"]["normalization"]["max_iterations"] \
            = int(self.norm_max_iter.currentText())
        self.fit_and_redraw_normalized_order()


    def update_normalization_low_sigma(self):
        """ Update the low sigma clipping during normalization. """
        low_sigma = self.norm_low_sigma.text()
        if low_sigma:
            self._cache["input"]["normalization"]["low_sigma_clip"] \
                = float(low_sigma)
            self.fit_and_redraw_normalized_order()


    def update_normalization_high_sigma(self):
        """ Update the high sigma clipping during normalization. """
        high_sigma = self.norm_high_sigma.text()
        if high_sigma:
            self._cache["input"]["normalization"]["high_sigma_clip"] \
                = float(high_sigma)
            self.fit_and_redraw_normalized_order()


    def update_normalization_knot_spacing(self):
        """ Update the knot spacing used for normalization. """
        knot_spacing = self.norm_knot_spacing.text()
        if knot_spacing:
            self._cache["input"]["normalization"]["knot_spacing"] \
                = float(knot_spacing)
            self.fit_and_redraw_normalized_order()



    def fit_and_redraw_normalized_order(self):
        """
        Fit and redraw the continuum, and the normalized order.
        """

        self.fit_continuum()
        self.redraw_continuum()
        self.redraw_normalized_order(True)
        return None


    def fit_continuum(self):
        """
        Fit and draw the continuum.
        """

        self._cache["normalized_order"], self._cache["continuum"], _, __ \
            = self._cache["overlap_order"].fit_continuum(full_output=True,
                **self._cache["input"]["normalization"])
        return None


    def redraw_continuum(self, refresh=False):
        """
        Redraw the continuum.

        :param refresh: [optional]
            Force the figure to update.
        """

        self.ax_order.lines[1].set_data([
            self._cache["overlap_order"].dispersion,
            self._cache["continuum"]
        ])
        if refresh:
            self.rv_plot.draw()
        return None


    def redraw_normalized_order(self, refresh=False):
        """
        Redraw the normalized order.

        :param refresh: [optional]
            Force the figure to update.
        """

        # Redshift the normalized order by the 'RV-applied', if it exists.
        try:
            rv_applied = self.parent.session.metadata["rv"]["rv_applied"]
        except (AttributeError, KeyError):
            rv_applied = 0

        self.ax_order_norm.lines[1].set_data([
            self._cache["normalized_order"].dispersion * (1 - rv_applied/c),
            self._cache["normalized_order"].flux,
        ])
        self.ax_order_norm.set_xlim(self._cache["input"]["wavelength_region"])

        if refresh:
            self.rv_plot.draw()

        return None


    def select_template(self):
        """
        Select the template spectrum filename from disk.
        """

        path, _ = QtGui.QFileDialog.getOpenFileName(self.parent,
            caption="Select template spectrum", dir="", filter="*.fits")
        if not path: return

        # Set the text.
        self.template_path.setReadOnly(False)
        self.template_path.setText(path)
        self.template_path.setReadOnly(True)

        # Update the data cache.
        self._cache["input"]["template_spectrum"] = path

        # Update the figure containing the template.
        self.draw_template(refresh=True)
        
        return None


    def cross_correlate(self):
        """
        Normalize and cross-correlate the observed spectrum with the template.
        """
        
        kwds = self._cache["input"].copy()
        kwds["normalization_kwargs"] = kwds.pop("normalization")

        # Perform the cross-correlation.
        rv, rv_uncertainty = self.parent.session.rv_measure(**kwds)

        # Update the measured radial velocity in the GUI.
        self.rv_applied.setText("{0:+.1f}".format(rv))

        # Draw the CCF in the bottom panel.
        self.redraw_ccf(refresh=True)

        return None


    def redraw_ccf(self, refresh=False):
        """
        Draw the CCF stored in the session.
        """

        try:
            v, ccf = self.parent.session.metadata["rv"]["ccf"]
        except (AttributeError, KeyError):
            return None

        self.ax_ccf.lines[0].set_data([v, ccf])

        rv_measured = self.parent.session.metadata["rv"]["rv_measured"]
        
        self.ax_ccf.set_xlim(rv_measured - 1000, rv_measured + 1000)
        self.ax_ccf.set_ylim(0, 1.2)

        self.ax_ccf.axvline(rv_measured, c='r')

        if refresh:
            self.rv_plot.draw()
        return None


    def correct_radial_velocity(self):
        """
        Correct the radial velocity of the observed spectra.
        """

        self.parent.session.rv_correct(self.rv_applied.text())

        # Redshift the normalized order.
        self.redraw_normalized_order(True)

        # Enable and update the normalization tab.
        self.parent.tabs.setTabEnabled(self.parent.tabs.indexOf(self) + 1, True)
        self.parent.normalization_tab.update_rv_applied()

        return None


    def cross_correlate_and_correct(self):
        """
        Normalize and cross-correlate the observed spectrum with a template,
        then correct the observed spectrum with that velocity.
        """

        self.cross_correlate()
        self.correct_radial_velocity()

        return None


    def update_from_new_session(self):

        # Update cache.
        # Update plots.

        self.draw_template()
        self.update_wl_region()
        self.rv_plot.draw()


    def update_wl_region(self):
        """
        Re-draw the order selected and the continuum fit, as well as the preview
        of the normalized spectrum.
        """

        if self.parent.session is None: return

        # Parse and cache the wavelength region.
        wavelength_region = [float(_) \
            for _ in self.wl_region.currentText().split(" ")[0].split("-")]
        self._cache["input"]["wavelength_region"] = wavelength_region

        # Get the right order.
        self._cache["overlap_order"], _, __ = \
            self.parent.session._get_overlap_order([wavelength_region])

        # Draw this order in the top axes.
        self.ax_order.lines[0].set_data([
            self._cache["overlap_order"].dispersion,
            self._cache["overlap_order"].flux,
        ])

        # Update the limits for this axis.
        self.ax_order.set_xlim(wavelength_region)
        flux_limits = (
            np.nanmin(self._cache["overlap_order"].flux),
            np.nanmax(self._cache["overlap_order"].flux)
        )
        self.ax_order.set_ylim(
            flux_limits[0],
            flux_limits[1] + (np.ptp(flux_limits) * 0.10)
        )

        # TODO: This may require some updating.
        print("Assuming that the session has not just been loaded and it has a CCF/norm order, etc")

        # Update the continuum fit.
        self.fit_and_redraw_normalized_order()

        return None



    def draw_template(self, refresh=False):
        """
        Draw the template spectrum in the figure.
        """

        path = self.template_path.text()
        if not os.path.exists(path): return

        template = specutils.Spectrum1D.read(path)
        self.ax_order_norm.lines[2].set_data([
            template.dispersion,
            template.flux
        ])

        if refresh:
            self.rv_plot.draw()

        return None
