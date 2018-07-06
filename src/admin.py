from tornado.gen import coroutine, Return

import common.admin as a

from model.apps import NoSuchApplicationError, NoSuchApplicationVersionError, ConfigApplicationError
from model.builds import NoSuchBuildError, ConfigBuildError

from common.environment import EnvironmentClient, AppNotFound
from common.validate import validate
from common.deployment import DeploymentMethods, DeploymentError
from common.internal import Internal, InternalError

import json
import tempfile
import os
import math


class DeployBuildController(a.UploadAdminController):
    def __init__(self, app, token):
        super(DeployBuildController, self).__init__(app, token)
        self.deployment = None
        self.tmp_file = None
        self.f = None
        self.build_id = None
        self.switch_default = None

    @coroutine
    def get(self, app_name):
        environment_client = EnvironmentClient(self.application.cache)

        try:
            app = yield environment_client.get_app_info(app_name)
        except AppNotFound as e:
            raise a.ActionError("App was not found.")

        result = {
            "app_name": app_name,
            "app_id": app.id,
            "app_title": app.title
        }

        raise a.Return(result)

    def render(self, data):
        return [
            a.breadcrumbs([
                a.link("apps", "Applications"),
                a.link("app", data["app_title"], app_name=self.context.get("app_name"))
            ], "Deploy New Configuration"),
            a.file_upload(
                "Deploy a new configuration",
                "deploy_build", fields={
                    "comment": a.field(
                        "Please describe this configuration shortly. A good "
                        "comment will help to figure out the right configuration if needed.",
                        "text", "primary", "non-empty"),
                    "switch_default": a.field(
                        "Switch default build for <b>{0}</b> to the new one".format(data["app_title"]),
                        "switch", "primary"),
                }, data=data),
            a.links("Navigate", [
                a.link("app", "Go back", icon="chevron-left", app_name=self.context.get("app_name")),
                a.link("app_settings", "Application Settings", icon="cogs", app_name=self.context.get("app_name")),
                a.link("/environment/app", "Manage app '{0}' at 'Environment' service.".format(data["app_name"]),
                       icon="link text-danger", record_id=data["app_id"]),
            ])
        ]

    @coroutine
    def receive_started(self, filename, args):
        app_name = self.context.get("app_name")

        try:
            comment = args["comment"]
        except KeyError:
            raise a.ActionError("Missing some fields")

        if len(comment) < 3:
            raise a.ActionError("Comment field should be at least 3 characters long")

        self.switch_default = args.get("switch_default", False)

        environment_client = EnvironmentClient(self.application.cache)
        apps = self.application.apps
        builds = self.application.builds

        try:
            yield environment_client.get_app_info(app_name)
        except AppNotFound:
            raise a.ActionError("App was not found.")

        try:
            settings = yield apps.get_application(self.gamespace, app_name)
        except NoSuchApplicationError:
            raise a.ActionError("Application deployment is not configured")
        except ConfigApplicationError as e:
            raise a.ActionError(e.message)

        deployment_method = settings.deployment_method
        deployment_data = settings.deployment_data

        self.deployment = DeploymentMethods.get(deployment_method)()
        self.deployment.load(deployment_data)

        self.tmp_file = tempfile.mkstemp()
        sys_fd, key_path = self.tmp_file
        self.f = open(key_path, "w")

        try:
            self.build_id = yield builds.create_build(self.gamespace, app_name, comment, self.token.account)
        except ConfigBuildError as e:
            raise a.ActionError(e.message)

    @coroutine
    def receive_completed(self):
        app_name = self.context.get("app_name")

        if self.tmp_file and self.deployment and self.f and self.build_id:
            sys_fd, key_path = self.tmp_file
            self.f.close()

            try:
                builds = self.application.builds

                try:
                    url = yield self.deployment.deploy(self.gamespace, key_path, app_name,
                                                       str(self.gamespace) + "_" + str(self.build_id))
                except DeploymentError as e:
                    yield builds.delete_build(self.gamespace, self.build_id)
                    raise a.ActionError(e.message)

                try:
                    yield builds.update_build_url(self.gamespace, self.build_id, app_name, url)
                except ConfigBuildError as e:
                    raise a.ActionError(e.message)

                if self.switch_default:

                    apps = self.application.apps
                    try:
                        yield apps.update_default_build(self.gamespace, app_name, self.build_id)
                    except ConfigApplicationError as e:
                        raise a.Redirect("app",
                                         message="Deployed, but failed to update default build: {0}".format(e.message),
                                         app_name=app_name)

            finally:
                os.close(sys_fd)

            raise a.Redirect("app", message="Build has been deployed", app_name=app_name)

    @coroutine
    def receive_data(self, chunk):
        if self.f:
            self.f.write(chunk)


