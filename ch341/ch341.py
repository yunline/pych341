import ctypes
from ctypes import *
import platform
import warnings

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


class Ch341:
    def __init__(self, index: int = 0):
        self.index = index

    def open(self, exclusive=0):
        self.handle = ch341dll.CH341OpenDevice(self.index)
        if self.handle < 0:
            raise CH341Error("Failed to open device %d." % self.index)
        self.reset()
        self.set_exclusive(exclusive)

    def close(self):
        ch341dll.CH341CloseDevice(self.index)

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def reset(self):
        result = ch341dll.CH341ResetDevice(self.index)
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

    def set_exclusive(self, exclusive):
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

    def i2c_set_speed(self, speed: int):
        # speed = 0: 20  kHz
        # speed = 1: 100 kHz
        # speed = 2: 400 kHz
        # speed = 3: 800 kHz
        speed = max(0, min(3, speed))
        result = ch341dll.CH341SetStream(self.index, speed)
        if not result:
            raise CH341Error("Operation Failed.")

    def i2c_read_byte(self, dev_addr, addr):
        out = c_ubyte()
        result = ch341dll.CH341ReadI2C(self.index, dev_addr, addr, byref(out))
        if not result:
            raise CH341Error("Operation Failed.")
        return out.value

    def i2c_read(self, dev_addr, addr, length, buf=None):
        if buf is None:
            read_buf = (c_ubyte * length)()
        else:
            read_buf = (c_ubyte * length).from_buffer(buf)
        write_buf = (c_ubyte * 2)((dev_addr << 1), addr)
        result = ch341dll.CH341StreamI2C(
            self.index, 2, byref(write_buf), length, byref(read_buf)
        )
        if not result:
            raise CH341Error("Operation Failed.")
        return read_buf

    def i2c_write_byte(self, dev_addr, addr, byte):
        result = ch341dll.CH341WriteI2C(self.index, dev_addr, addr, byte)
        if not result:
            raise CH341Error("Operation Failed.")

    def i2c_write(self, dev_addr, addr, length, data):
        buf = bytearray([dev_addr << 1, addr])
        buf.extend(data)
        write_buf = (c_ubyte * (length + 2)).from_buffer(buf)

        result = ch341dll.CH341StreamI2C(self.index, length + 2, byref(write_buf), 0, 0)
        if not result:
            raise CH341Error("Operation Failed.")

    def set_eeprom_type(self, eeptom_type):
        self.eeprom = eeptom_type

    def eeprom_read(self, addr, length, buf):
        read_buf = (c_ubyte * length).from_buffer(buf)

        result = ch341dll.CH341ReadEEPROM(
            self.index, self.eeprom, addr, length, byref(read_buf)
        )
        if not result:
            raise CH341Error("Operation Failed.")

    def eeprom_write(self, addr, length, buf):
        write_buf = (c_ubyte * length).from_buffer(buf)

        result = ch341dll.CH341WriteEEPROM(
            self.index, self.eeprom, addr, length, byref(write_buf)
        )
        if not result:
            raise CH341Error("Operation Failed.")


eeprom_enum = [
    "ID_24C01",
    "ID_24C02",
    "ID_24C04",
    "ID_24C08",
    "ID_24C16",
    "ID_24C32",
    "ID_24C64",
    "ID_24C128",
    "ID_24C256",
    "ID_24C512",
    "ID_24C1024",
    "ID_24C2048",
    "ID_24C4096",
]
globals().update({i[1]: i[0] for i in enumerate(eeprom_enum)})

IC_VER_CH341A = 0x20
IC_VER_CH341A3 = 0x30

__all__ = [
    "CH341Error",
    "IC_VER_CH341A",
    "IC_VER_CH341A3",
    "Ch341",
    "get_dll_version",
    "get_drv_version",
]

__all__.extend(eeprom_enum)
