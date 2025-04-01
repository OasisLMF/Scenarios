Impact Forecasting European Windstorm Model
Event Response Oasis Package

Overview

Impact Forecasting European Windstorm Event Response is tool to address in-season scenario footprints when a significant storm hits Europe.

This package contains data for two recent storms which hit Europe: a powerful storm named Ciarán that hit Western Europe on November 1-2, and a low-pressure system named Domingos that affected parts of Western Europe on November 4-7.

Hazard footprints are based on pan-European measured station data provided by the UK Met Office. To account for the uncertainty of the wind field, three different footprints are created for each event. The number of nearby stations used to interpolate the measured point data into the hazard grid is set to 15 (Footprint 1), 30 (Footprint 2) and 40 (Footprint 3), resulting in progressive smoothing of the wind field.


Details
* supported OED Peril code: ZST
* supported coverage types: Building, Contents, Business Interruption
* primary modifiers
	* Occupancy Code
* geographic scope: Austria (Country Code AT), Belgium (BE), Czechia (CZ), Denmark (DE), Finland (FI), France (FR), Germany (DE), Ireland (IE), Luxembourg (LU), Netherlands (NL), Norway (NO), Poland (PL), Slovakia (SK), Sweden (SE), United Kingdom (UK)
* geographic schemes
	* Postal Code
	* District: GeogSchemeX = "IFDIS"
	* Municipality: GeogSchemeX = "IFMUN"
	* State: GeogSchemeX = "IFSTA"
	* Cresta: GeogSchemeX = "CRL"