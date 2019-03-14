# -*- coding: utf-8 -*-
#
# Copyright (C) 2019 Frootlab Developers
# Copyright (C) 2013-2019 Patrick Michl
#
# This file is part of Nemoa, https://github.com/frootlab/nemoa
#
#  Nemoa is free software: you can redistribute it and/or modify it under the
#  terms of the GNU General Public License as published by the Free Software
#  Foundation, either version 3 of the License, or (at your option) any later
#  version.
#
#  Nemoa is distributed in the hope that it will be useful, but WITHOUT ANY
#  WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
#  A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#  You should have received a copy of the GNU General Public License along with
#  Nemoa. If not, see <http://www.gnu.org/licenses/>.
#

__copyright__ = '2019 Frootlab Developers'
__license__ = 'GPLv3'
__docformat__ = 'google'
__author__ = 'Frootlab Developers'
__email__ = 'contact@frootlab.org'
__authors__ = ['Patrick Michl <patrick.michl@frootlab.org>']

from flib.base import pkg

def new(*args, **kwds):
    """Create new session instance."""
    # validate configuration
    if not kwds:
        kwds = {'config': {'type': 'base.Session'}}
    elif len(kwds.get('config', {}).get('type', '').split('.')) != 2:
        raise ValueError("configuration is not valid")

    mname, cname = tuple(kwds['config']['type'].split('.'))
    module = pkg.get_submodule(name=mname)
    if not hasattr(module, cname):
        raise NameError(f"class '{mname}.{cname}' is not known")
    return getattr(module, cname)(**kwds)
