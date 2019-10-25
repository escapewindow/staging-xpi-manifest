# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import, print_function, unicode_literals

from copy import deepcopy
import json
import os
import time
from datetime import datetime

from taskgraph.config import load_graph_config
from taskgraph.util.schema import validate_schema
from taskgraph.util.vcs import calculate_head_rev, get_repo_path, get_repository_type
from taskgraph.util import yaml
from taskgraph.util.memoize import memoize
from taskgraph.util.readonlydict import ReadOnlyDict
from voluptuous import (
    ALLOW_EXTRA,
    Optional,
    Required,
    Schema,
    Any,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
ROOT = os.path.join(BASE_DIR, 'taskcluster', 'ci')
MANIFEST_PATH = os.path.join(BASE_DIR, "xpi-manifest.yml")


base_schema = Schema({
    Required('xpis'): [{
        Required('name'): basestring,
        Optional('description'): basestring,
        Required('repo-prefix'): basestring,
        Optional('directory'): basestring,
        Optional('active'): bool,
        Optional('private-repo'): bool,
        Required('artifacts'): [basestring],
        Required('addon-type'): Any('system', 'standard'),
        Optional('install-type'): Any('npm', 'yarn'),
        Optional('treeherder-symbol'): basestring,
        Optional('notify'): basestring,
    }],
})


@memoize
def get_manifest():
    rw_manifest = yaml.load_yaml(MANIFEST_PATH)
    graph_config = load_graph_config(ROOT)
    validate_schema(base_schema, deepcopy(rw_manifest), 'Invalid manifest:')
    for xpi_config in rw_manifest['xpis']:
        assert xpi_config['repo-prefix'] in graph_config['taskgraph']['repositories']
        assert '-' not in xpi_config['repo-prefix']
    # any other checks?
    # TODO make read-only recursively
    return ReadOnlyDict(rw_manifest)


def get_xpi_config(xpi_name):
    manifest = get_manifest()
    xpi_configs = [xpi for xpi in manifest["xpis"] if xpi["name"] == xpi_name]
    if len(xpi_configs) != 1:
        raise Exception(
            "Unable to find a single xpi matching name {}: found {}".format(
                input.xpi_name, len(xpi_configs)
            )
        )
    return xpi_configs[0]
