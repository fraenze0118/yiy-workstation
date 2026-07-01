// v0.4.0 — TinyUSB build flags (Arduino-ESP32 3.x build_opt.h)
// 放在 sketch 目录下, IDE/CLI 编译时自动载入.
//
// PID=0x4001: 区分新固件 (v0.4.0 TinyUSB) 与旧固件 (PID=0x1001 Hardware CDC)
// VID=0x303A: Espressif, 不变. Launcher 按 VID 检测设备, SDK 亦然.

-DUSB_VID=0x303A
-DUSB_PID=0x4001

// TinyUSB CDC RX FIFO (byte). 默认 64. B 命令逐块读时不依赖大缓冲,
// 但 process_serial 批量处理时加大缓冲减少丢字节风险.
-DCFG_TUD_CDC_RX_BUFSIZE=512

// 日志 (调试时可开启, 默认关)
// -DCFG_TUD_CDC_DEBUG=1
// -DCFG_TUD_LOG_LEVEL=3
