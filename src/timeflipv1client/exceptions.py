class TimeFlipClientException(Exception):
    pass


class NotTimeFlipDeviceException(TimeFlipClientException):
    def __init__(self):
        super().__init__("Connected device is not a TimeFlip")


class NotConnectedException(TimeFlipClientException):
    def __init__(self):
        super().__init__("Not connected to a TimeFlip device. Please connect first")


class CommandRequiresLoginException(TimeFlipClientException):
    def __init__(self):
        super().__init__(
            "This command requires a login to the TimeFlip device. Please login"
        )


class CommandExecutionException(TimeFlipClientException):
    def __init__(self, command: str):
        super().__init__(f"Unable to execute the command {command}")


class CommandResultException(TimeFlipClientException):
    def __init__(self, command: str):
        super().__init__(
            f"The result of the command {command} is malformed, please check if you are logged in"
        )
