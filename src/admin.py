import json

from tornado.gen import coroutine, Return

import common.admin as a

from model.config import ConfigNotFound, DEFAULT
from model.scheme import SchemeNotFound

from common.environment import AppNotFound
from common.validate import validate


class ApplicationController(a.AdminController):
    @coroutine
    @validate(app_name="str_name")
    def get(self, app_name):

        env_service = self.application.env_service

        try:
            app = yield env_service.get_app_info(self.gamespace, app_name)
        except AppNotFound as e:
            raise a.ActionError("App was not found.")

        result = {
            "app_name": app_name,
            "app_id": app["id"],
            "app_title": app["title"],
            "versions": app["versions"]
        }

        raise a.Return(result)

    def render(self, data):
        return [
            a.breadcrumbs([
                a.link("apps", "Applications")
            ], data["app_name"]),
            a.links("Application '{0}' versions".format(data["app_title"]), links=[
                a.link("app_version", v_name, icon="tags", app_name=self.context.get("app_name"),
                       app_version=v_name) for v_name, v_id in data["versions"].iteritems()
            ] + [
                a.link("app_version", "Default configuration", icon="tags", badge="default",
                       app_name=self.context.get("app_name"), app_version=DEFAULT)
            ]),
            a.links("Navigate", [
                a.link("apps", "Go back", icon="chevron-left"),
                a.link("scheme", "Edit default scheme", badge="default", icon="flask",
                       app_name=self.context.get("app_name"), app_version=DEFAULT),
                a.link("/environment/app", "Manage app '{0}' at 'Environment' service.".format(data["app_name"]),
                       icon="link text-danger", record_id=data["app_id"]),
            ])
        ]

    def access_scopes(self):
        return ["config_admin"]


class ApplicationVersionController(a.AdminController):
    @coroutine
    @validate(app_name="str", app_version="str")
    def get(self, app_name, app_version):

        env_service = self.application.env_service

        try:
            app = yield env_service.get_app_info(self.gamespace, app_name)
        except AppNotFound as e:
            raise a.ActionError("App was not found.")

        configs = self.application.configs
        schemes = self.application.schemes

        try:
            config = yield configs.get_config(
                self.gamespace,
                app_name,
                app_version,
                try_default=False)
        except ConfigNotFound:
            no_such_configuration = app_version != DEFAULT
            config = {}
        else:
            no_such_configuration = False

        try:
            scheme = yield schemes.get_scheme(
                self.gamespace,
                app_name,
                app_version,
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
                a.link("app", data["app_name"], app_name=self.context.get("app_name"))
            ], self.context.get("app_version"))
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
                               app_name=self.context.get("app_name"),
                               app_version=DEFAULT)
                    ] + [
                        a.link("scheme", "Edit scheme for version " + self.context.get("app_version"), icon="flask",
                               app_name=self.context.get("app_name"),
                               app_version=self.context.get("app_version"))
                    ] if self.context.get("app_version") != DEFAULT else [])
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
                                   app_name=self.context.get("app_name"),
                                   app_version=DEFAULT)
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
                a.link("app", "Go back", icon="chevron-left", app_name=self.context.get("app_name")),
                a.link("scheme", "Edit scheme for this version", icon="flask",
                       app_name=self.context.get("app_name"),
                       app_version=self.context.get("app_version"))
            ])
        ])

        return l

    def access_scopes(self):
        return ["config_admin"]

    @coroutine
    @validate(config="load_json")
    def update(self, config, **ignored):
        configs = self.application.configs

        yield configs.set_config(
            self.gamespace,
            self.get_context("app_name"),
            self.get_context("app_version"),
            config
        )

        raise a.Redirect(
            "app_version",
            message="Configuration has been updated",
            app_name=self.context.get("app_name"),
            app_version=self.context.get("app_version"))


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


class SchemeController(a.AdminController):
    @coroutine
    @validate(app_name="str", app_version="str")
    def get(self, app_name, app_version):

        env_service = self.application.env_service

        try:
            app = yield env_service.get_app_info(self.gamespace, app_name)
        except AppNotFound as e:
            raise a.ActionError("App was not found.")

        schemes = self.application.schemes

        try:
            scheme = yield schemes.get_scheme(
                self.gamespace,
                app_name,
                app_version,
                try_default=False)
        except SchemeNotFound:
            no_such_scheme = app_version != DEFAULT
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
                a.link("app", data["app_name"], app_name=self.context.get("app_name"))
            ], "Scheme for version: " + self.context.get("app_version"))
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
                               app_name=self.context.get("app_name"),
                               app_version=DEFAULT)
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
                a.link("app", "Go back", icon="chevron-left", app_name=self.context.get("app_name")),
                a.link("app_version", "Edit configuration for this scheme",
                       app_name=self.context.get("app_name"),
                       app_version=self.context.get("app_version"),
                       icon="tags"),
                a.link("https://spacetelescope.github.io/understanding-json-schema/index.html", "See docs", icon="book")
            ])
        ])

        return l

    def access_scopes(self):
        return ["config_admin"]

    @coroutine
    @validate(scheme="load_json")
    def update(self, scheme, **ignored):
        schemes = self.application.schemes

        yield schemes.set_scheme(
            self.gamespace,
            self.get_context("app_name"),
            self.get_context("app_version"),
            scheme
        )

        raise a.Redirect(
            "scheme",
            message="Configuration scheme has been updated",
            app_name=self.context.get("app_name"),
            app_version=self.context.get("app_version"))
