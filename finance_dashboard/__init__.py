#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance_dashboard/__init__.py: Package root of Finance Dashboard
#
#  Description:
#  Expose the package version, and nothing else. The FastAPI application,
#  the settings and the loaders are built by finance_dashboard.main,
#  finance_dashboard.config and finance_dashboard.data respectively, and
#  none of them is imported here.
#
#  That emptiness is the point. Importing this package reads no
#  configuration file, resolves no data directory, binds no port and
#  touches no disk, so a tool that only wants the version -- the
#  --version option, a packaging step, a test collecting modules -- pays
#  for none of it and cannot fail on a host where the data directory is
#  absent.
#
#  The version is the release number of the whole repository, which
#  doc/VERSIONS records. It is not the version history of any single
#  module; those live in the header of the module concerned.
#
#  Author: id774 (More info: https://id774.net)
#  Source Code: https://github.com/id774/finance-dashboard
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.9 or later
#  - Standard library only
#
#  Version History:
#  v1.0 2026-07-25
#       Initial release.
#
########################################################################

__version__ = "1.0.1"
