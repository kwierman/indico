# -*- coding: utf-8 -*-
##
##
## This file is part of Indico
## Copyright (C) 2002 - 2013 European Organization for Nuclear Research (CERN)
##
## Indico is free software: you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation, either version 3 of the
## License, or (at your option) any later version.
##
## Indico is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Indico.  If not, see <http://www.gnu.org/licenses/>.

import ast
import glob
import inspect
import itertools
import os
import re
import sys
import textwrap
import types
from operator import itemgetter

from indico.web.flask.app import make_app, COMPAT_BLUEPRINTS
from indico.web.flask.util import iter_blueprint_rules, legacy_rule_from_endpoint


def intercept_visit(f):
    def wrapper(self, node):
        f(self, node)
        return self.generic_visit(node)
    return wrapper


# Module(body=[
#     FunctionDef(
#         name='index',
#         args=arguments(args=[Name(id='req', ctx=Param())], vararg=None, kwarg='params', defaults=[]),
#         body=[
#             Return(
#                 value=Call(
#                     func=Attribute(
#                         value=Call(
#                             func=Attribute(
#                                 value=Name(id='conferenceDisplay', ctx=Load()),
#                                 attr='RHConferenceEmail', ctx=Load()
#                             ),
#                             args=[Name(id='req', ctx=Load())],
#                             keywords=[],
#                             starargs=None,
#                             kwargs=None
#                         ),
#                         attr='process', ctx=Load()
#                     ),
#                     args=[Name(id='params', ctx=Load())],
#                     keywords=[],
#                     starargs=None,
#                     kwargs=None
#                 )
#             )
#         ],
#         decorator_list=[]
#     )
# ])

class Walker(ast.NodeVisitor):
    def __init__(self, func_name):
        self.expected_func_name = func_name
        self.data = {}
        self.last_node = None

    @intercept_visit
    def visit_FunctionDef(self, node):
        assert node.name == self.expected_func_name

    @intercept_visit
    def visit_Call(self, node):
        if type(self.last_node).__name__ == 'Return' and node.func.attr == 'process':
            return
        self.data['global'] = node.func.value.id
        self.data['rh_name'] = node.func.attr

    def generic_visit(self, node):
        self.last_node = node
        super(Walker, self).generic_visit(node)


def generate_imports(routes):
    active_routes = (route for route in routes if not route['inactive'])
    for module, alias in sorted(set((route['module'], route['module_alias']) for route in active_routes)):
        yield 'import {0} as {1}'.format(module, alias)


def generate_routes(routes):
    grouped_routes = itertools.groupby(sorted(routes, key=itemgetter('rule')), key=itemgetter('pyfile'))
    for i, (module, module_routes) in enumerate(grouped_routes):
        if i != 0:
            yield '\n'
        yield '# Routes for {0}'.format(module)
        for i, route in enumerate(module_routes):
            if route['inactive']:
                yield '# Inactive: {rule} ({module_alias}.{rh})'.format(**route)
                continue
            if i != 0:
                yield ''
            yield textwrap.dedent('''
                legacy.add_url_rule({rule!r},
                                    {endpoint!r},
                                    rh_as_view({module_alias}.{rh}),
                                    methods=('GET', 'POST'))
            ''').format(**route).strip('\n')


def main():
    app = make_app()

    # Rules which we need to skip because a legacy blueprint already defines them (with a redirect)
    modernized_rules = set(legacy_rule_from_endpoint(rule['endpoint'])
                           for blueprint in COMPAT_BLUEPRINTS
                           for rule in iter_blueprint_rules(blueprint))

    routes = []
    for path in sorted(glob.iglob(os.path.join(app.config['INDICO_HTDOCS'], '*.py'))):
        name = os.path.basename(path)
        module_globals = {}
        execfile(path, module_globals)
        functions = filter(lambda x: isinstance(x[1], types.FunctionType), module_globals.iteritems())
        for func_name, func in functions:
            w = Walker(func_name)
            w.visit(ast.parse(inspect.getsource(func)))
            module_name = module_globals[w.data['global']].__name__
            rh = getattr(module_globals[w.data['global']], w.data['rh_name'])
            base_url = '/' + name
            if func_name == 'index':
                rule = base_url
                endpoint = re.sub(r'\.py$', '', name)
            else:
                rule = base_url + '/' + func_name
                endpoint = '{0}-{1}'.format(re.sub(r'\.py$', '', name), func_name)
            inactive = rule in modernized_rules
            if inactive:
                print 'Skipping rule (found in compat blueprint): ' + rule
            routes.append({
                'rule': rule,
                'endpoint': endpoint,
                'pyfile': name,
                'module': module_name,
                'module_alias': 'mod_rh_' + module_name.split('.')[-1],
                'rh': rh.__name__,
                'inactive': inactive
            })

    if not routes:
        print 'No rules, aborting'
        sys.exit(1)

    with open('indico/web/flask/blueprints/legacy.py', 'w') as f:
        f.write(textwrap.dedent('''
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
            ## along with Indico. If not, see <http://www.gnu.org/licenses/>.

            from flask import Blueprint
            from indico.web.flask.util import rh_as_view
        ''').lstrip('\n'))
        f.write('\n')
        f.writelines(line + '\n' for line in generate_imports(routes))
        f.write('\n')
        f.write(textwrap.dedent('''
            legacy = Blueprint('legacy', __name__)
        '''))
        f.write('\n\n')
        f.writelines(line + '\n' for line in generate_routes(routes))

if __name__ == '__main__':
    main()