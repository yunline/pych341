import ctypes
from ctypes import *
import platform
import warnings
from typing import Optional, Union

pyver = [int(i) for i in platform.python_version_tuple()]

if not (pyver[0] >= 3 and pyver[1] >= 10):
    warnings.warn("This Library requires python3.10+")


class CH341Error(Exception):
    pass


if platform.system() == "Windows":
    try:
        if platform.architecture()[0] == "64bit":
            ch341dll = windll.CH341DLLA64
        elif platform.architecture()[0] == "32bit":
            ch341dll = windll.CH341DLL
        else:
            raise RuntimeError("Unknown architecture")

    except FileNotFoundError:
        raise RuntimeError(
            "DLL not found. "
            "Try get ch341 drivers here: "
            "https://www.wch.cn/downloads/CH341PAR_EXE.html"
        )

else:
    raise RuntimeError("Platform '%s' is not supported." % platform.system())


def get_dll_version():
    return ch341dll.CH341GetVersion()


def get_drv_version():
    result = ch341dll.CH341GetDrvVersion()
    if not result:
        raise CH341Error("Operation Failed.")
    return result


mCH341_PACKET_LENGTH = 32

mCH341A_CMD_I2C_STREAM = 0xAA

mCH341A_CMD_I2C_STM_STA = 0x74
mCH341A_CMD_I2C_STM_STO = 0x75
mCH341A_CMD_I2C_STM_OUT = 0x80
mCH341A_CMD_I2C_STM_IN = 0xC0
mCH341A_CMD_I2C_STM_MAX = min(0x3F, mCH341_PACKET_LENGTH)
mCH341A_CMD_I2C_STM_SET = 0x60
mCH341A_CMD_I2C_STM_US = 0x40
mCH341A_CMD_I2C_STM_MS = 0x50
mCH341A_CMD_I2C_STM_DLY = 0x0F
mCH341A_CMD_I2C_STM_END = 0x00

SPI_NOCS = 0x00
SPI_CS0 = 0x80
SPI_CS1 = 0x81
SPI_CS2 = 0x82
SPI_MSBFIRST = 0x80
SPI_LSBFIRST = 0x00


