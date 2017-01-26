import json

from tornado.gen import coroutine, Return

import common.admin as a

from model.config import ConfigNotFound, DEFAULT
from model.scheme import SchemeNotFound

from common.environment import AppNotFound


class ApplicationController(a.AdminController):
    @coroutine
    def get(self, record_id):

        env_service = self.application.env_service

        try:
            app = yield env_service.get_app_info(self.gamespace, record_id)
        except AppNotFound as e:
            raise a.ActionError("App was not found.")

        result = {
            "app_id": record_id,
            "app_record_id": app["id"],
            "app_name": app["title"],
            "versions": app["versions"]
        }

        raise a.Return(result)

    def render(self, data):
        return [
            a.breadcrumbs([
                a.link("apps", "Applications")
            ], data["app_name"]),
            a.links("Application '{0}' versions".format(data["app_name"]), links=[
                a.link("app_version", v_name, icon="tags", app_id=self.context.get("record_id"),
                       version_id=v_name) for v_name, v_id in data["versions"].iteritems()
            ] + [
                a.link("app_version", "Default configuration", icon="tags", badge="default",
                       app_id=self.context.get("record_id"), version_id=DEFAULT)
            ]),
            a.links("Navigate", [
                a.link("apps", "Go back", icon="chevron-left"),
                a.link("scheme", "Edit default scheme", badge="default", icon="flask",
                       app_id=self.context.get("record_id"), version_id=DEFAULT),
                a.link("/environment/app", "Manage app '{0}' at 'Environment' service.".format(data["app_name"]),
                       icon="link text-danger", record_id=data["app_record_id"]),
            ])
        ]

    def access_scopes(self):
        return ["config_admin"]


class ApplicationVersionController(a.AdminController):
    @coroutine
    def get(self, app_id, version_id):

        env_service = self.application.env_service

        try:
            app = yield env_service.get_app_info(self.gamespace, app_id)
        except AppNotFound as e:
            raise a.ActionError("App was not found.")

        configs = self.application.configs
        schemes = self.application.schemes

        try:
            config = yield configs.get_config(
                self.gamespace,
                app_id,
                version_id,
                try_default=False)
        except ConfigNotFound:
            no_such_configuration = version_id != DEFAULT
            config = {}
        else:
            no_such_configuration = False

        try:
            scheme = yield schemes.get_scheme(
                self.gamespace,
                app_id,
                version_id,
                try_default=True)
        except SchemeNotFound:
            no_such_scheme = True
            scheme = {}
        else:
            no_such_scheme = False

        result = {
            "app_name": app["title"],
            "config": config,
            "scheme": scheme,
            "no_such_configuration": no_such_configuration,
            "no_such_scheme": no_such_scheme
        }

        raise a.Return(result)

    def render(self, data):
        l = [
            a.breadcrumbs([
                a.link("apps", "Applications"),
                a.link("app", data["app_name"], record_id=self.context.get("app_id"))
            ], self.context.get("version_id"))
        ]

        if data["no_such_scheme"]:
            l.append(
                a.split(items=[
                    a.notice(
                        "No scheme",
                        "This configuration has no scheme to configure upon. Please define the scheme first. "
                        "You may edit default scheme (to apply to all configuration versions), or edit a scheme "
                        "for each configuration."
                    ),
                    a.links("Navigate", links=[
                        a.link("scheme", "Edit default scheme", icon="flask", badge="default",
                               app_id=self.context.get("app_id"),
                               version_id=DEFAULT)
                    ] + [
                        a.link("scheme", "Edit scheme for version " + self.context.get("version_id"), icon="flask",
                               app_id=self.context.get("app_id"),
                               version_id=self.context.get("version_id"))
                    ] if self.context.get("version_id") != DEFAULT else [])
                ])
            )
        else:

            if data["no_such_configuration"]:
                l.append(
                    a.split(items=[
                        a.notice(
                            "No such configuration",
                            "There is no configuration for this version, so default configuration is applied. "
                            "You may save this version (to override default), or edit default configuration instead."
                        ),
                        a.links("Navigate", links=[
                            a.link("app_version", "Edit default configuration", icon="tags", badge="default",
                                   app_id=self.context.get("app_id"),
                                   version_id=DEFAULT)
                        ])
                    ])
                )

            l.extend([
                a.form(title="Edit configuration", fields={
                    "config": a.field("Configuration", "dorn", "primary", "non-empty", schema=data["scheme"])
                }, methods={
                    "update": a.method(
                        "Override default configuration" if data["no_such_configuration"] else "Update",
                        "primary")
                }, data=data)
            ])

        l.extend([
            a.links("Navigate", [
                a.link("app", "Go back", icon="chevron-left", record_id=self.context.get("app_id")),
                a.link("scheme", "Edit scheme for this version", icon="flask",
                       app_id=self.context.get("app_id"),
                       version_id=self.context.get("version_id"))
            ])
        ])

        return l

    def access_scopes(self):
        return ["config_admin"]

    @coroutine
    def update(self, config):

        try:
            config = json.loads(config)
        except ValueError:
            raise a.ActionError("Corrupted JSON")

        configs = self.application.configs

        yield configs.set_config(
            self.gamespace,
            self.get_context("app_id"),
            self.get_context("version_id"),
            config
        )

        raise a.Redirect(
            "app_version",
            message="Configuration has been updated",
            app_id=self.context.get("app_id"),
            version_id=self.context.get("version_id"))


