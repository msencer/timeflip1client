from .exceptions import (
    NotConnectedException,
    NotTimeFlipDeviceException,
    CommandResultException,
    CommandExecutionException,
)
from .decorators import logged_in, connected
from typing import Callable, Any
from bleak import BleakClient, BLEDevice, BleakError

GENERIC_UUID = "0000{:x}-0000-1000-8000-00805f9b34fb"
TIMEFLIP_UUID = "f119{:x}-71a4-11e6-bdf4-0800200c9a66"

"""Everytime the battery is removed & installed the password resets to default 000000
"""
DEFAULT_PASSWORD = "000000"
ENDIANNESS = "little"

COMMAND_ERROR = 0x01
COMMAND_OK = 0x02
COMMAND_RESULT_LEN = 21

STATUS_FLAG_TRUE = 0x01
STATUS_FLAG_FALSE = 0x02

PAUSE_FACET_ID = 63

CHARACTERISTICS = {
    "accelerometer_data": TIMEFLIP_UUID.format(0x6F51),
    "battery_level": GENERIC_UUID.format(0x2A19),
    "calibration_version": TIMEFLIP_UUID.format(0x6F56),
    "command_input": TIMEFLIP_UUID.format(0x6F54),
    "command_result": TIMEFLIP_UUID.format(0x6F53),
    "device_name": GENERIC_UUID.format(0x2A00),
    "facet": TIMEFLIP_UUID.format(0x6F52),
    "firmware_revision": GENERIC_UUID.format(0x2A26),
    "password_input": TIMEFLIP_UUID.format(0x6F57),
}

COMMANDS = {
    "auto_pause": bytearray([0x05]),
    "calibration_reset": bytearray([0x03]),
    "history": bytearray([0x01]),
    "history_delete": bytearray([0x02]),
    "lock_off": bytearray([0x04, STATUS_FLAG_FALSE]),
    "lock_on": bytearray([0x04, STATUS_FLAG_TRUE]),
    "pause_off": bytearray([0x06, STATUS_FLAG_FALSE]),
    "pause_on": bytearray([0x06, STATUS_FLAG_TRUE]),
    "status": bytearray([0x10]),
}


