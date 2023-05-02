import ch341

with ch341.Ch341(0) as dev:
    dev.set_eeprom_type(ch341.EEPROM_24C256)
    # dev.eeprom_write(0x10, bytearray([0xAC]*12))
    buf = dev.eeprom_read(0x10, length=12)
    print([hex(i) for i in buf])