class ApplicationController(a.AdminController):
    BUILDS_PER_PAGE = 10

    @coroutine
    @validate(app_name="str_name", build_page="int")
    def get(self, app_name, build_page=1):

        environment_client = EnvironmentClient(self.application.cache)
        apps = self.application.apps
        builds_data = self.application.builds

        try:
            app = yield environment_client.get_app_info(app_name)
        except AppNotFound as e:
            raise a.ActionError("App was not found.")

        versions = app.versions

        try:
            app_settings = yield apps.get_application(self.gamespace, app_name)
        except NoSuchApplicationError:
            app_settings = None
            deployment_configured = False
            default_build = None
        except ConfigApplicationError as e:
            raise a.ActionError(e.message)
        else:
            deployment_configured = True
            default_build = app_settings.default_build

        try:
            build_items, builds = yield builds_data.list_builds_pages(
                self.gamespace, app_name,
                limit=ApplicationController.BUILDS_PER_PAGE,
                offset=(ApplicationController.BUILDS_PER_PAGE * (build_page - 1)))
        except ConfigBuildError as e:
            raise a.ActionError(e.message)

        build_pages = int(math.ceil(float(build_items) / float(ApplicationController.BUILDS_PER_PAGE)))

        author_ids = set()
        for build in builds:
            build.author_name = str(build.author)
            author_ids.add(build.author)

        internal = Internal()

        try:
            profiles = yield internal.send_request(
                "profile", "mass_profiles",
                accounts=author_ids,
                gamespace=self.gamespace,
                action="get_public",
                profile_fields=["name"])
        except InternalError as e:
            pass  # well
        else:
            for build in builds:
                profile = profiles.get(str(build.author))
                if profile:
                    build.author_name = profile.get("name")

        try:
            app_versions = yield apps.list_application_versions(self.gamespace, app_name)
        except ConfigApplicationError as e:
            raise a.ActionError(e.message)
        else:
            version_builds = {
                v.application_version: v
                for v in app_versions
            }

        result = {
            "app_name": app_name,
            "app_id": app.id,
            "app_title": app.title,
            "versions": versions,
            "deployment_configured": deployment_configured,
            "builds": builds,
            "app_settings": app_settings,
            "default_build": default_build,
            "version_builds": version_builds,
            "build_pages": build_pages,
            "default_build_title": "Build {0}".format(default_build) if default_build else "Unset",
        }

        raise a.Return(result)

    @coroutine
    def update_default_configuration(self):
        app_name = self.context.get("app_name")
        build_id = self.context.get("build_id")

        environment_client = EnvironmentClient(self.application.cache)
        apps = self.application.apps

        try:
            yield environment_client.get_app_info(app_name)
        except AppNotFound:
            raise a.ActionError("App was not found.")

        try:
            yield apps.update_default_build(self.gamespace, app_name, build_id)
        except ConfigApplicationError as e:
            raise a.ActionError(e.message)

        raise a.Redirect(
            "app", message="Default configuration has been updated",
            app_name=app_name)

    @coroutine
    def unset_default_configuration(self):
        app_name = self.context.get("app_name")

        environment_client = EnvironmentClient(self.application.cache)
        apps = self.application.apps

        try:
            yield environment_client.get_app_info(app_name)
        except AppNotFound:
            raise a.ActionError("App was not found.")

        try:
            yield apps.unset_default_build(self.gamespace, app_name)
        except ConfigApplicationError as e:
            raise a.ActionError(e.message)

        raise a.Redirect(
            "app", message="Default configuration has been unset",
            app_name=app_name)

    def render(self, data):
        r = [
            a.breadcrumbs([
                a.link("apps", "Applications")
            ], data["app_title"])
        ]

        if data["deployment_configured"]:
            vb = data["version_builds"]

            r.extend([
                a.links("Deploy", [
                    a.link("deploy_build", "Deploy a new configuration", icon="upload",
                           app_name=self.context.get("app_name"))
                ]),
                a.links("Application '{0}' versions".format(data["app_title"]), links=[
                    a.link("app_version", v_name, icon="tags",
                           badge="b.{0}".format(vb[v_name].build) if v_name in vb else None,
                           app_name=self.context.get("app_name"),
                           app_version=v_name) for v_name, v_id in data["versions"].iteritems()
                ])
            ])

            if data["default_build"]:
                r.append(a.form("Default configuration", fields={
                    "default_build_title": a.field("Default configuration", "status", "info")
                }, methods={
                    "unset_default_configuration": a.method(
                        "Unset default configuration", "danger",
                        danger="Once unset, if version is not configured, "
                               "the user would not be able to download any configuration.")
                }, data=data))
            else:
                r.append(a.notice(
                    "No default configuration", "Default configuration for the application is not set. "
                                                "Therefore, if not set per application version, users would not "
                                                "be able to download any configuration."))

            r.extend([
                a.content("Recent Configuration Builds", headers=[
                    {"id": "actions", "title": "Actions"},
                    {"id": "build_id", "title": "Build ID"},
                    {"id": "comment", "title": "Comment"},
                    {"id": "author", "title": "Author"},
                    {"id": "date", "title": "Upload Date"},
                    {"id": "download", "title": "Download"},
                ], items=[
                    {
                        "actions": [
                            a.status("Default Configuration", "success", "check")
                            if data["default_build"] == build.build_id else
                            a.button("app", "Use This", "primary", _method="update_default_configuration",
                                     build_id=build.build_id, app_name=self.context.get("app_name"))
                        ],
                        "build_id": build.build_id,
                        "date": str(build.date),
                        "comment": build.comment,
                        "author": [
                            a.link("/profile/profile", build.author_name, icon="user", account=build.author)
                        ],
                        "download": [
                            a.link(build.url, "", icon="download")
                        ]
                    }
                    for build in data["builds"]
                ], style="default")
            ])

            if data["build_pages"] > 1:
                r.append(a.pages(data["build_pages"], "build_page"))
        else:
            r.append(a.notice(
                "Please select deployment method",
                """
                    In order to deploy configurations, the deployment method should be configured first in the
                    application settings below.
                """))

        r.extend([
            a.links("Navigate", [
                a.link("apps", "Go back", icon="chevron-left"),
                a.link("app_settings", "Application Settings", icon="cogs", app_name=self.context.get("app_name")),
                a.link("/environment/app", "Manage app '{0}' at 'Environment' service.".format(data["app_name"]),
                       icon="link text-danger", record_id=data["app_id"]),
            ])
        ])
        return r

    def access_scopes(self):
        return ["config_admin"]