class Ch341:
    def __init__(self, index: int = 0):
        self.index = index
        self._eeprom_type = None
        self._i2c_speed = 0
        self._spi_bit_order = SPI_LSBFIRST
        self._io_rw = 0x00
        self._io_out = 0x00

    def open(self, exclusive: bool = False):
        self.handle = ch341dll.CH341OpenDevice(self.index)
        if self.handle < 0:
            raise CH341Error("Failed to open device %d." % self.index)
        self.reset()
        self.set_exclusive(exclusive)

    def close(self):
        self.reset()
        ch341dll.CH341CloseDevice(self.index)

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def reset(self):
        self.update_io_state(0x00, 0x00)  # set all IOs to read mode
        result = ch341dll.CH341ResetDevice(self.index)
        if not result:
            raise CH341Error("Operation Failed.")

    def _update_config(self):
        result = ch341dll.CH341SetStream(
            self.index, self._i2c_speed | self._spi_bit_order
        )
        if not result:
            raise CH341Error("Operation Failed.")

    def get_ic_version(self):
        result = ch341dll.CH341GetVerIC(self.index)
        if not result:
            raise CH341Error("Operation Failed.")
        return result

    def get_name(self):
        result = ch341dll.CH341GetDeviceName(self.index)
        if not result:
            raise CH341Error("Operation Failed.")
        return string_at(result).decode()

    def set_exclusive(self, exclusive: bool):
        result = ch341dll.CH341SetExclusive(self.index, exclusive)
        if not result:
            raise CH341Error("Operation Failed.")

    def i2c_scan(self):
        out = []
        for addr in range(127):
            self._i2c_start_stop(1)
            if self._i2c_out_byte_check_ack(addr << 1):
                out.append(addr)
            self._i2c_start_stop(0)
        return out

    def i2c_scan_print(self):
        l = self.i2c_scan()
        for y in range(8):
            for x in range(16):
                addr = (y << 4) + x
                if addr in l:
                    print("0x{0:02X}".format(addr), end=" ")
                else:
                    print("[  ]", end=" ")
            print("")
        print(f"{len(l)} address{' was' if len(l)==1 else 'es were'} detected.")

    def _i2c_out_byte_check_ack(self, byte):
        buf = (c_ubyte * 10)()
        buf[0] = mCH341A_CMD_I2C_STREAM
        buf[1] = mCH341A_CMD_I2C_STM_OUT
        buf[2] = byte
        buf[3] = mCH341A_CMD_I2C_STM_END
        length = c_ulong(0)

        result = ch341dll.CH341WriteRead(
            self.index, 4, byref(buf), 32, 1, byref(length), byref(buf)
        )

        if not (result and length):
            raise CH341Error("Operation Failed.")

        if buf[length.value - 1] & 0x80:
            return False
        return True

    def _i2c_start_stop(self, start=1):
        cmd = (c_ubyte * 3)()
        cmd[0] = mCH341A_CMD_I2C_STREAM
        cmd[1] = mCH341A_CMD_I2C_STM_STA if start else mCH341A_CMD_I2C_STM_STO
        cmd[2] = mCH341A_CMD_I2C_STM_END
        length = c_ulong(3)
        result = ch341dll.CH341WriteData(self.index, byref(cmd), byref(length))
        if not result:
            raise CH341Error("Operation Failed.")

    def set_i2c_speed(self, speed: int):
        # speed = 0: 20  kHz
        # speed = 1: 100 kHz
        # speed = 2: 400 kHz
        # speed = 3: 800 kHz
        self._i2c_speed = max(0, min(3, speed))
        self._update_config()

    def i2c_read(
        self,
        dev_addr: int,
        addr: int,
        buf: Optional[bytearray] = None,
        length: Optional[int] = None,
    ) -> bytearray:
        if buf is None and length is None:
            raise ValueError("'buf' and 'length' shouldn't be both None.")
        if length is None:
            length = len(buf)
        if buf is None:
            buf = bytearray(length)
        read_buf = (c_ubyte * length).from_buffer(buf)

        write_buf = (c_ubyte * 2)((dev_addr << 1), addr)
        result = ch341dll.CH341StreamI2C(
            self.index, 2, byref(write_buf), length, byref(read_buf)
        )
        if not result:
            raise CH341Error("Operation Failed.")
        return buf

    def i2c_write(self, dev_addr: int, addr: int, buf: bytearray):
        _buf = bytearray([dev_addr << 1, addr])
        _buf.extend(buf)
        write_buf = (c_ubyte * (len(buf) + 2)).from_buffer(_buf)

        result = ch341dll.CH341StreamI2C(
            self.index, len(buf) + 2, byref(write_buf), 0, 0
        )
        if not result:
            raise CH341Error("Operation Failed.")

    def set_eeprom_type(self, eeprom_type: int):
        if not isinstance(eeprom_type, int):
            raise TypeError(
                "Argument 'eeprom_type' must be int, got %s."
                % type(eeprom_type).__name__
            )
        self._eeprom_type = eeprom_type

    def eeprom_read(
        self,
        addr: int,
        buf: Optional[bytearray] = None,
        length: Optional[int] = None,
    ) -> bytearray:
        if self._eeprom_type is None:
            raise CH341Error("EEPROM type is not specified.")
        if buf is None and length is None:
            raise ValueError("'buf' and 'length' shouldn't be both None.")
        if length is None:
            length = len(buf)
        if buf is None:
            buf = bytearray(length)

        read_buf = (c_ubyte * length).from_buffer(buf)

        result = ch341dll.CH341ReadEEPROM(
            self.index, self._eeprom_type, addr, length, byref(read_buf)
        )
        if not result:
            raise CH341Error("Operation Failed.")
        return buf

    def eeprom_write(self, addr: int, buf: bytearray):
        if self._eeprom_type is None:
            raise CH341Error("EEPROM type is not specified.")
        write_buf = (c_ubyte * len(buf)).from_buffer(buf)

        result = ch341dll.CH341WriteEEPROM(
            self.index, self._eeprom_type, addr, len(buf), byref(write_buf)
        )
        if not result:
            raise CH341Error("Operation Failed.")

    def set_spi_bit_order(self, bit_order: int):
        self._spi_bit_order = bit_order
        self._update_config()

    def spi_write(
        self,
        buf1: bytearray,
        buf2: Optional[bytearray] = None,
        /,
        cs: int = SPI_NOCS,
    ):
        _buf1 = buf1.copy()
        if buf2 is None:
            _buf2 = None
        else:
            _buf2 = buf2.copy()
        self.spi_swap(_buf1, _buf2, cs=cs)

    def spi_read(
        self,
        length: int,
        n_channels: int = 1,
        cs: int = SPI_NOCS,
    ) -> Union[bytearray, tuple[bytearray]]:
        if n_channels == 1:
            buf = bytearray(length)
            self.spi_swap(buf, cs=cs)
            return buf
        elif n_channels == 2:
            buf1 = bytearray(length)
            buf2 = bytearray(length)
            self.spi_swap(buf1, buf2, cs=cs)
            return buf1, buf2
        else:
            raise ValueError("'n_channels' should be 1 or 2")

    def spi_swap(
        self,
        buf1: bytearray,
        buf2: Optional[bytearray] = None,
        /,
        cs: int = SPI_NOCS,
    ):
        length = len(buf1)
        if buf2 is None:
            write_buf = (c_ubyte * length).from_buffer(buf1)
            result = ch341dll.CH341StreamSPI4(self.index, cs, length, byref(write_buf))
        else:
            if length != len(buf2):
                raise CH341Error("Length of buf1 and buf2 must be the same")
            write_buf1 = (c_ubyte * length).from_buffer(buf1)
            write_buf2 = (c_ubyte * length).from_buffer(buf2)
            result = ch341dll.CH341StreamSPI5(
                self.index,
                cs,
                length,
                byref(write_buf1),
                byref(write_buf2),
            )

        if not result:
            raise CH341Error("Operation Failed.")

    def _update_io_state(self):
        result = ch341dll.CH341Set_D5_D0(
            self.index, c_ubyte(self._io_rw), c_ubyte(self._io_out)
        )
        if not result:
            raise CH341Error("Operation Failed.")

    def update_io_state(self, io_rw: int, io_out: int):
        self._io_rw = io_rw
        self._io_out = io_out
        self._update_io_state()

    def set_io_rw(self, io: int, rw: int):
        self._io_rw &= 0xFF ^ (1 << io)
        self._io_rw |= bool(rw) << io
        self._update_io_state()

    def write_io(self, io: int, level: int):
        self._io_out &= 0xFF ^ (1 << io)
        self._io_out |= bool(level) << io
        self._update_io_state()


eeprom_enum = [
    "EEPROM_24C01",
    "EEPROM_24C02",
    "EEPROM_24C04",
    "EEPROM_24C08",
    "EEPROM_24C16",
    "EEPROM_24C32",
    "EEPROM_24C64",
    "EEPROM_24C128",
    "EEPROM_24C256",
    "EEPROM_24C512",
    "EEPROM_24C1024",
    "EEPROM_24C2048",
    "EEPROM_24C4096",
]
globals().update({i[1]: i[0] for i in enumerate(eeprom_enum)})

IC_VER_CH341A = 0x20
IC_VER_CH341A3 = 0x30

__all__ = [
    # Errors
    "CH341Error",
    # Constants
    "IC_VER_CH341A",
    "IC_VER_CH341A3",
    "SPI_NOCS",
    "SPI_CS0",
    "SPI_CS1",
    "SPI_CS2",
    "SPI_MSBFIRST",
    "SPI_LSBFIRST",
    # Classes and Methods
    "Ch341",
    "get_dll_version",
    "get_drv_version",
]

__all__.extend(eeprom_enum)