class Timeflip1Client(BleakClient):
    """
    BleakClient wrapper for Timeflip V3 client implementation, for more information check <DOCUMENTATION_LINK>
    """

    def __init__(self, device: BLEDevice):
        super().__init__(device)

        self.logged_in = False
        self.connected = False
        self.calibrated = False

    async def connect(self) -> None:
        try:
            self.connected = await super().connect()
        except:
            raise NotConnectedException()
        try:
            # if we are connected to a non-TF device, this should raise an error
            _ = await self._read_facet_characteristic()
        except BleakError:
            raise NotTimeFlipDeviceException()

    @connected
    async def disconnect(self) -> None:
        try:
            if self.calibrated:
                await super().stop_notify(CHARACTERISTICS["facet"])
            await super().disconnect()
        except (KeyboardInterrupt, SystemExit):
            raise

    @connected
    async def battery_level(self) -> int:
        """Get the battery level

        :return: percentage of battery level (from 0 to 100)
        """

        return int.from_bytes(
            await super().read_gatt_char(CHARACTERISTICS["battery_level"]), ENDIANNESS
        )

    @connected
    async def firmware_revision(self) -> str:
        """Get firmware revision version

        :return: revision version
        """

        return (
            await super().read_gatt_char(CHARACTERISTICS["firmware_revision"])
        ).decode("ascii")

    @connected
    async def login(self, password: str = DEFAULT_PASSWORD) -> None:
        """Login is required to run some of the commands.
        :note: There is no way of verifying if the login is OK or not.
        """

        _ = await super().write_gatt_char(
            CHARACTERISTICS["password_input"],
            bytearray(password.encode("ascii")),
            response=True,
        )

        # there is no good way of checking if the login is successful or not. fundamentally the facet read is empty if the login is not successful so we are leveraging this info.
        f = await self._read_facet_characteristic()
        self.logged_in = len(f) > 0 and f[0] != b""

    @logged_in
    async def setup_facets(
        self, facet_callback: Callable[[str, Any], Any] = None
    ) -> None:
        """
        + Setup the notification callback on 0x6f52 (if any)
        + Get status to update internals
        + Get current facet (triggers the callback)

        :param facet_callback: callback called every time the facet change.
        Should be of the form ``callback(sender, data)``.
        """

        async def custom_facet_callback(_, data, func=facet_callback):
            current_facet = int.from_bytes(data, ENDIANNESS)
            if func:
                await func(current_facet)

        self.calibrated = True
        await super().start_notify(CHARACTERISTICS["facet"], custom_facet_callback)

    @logged_in
    async def stop_setup_facets(self) -> None:
        await super().stop_notify(CHARACTERISTICS["facet"])

    @logged_in
    async def get_status(self) -> dict:
        """Gets the status of the TF device.(Is is on pause, is it locked and the auto-auto_pause value).

        .. note: this command requires login


        :return: a dict containing the pause, lock and auto-pause status
        """

        locked, paused, *data = await self._run_command_and_read_output(
            COMMANDS["status"], check_if_successful=True
        )

        return {
            "locked": locked == STATUS_FLAG_TRUE,
            "paused": paused == STATUS_FLAG_TRUE,
            "auto_pause_time": int.from_bytes(data[0:2], ENDIANNESS),
        }

    @logged_in
    async def unpause(self) -> None:
        await self._run_command(COMMANDS["pause_off"])

    @logged_in
    async def get_history(self) -> dict:
        """Gets the history of the recordings from the TF device.
        .. note: this command requires login


        :return: a dict containing a history array for each facet
        """
        result = {}
        histories = []
        num_histories = 0
        empty = bytearray(21)

        await self._run_command(COMMANDS["history"])

        while True:
            data = await self._read_command_result_characteristic()
            if data == empty:
                break
            num_histories = int.from_bytes(
                data[:2], ENDIANNESS
            )  # the penultimate package will contain the number read
            for i in range(7):
                history = data[i * 3 : (i + 1) * 3]
                facet = int(
                    history[2] >> 2
                )  # removing the 2 bits that are not included for facet information
                history[2] &= 3  # the mask removes the facet related bits(first 6)
                time_in_seconds = int.from_bytes(history, ENDIANNESS)
                histories.append((facet, time_in_seconds))

        histories = histories[:num_histories]

        for facet, tis in histories:
            if facet not in result:
                result[facet] = []
            result[facet].append(tis)

        return result

    @logged_in
    async def clear_history(self) -> None:
        """Clears the history from the TF device.
        .. note: this command requires login


        """
        await self._run_command(COMMANDS["history_delete"])

    @logged_in
    async def set_auto_pause(self, time: int) -> None:
        """Set auto-pause time.

        .. note: this command requires login

        :param: time (in minutes) after which the timeflip should pause counting. It should be a 2byte number
        """

        if time < 0:
            raise ValueError("time should be bigger than 0")
        if time >> 16 > 0:
            raise ValueError("time should be only two bytes")

        command = COMMANDS["auto_pause"]
        command.extend(int.to_bytes(time, 2, ENDIANNESS))
        await self._run_command(command, check_if_successful=True)
        self.auto_pause_time = time

    @logged_in
    async def reset_calibration(self) -> None:
        """Resets the calibration version. It's also reset when the battery is replaced

        .. note: this command requires login
        """

        await self._run_command(COMMANDS["calibration_reset"])

    @logged_in
    async def get_current_facet(self) -> int:
        """Gets current active facet.

        .. note: this command requires login

        :return: an integer between 0 and 47
        """

        return int.from_bytes(await self._read_facet_characteristic(), ENDIANNESS)

    @logged_in
    async def get_current_calibration_version(self) -> int:
        """Gets the version of calibration that's synced with the device.

        .. note: this command requires login

        :return: an integer
        """

        return int.from_bytes(
            await self._read_calibration_version_characteristic(), ENDIANNESS
        )

    @logged_in
    async def set_current_calibration_version(self, version: int) -> None:
        """Sets the version of calibration that's synced with the device.

        .. note: this command requires login

        :param: new version number (integer)
        """
        payload = int.to_bytes(version, 4, ENDIANNESS)
        await super().write_gatt_char(
            CHARACTERISTICS["calibration_version"], payload, response=True
        )

    async def _read_facet_characteristic(self) -> bytearray:
        return await super().read_gatt_char(CHARACTERISTICS["facet"])

    async def _read_calibration_version_characteristic(self) -> bytearray:
        return await super().read_gatt_char(CHARACTERISTICS["calibration_version"])

    async def _read_command_result_characteristic(self) -> bytearray:
        return await super().read_gatt_char(CHARACTERISTICS["command_result"])

    async def _run_command(
        self, command: bytearray, check_if_successful: bool = False
    ) -> bytearray:

        await super().write_gatt_char(
            CHARACTERISTICS["command_input"], command, response=True
        )

        if check_if_successful:
            exec_command, result = await super().read_gatt_char(
                CHARACTERISTICS["command_input"]
            )

            successful = exec_command == command[0] and result == COMMAND_OK
            if not successful:
                raise CommandExecutionException(command)

    async def _run_command_and_read_output(
        self, command: bytearray, check_if_successful: bool = False
    ) -> bytearray:

        await self._run_command(command, check_if_successful)

        data = await self._read_command_result_characteristic()

        if len(data) != COMMAND_RESULT_LEN:
            raise CommandResultException(command)

        return data

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