class ApplicationSettingsController(a.AdminController):
    @coroutine
    def get(self, app_name):

        environment_client = EnvironmentClient(self.application.cache)
        apps = self.application.apps

        try:
            app = yield environment_client.get_app_info(app_name)
        except AppNotFound:
            raise a.ActionError("App was not found.")

        try:
            settings = yield apps.get_application(self.gamespace, app_name)
        except NoSuchApplicationError:
            deployment_method = ""
            deployment_data = {}
        except ConfigApplicationError as e:
            raise a.ActionError(e.message)
        else:
            deployment_method = settings.deployment_method
            deployment_data = settings.deployment_data

        deployment_methods = {t: t.title() for t in DeploymentMethods.types()}

        if not deployment_method:
            deployment_methods[""] = "< SELECT >"

        result = {
            "app_name": app.title,
            "deployment_methods": deployment_methods,
            "deployment_method": deployment_method,
            "deployment_data": deployment_data
        }

        raise a.Return(result)

    @coroutine
    def update_deployment_method(self, deployment_method):

        app_name = self.context.get("app_name")

        environment_client = EnvironmentClient(self.application.cache)
        apps = self.application.apps

        try:
            yield environment_client.get_app_info(app_name)
        except AppNotFound:
            raise a.ActionError("App was not found.")

        if not DeploymentMethods.valid(deployment_method):
            raise a.ActionError("Not a valid deployment method")

        try:
            stt = yield apps.get_application(self.gamespace, app_name)
        except NoSuchApplicationError:
            deployment_data = {}
        else:
            deployment_data = stt.deployment_data

        try:
            yield apps.update_application_settings(
                self.gamespace, app_name, deployment_method,
                deployment_data)
        except ConfigApplicationError as e:
            raise a.ActionError(e.message)

        raise a.Redirect("app_settings", message="Deployment method has been updated",
                         app_name=app_name)

    @coroutine
    def update_deployment(self, **kwargs):

        app_name = self.context.get("app_name")

        environment_client = EnvironmentClient(self.application.cache)
        apps = self.application.apps

        try:
            yield environment_client.get_app_info(app_name)
        except AppNotFound:
            raise a.ActionError("App was not found.")

        try:
            settings = yield apps.get_application(self.gamespace, app_name)
        except NoSuchApplicationError:
            raise a.ActionError("Please select deployment method first")
        except ConfigApplicationError as e:
            raise a.ActionError(e.message)
        else:
            deployment_method = settings.deployment_method
            deployment_data = settings.deployment_data

        m = DeploymentMethods.get(deployment_method)()

        m.load(deployment_data)
        yield m.update(**kwargs)

        try:
            yield apps.update_application_settings(self.gamespace, app_name, deployment_method, m.dump())
        except ConfigApplicationError as e:
            raise a.ActionError(e.message)

        raise a.Redirect("app_settings", message="Deployment settings have been updated",
                         app_name=app_name)

    def render(self, data):

        r = [
            a.breadcrumbs([
                a.link("index", "Applications"),
                a.link("app", data["app_name"], app_name=self.context.get("app_name"))
            ], "Application Settings")
        ]

        deployment_method = data["deployment_method"]
        deployment_data = data["deployment_data"]

        if deployment_method:
            m = DeploymentMethods.get(deployment_method)
            if m.has_admin():
                r.append(a.form(
                    "{0} Deployment settings".format(deployment_method.title()), fields=m.render(a), methods={
                        "update_deployment": a.method("Update", "primary")
                    }, data=deployment_data, icon="rocket"))
        else:
            r.append(a.notice(
                "Please select deployment method",
                """
                    In order to deploy configurations, the deployment method should be configured first in the
                    application settings below.
                """))

        r.extend([
            a.form("Deployment method", fields={
                "deployment_method": a.field(
                    "Deployment method", "select", "primary", "non-empty", values=data["deployment_methods"]
                )
            }, methods={
                "update_deployment_method": a.method("Switch deployment method", "primary")
            }, data=data),
            a.links("Navigate", [
                a.link("app", "Back", app_name=self.context.get("app_name")),
            ])
        ])

        return r

    def access_scopes(self):
        return ["config_admin"]


