from ch341 import *
import struct

MPU6050_ADDR = 0x68


def mpu6050_read_data(dev):
    # [ax,ay,az,t,gx,gy,gz]
    tmp = dev.i2c_read(MPU6050_ADDR, 0x3B, length=14)
    return struct.unpack("!hhhhhhh", tmp)


def mpu6050_read_temp(dev):
    tmp = dev.i2c_read(MPU6050_ADDR, 0x41, length=2)
    return struct.unpack("!h", tmp)[0] / 340 + 36.53


def mpu6050_read_acce(dev):
    tmp = dev.i2c_read(MPU6050_ADDR, 0x3B, length=6)
    return struct.unpack("!hhh", tmp)


def mpu6050_read_gyro(dev):
    tmp = dev.i2c_read(MPU6050_ADDR, 0x43, length=6)
    return struct.unpack("!hhh", tmp)


def mpu6050_write_reg(dev, addr, dat):
    dev.i2c_write(MPU6050_ADDR, addr, bytearray([dat]))


def mpu6050_init(dev):
    mpu6050_write_reg(dev, 0x6B, 0x00)  # PWR_MGMT_1
    mpu6050_write_reg(dev, 0x19, 0x07)  # SMPLRT_DIV
    mpu6050_write_reg(dev, 0x1A, 0x06)  # CONFIG
    mpu6050_write_reg(dev, 0x1C, 0x00)  # ACCEL_CONFIG
    mpu6050_write_reg(dev, 0x1B, 0x18)  # GYRO_CONFIG


with Ch341(0) as dev:
    dev.set_i2c_speed(3)
    mpu6050_init(dev)
    while 1:
        print("gyro(%d\t%d\t%d\t)" % mpu6050_read_gyro(dev))
