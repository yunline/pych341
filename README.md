# PyCh341

*注意：本库尚在开发中，API可能频繁变化*

CH341 是一个 USB 总线的转接芯片，通过 USB 总线提供异步串口、打印口、并口以及常用的 2 线和 4 线等同步串行接口。  

本库提供ch341 API的python绑定，底层API由WCH提供，详见[https://www.wch.cn/](https://www.wch.cn/)。

### 安装
```
python setup.py install
```

### 版本依赖
- python 3.10+

### 开发进度

**功能**
- [x] i2c
- [x] spi
- [x] gpio
- [ ] 中断回调

**例程**
- [x] mpu6050例程
- [ ] ssd1306例程
- [x] at24cXX例程

**平台支持**
- [x] Windows
- [ ] Linux