class ApplicationVersionController(a.AdminController):
    BUILDS_PER_PAGE = 10

    @coroutine
    @validate(app_name="str_name", app_version="str", build_page="int")
    def get(self, app_name, app_version, build_page=1):

        environment_client = EnvironmentClient(self.application.cache)
        apps = self.application.apps
        builds_data = self.application.builds

        try:
            app = yield environment_client.get_app_info(app_name)
        except AppNotFound as e:
            raise a.ActionError("App was not found.")

        versions = app.versions

        if app_version not in versions:
            raise a.ActionError("No such app version")

        try:
            yield apps.get_application(self.gamespace, app_name)
        except NoSuchApplicationError:
            raise a.Redirect("app_settings", message="Please configure the application first", app_name=app_name)

        try:
            version_settings = yield apps.get_application_version(self.gamespace, app_name, app_version)
        except NoSuchApplicationVersionError:
            version_settings = None
            version_build = None
        except ConfigApplicationError as e:
            raise a.ActionError(e.message)
        else:
            version_build = version_settings.build

        try:
            build_items, builds = yield builds_data.list_builds_pages(
                self.gamespace, app_name,
                limit=ApplicationController.BUILDS_PER_PAGE,
                offset=(ApplicationController.BUILDS_PER_PAGE * (build_page - 1)))
        except ConfigBuildError as e:
            raise a.ActionError(e.message)

        build_pages = int(math.ceil(float(build_items) / float(ApplicationController.BUILDS_PER_PAGE)))

        author_ids = set()
        for build in builds:
            build.author_name = unicode(build.author)
            author_ids.add(build.author)

        internal = Internal()

        try:
            profiles = yield internal.send_request(
                "profile", "mass_profiles",
                accounts=author_ids,
                gamespace=self.gamespace,
                action="get_public",
                profile_fields=["name"])
        except InternalError as e:
            pass  # well
        else:
            for build in builds:
                profile = profiles.get(str(build.author))
                if profile:
                    build.author_name = profile.get("name")

        result = {
            "app_name": app_name,
            "app_id": app.id,
            "app_title": app.title,
            "versions": versions,
            "builds": builds,
            "app_settings": version_settings,
            "build": version_build,
            "build_pages": build_pages,
            "build_title": "Build {0}".format(version_build) if version_build else "Unset",
        }

        raise a.Return(result)

    @coroutine
    def update_configuration(self):
        app_name = self.context.get("app_name")
        app_version = self.context.get("app_version")
        build_id = self.context.get("build_id")

        environment_client = EnvironmentClient(self.application.cache)
        apps = self.application.apps

        try:
            yield environment_client.get_app_info(app_name)
        except AppNotFound:
            raise a.ActionError("App was not found.")

        try:
            yield apps.update_application_version(self.gamespace, app_name, app_version, build_id)
        except ConfigApplicationError as e:
            raise a.ActionError(e.message)

        raise a.Redirect(
            "app_version", message="Configuration for version {0} has been updated".format(app_version),
            app_name=app_name, app_version=app_version)

    @coroutine
    def unset_configuration(self):
        app_name = self.context.get("app_name")
        app_version = self.context.get("app_version")

        environment_client = EnvironmentClient(self.application.cache)
        apps = self.application.apps

        try:
            yield environment_client.get_app_info(app_name)
        except AppNotFound:
            raise a.ActionError("App was not found.")

        try:
            yield apps.delete_application_version(self.gamespace, app_name, app_version)
        except ConfigApplicationError as e:
            raise a.ActionError(e.message)

        raise a.Redirect(
            "app_version", message="Configuration for version {0} has been deleted",
            app_name=app_name, app_version=app_version)

    def render(self, data):
        r = [
            a.breadcrumbs([
                a.link("apps", "Applications"),
                a.link("app", data["app_title"], app_name=self.context.get("app_name"))
            ], "Version {0}".format(self.context.get("app_version")))
        ]

        if data["build"]:
            r.append(a.form("Version {0} configuration".format(self.context.get("app_version")), fields={
                "build_title": a.field("Current Build", "status", "info")
            }, methods={
                "unset_configuration": a.method(
                    "Unset configuration", "danger",
                    danger="Once unset, if the default configuration is not set, "
                           "the user would not be able to download any configuration.")
            }, data=data))
        else:
            r.append(a.notice(
                "No version {0} configuration".format(self.context.get("app_version")),
                "Configuration for the version {0} is not set. "
                "Therefore, if the default configuration is not set, users would not "
                "be able to download any configuration.".format(self.context.get("app_version"))))

        r.extend([
            a.content("Recent Configuration Builds", headers=[
                {"id": "actions", "title": "Actions"},
                {"id": "build_id", "title": "Build ID"},
                {"id": "comment", "title": "Comment"},
                {"id": "author", "title": "Author"},
                {"id": "date", "title": "Upload Date"},
                {"id": "download", "title": "Download"},
            ], items=[
                {
                    "actions": [
                        a.status("Version {0}".format(self.context.get("app_version")), "success", "check")
                        if data["build"] == build.build_id else
                        a.button("app_version", "Use This", "primary", _method="update_configuration",
                                 build_id=build.build_id, app_name=self.context.get("app_name"),
                                 app_version=self.context.get("app_version"))
                    ],
                    "build_id": build.build_id,
                    "date": str(build.date),
                    "comment": build.comment,
                    "author": [
                        a.link("/profile/profile", build.author_name, icon="user", account=build.author)
                    ],
                    "download": [
                        a.link(build.url, "", icon="download")
                    ]
                }
                for build in data["builds"]
            ], style="default")
        ])

        if data["build_pages"] > 1:
            r.append(a.pages(data["build_pages"], "build_page"))

        r.extend([
            a.links("Navigate", [
                a.link("app", "Go back", icon="chevron-left", app_name=self.context.get("app_name")),
                a.link("deploy_build", "Deploy a new configuration", icon="upload",
                       app_name=self.context.get("app_name")),
                a.link("app_settings", "Application Settings", icon="cogs", app_name=self.context.get("app_name")),
                a.link("/environment/app", "Manage app '{0}' at 'Environment' service.".format(data["app_name"]),
                       icon="link text-danger", record_id=data["app_id"]),
            ])
        ])
        return r

    def access_scopes(self):
        return ["config_admin"]


class ApplicationsController(a.AdminController):
    @coroutine
    def get(self):
        environment_client = EnvironmentClient(self.application.cache)
        apps = yield environment_client.list_apps()

        result = {
            "apps": apps
        }

        raise a.Return(result)

    def render(self, data):
        return [
            a.breadcrumbs([], "Applications"),
            a.links("Select application", links=[
                a.link("app", app_title, icon="mobile", app_name=app_name)
                for app_name, app_title in data["apps"].iteritems()
            ]),
            a.links("Navigate", [
                a.link("index", "Go back", icon="chevron-left"),
                a.link("/environment/apps", "Manage apps", icon="link text-danger"),
            ])
        ]

    def access_scopes(self):
        return ["config_admin"]


class RootAdminController(a.AdminController):
    def render(self, data):
        return [
            a.links("Config service", [
                a.link("apps", "Applications", icon="mobile")
            ])
        ]

    def access_scopes(self):
        return ["config_admin"]
