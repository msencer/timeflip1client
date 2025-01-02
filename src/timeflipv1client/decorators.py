from .exceptions import NotConnectedException, CommandRequiresLoginException


def connected(func):
    """Decorator for checking if the client has connected to a device"""

    def wrapper(self, *args, **kwargs):
        if not self.connected:
            raise NotConnectedException()

        return func(self, *args, **kwargs)

    return wrapper


def logged_in(func):
    """Decorator for checking if the client has logged in to the device before running commands that require login"""

    def wrapper(self, *args, **kwargs):
        if not self.logged_in:
            raise CommandRequiresLoginException()

        return func(self, *args, **kwargs)

    return wrapper
