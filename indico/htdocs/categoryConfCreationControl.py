# -*- coding: utf-8 -*-
##
##
## This file is part of Indico.
## Copyright (C) 2002 - 2013 European Organization for Nuclear Research (CERN).
##
## Indico is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 3 of the
## License, or (at your option) any later version.
##
## Indico is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Indico;if not, see <http://www.gnu.org/licenses/>.

import MaKaC.webinterface.rh.categoryMod as categoryMod


def index(req, **params):
    return categoryMod.RHCategoryConfCreationControl( req ).process( params )

def setCreateConferenceControl( req, **params ):
    return categoryMod.RHCategorySetConfControl( req ).process( params )

def setNotifyCreation( req, **params ):
    return categoryMod.RHCategorySetNotifyCreation( req ).process( params )