class ApplicationsController(a.AdminController):
    @coroutine
    def get(self):

        env_service = self.application.env_service
        apps = yield env_service.list_apps(self.gamespace)

        result = {
            "apps": apps
        }

        raise a.Return(result)

    def render(self, data):
        return [
            a.breadcrumbs([], "Applications"),
            a.links("Select application", links=[
                a.link("app", app_name, icon="mobile", record_id=app_id)
                    for app_id, app_name in data["apps"].iteritems()
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


class SchemeController(a.AdminController):
    @coroutine
    def get(self, app_id, version_id):

        env_service = self.application.env_service

        try:
            app = yield env_service.get_app_info(self.gamespace, app_id)
        except AppNotFound as e:
            raise a.ActionError("App was not found.")

        schemes = self.application.schemes

        try:
            scheme = yield schemes.get_scheme(
                self.gamespace,
                app_id,
                version_id,
                try_default=False)
        except SchemeNotFound:
            no_such_scheme = version_id != DEFAULT
            scheme = {"type": "object", "properties": {}}
        else:
            no_such_scheme = False

        result = {
            "app_name": app["title"],
            "no_such_scheme": no_such_scheme,
            "scheme": scheme
        }

        raise a.Return(result)

    def render(self, data):
        l = [
            a.breadcrumbs([
                a.link("apps", "Applications"),
                a.link("app", data["app_name"], record_id=self.context.get("app_id"))
            ], "Scheme for version: " + self.context.get("version_id"))
        ]

        if data["no_such_scheme"]:
            l.append(
                a.split(items=[
                    a.notice(
                        "No such scheme",
                        "There is no scheme for this version, so default scheme is applied. "
                        "You may edit the default one (to apply to all configuration versions), "
                        "or override it with this one."
                    ),
                    a.links("Navigate", links=[
                        a.link("scheme", "Edit default scheme", icon="flask", badge="default",
                               app_id=self.context.get("app_id"),
                               version_id=DEFAULT)
                    ])
                ])
            )

        l.extend([
            a.form(title="Edit configuration", fields={
                "scheme": a.field("Scheme", "json", "primary", "non-empty")
            }, methods={
                "update": a.method(
                    "Override default scheme" if data["no_such_scheme"] else "Update",
                    "primary")
            }, data=data),
            a.links("Navigate", [
                a.link("app", "Go back", icon="chevron-left", record_id=self.context.get("app_id")),
                a.link("app_version", "Edit configuration for this scheme",
                       app_id=self.context.get("app_id"),
                       version_id=self.context.get("version_id"),
                       icon="tags"),
                a.link("https://spacetelescope.github.io/understanding-json-schema/index.html", "See docs", icon="book")
            ])
        ])

        return l

    def access_scopes(self):
        return ["config_admin"]

    @coroutine
    def update(self, scheme):

        try:
            scheme = json.loads(scheme)
        except ValueError:
            raise a.ActionError("Corrupted JSON")

        schemes = self.application.schemes

        yield schemes.set_scheme(
            self.gamespace,
            self.get_context("app_id"),
            self.get_context("version_id"),
            scheme
        )

        raise a.Redirect(
            "scheme",
            message="Configuration scheme has been updated",
            app_id=self.context.get("app_id"),
            version_id=self.context.get("version_id"))

