# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Apply some defaults and minor modifications to the jobs defined in the github_release
kind.
"""
from __future__ import absolute_import, print_function, unicode_literals

from taskgraph.config import load_graph_config
from taskgraph.transforms.base import TransformSequence
from taskgraph.util.schema import resolve_keyed_by
from xpi_taskgraph.xpi_manifest import get_manifest

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
ROOT = os.path.join(BASE_DIR, "ci")

transforms = TransformSequence()


@transforms.add
def resolve_keys(config, jobs):
    for job in jobs:
        for key in ("worker.github-project", "worker.release-name"):
            resolve_keyed_by(
                job,
                key,
                item_name=job["name"],
                **{
                    'level': config.params["level"],
                }
            )
        yield job


@transforms.add
def build_worker_definition(config, jobs):
    for job in jobs:
        # TODO: this section taken from release_mark_as_shipped
        if not (
            config.params.get('version')
            and config.params.get('xpi_name')
            and config.params.get('build_number')
        ):
            continue

        resolve_keyed_by(
            job, 'scopes', item_name=job['name'],
            **{'level': config.params["level"]}
        )

        job['worker']['release-name'] = '{xpi_name}-{version}-build{build_number}'.format(
            xpi_name=config.params['xpi_name'],
            version=config.params['version'],
            build_number=config.params['build_number']
        )

        # translate input xpi_name to get manifest and graph info
        manifest = get_manifest()
        manifest_config = manifest[config.params['xpi_name']]
        repo_prefix = manifest_config["repo-prefix"]
        graph_config = load_graph_config(ROOT)
        repo_url = graph_config["taskgraph"]["repositories"][repo_prefix]["default-repository"]
        repo = repo_url.split('github.com')[-1]
        repo = repo.strip(':/')

        # TODO: do we need git-revision from the actual manifest source, I think so
        worker_definition = {
            "artifact-map": _build_artifact_map(job),
            "git-tag": config.params["head_tag"].decode("utf-8"),
            "git-revision": config.params["xpi_revision"].decode("utf-8"),
            "github-project": repo,
            "is-prerelease": False
        }

        # TODO: figure out how to specify a tag
        if worker_definition["git-tag"] == "":
            worker_definition["git-tag"] = "TODO"

        dep = job["primary-dependency"]
        worker_definition["upstream-artifacts"] = []
        if "upstream-artifacts" in dep.attributes:
            worker_definition["upstream-artifacts"] = dep.attributes["upstream-artifacts"]

        if "payload" in dep.task and "env" in dep.task["payload"] and "ARTIFACT_PREFIX" in dep.task["payload"]["env"]:
            if not dep.task["payload"]["env"]["ARTIFACT_PREFIX"].startswith("public"):
                scopes = job.setdefault('scopes', [])
                scopes.append(
                    "queue:get-artifact:{}/*".format(dep.task["payload"]["env"]["ARTIFACT_PREFIX"].rstrip('/'))
                )

        job["worker"].update(worker_definition)
        del job["primary-dependency"]
        yield job

def _build_artifact_map(job):
    artifact_map = []
    dep = job["primary-dependency"]

    artifacts = {"paths": dep.attributes["xpis"].values(), "taskId": dep.task["extra"]["parent"]}
    artifact_map.append(artifacts)
    return artifact_map
