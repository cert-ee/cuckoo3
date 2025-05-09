# Copyright (C) 2019-2021 Estonian Information System Authority.
# See the file 'LICENSE' for copying permission.


class RooterError(Exception):
    pass


class InterfaceError(RooterError):
    pass


class CommandFailedError(RooterError):
    pass


class RequestFailedError(RooterError):
    pass


class InvalidRequestError(RequestFailedError):
    pass


class AutoVPNError(RooterError):
    pass


class MaxConnectionsError(AutoVPNError):
    pass


class RouteUnavailableError(RooterError):
    pass


class ExistingRouteError(RooterError):
    pass
