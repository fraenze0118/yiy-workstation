# Yiy-Workstation

**ESP32-S3 驱动的多功能桌面外设——带屏幕、按键、编码器和麦克风的迷你终端。**

```
┌─ PC (Python) ────────────────────────────────┐
│  tomato.py / paint.py / screen_mirror.py     │
│               vckb/device.py                 │
└──────────────────┼───────────────────────────┘
                   │ USB CDC Serial
┌──────────────────┼───────────────────────────┐
│  ESP32-S3 固件   │ 文本命令解析 / 输入采集    │
│  ┌────┬────┬────┬┴────┐                      │
│  │TFT │按键│编码│麦克风│                      │
│  └────┴────┴────┴─────┘                      │
└──────────────────────────────────────────────┘
```

**一套固件，不刷不改。PC 端 Python SDK 驱动所有交互逻辑。**

---

## 快速开始

### 1. 烧录固件

用 Arduino IDE 打开 `firmware/arduino/vc-keyboard-pc/vc-keyboard-pc.ino`，烧录到 ESP32-S3（仅需一次）。

必需的板子配置（选错会导致 USB 串口不工作）：

```
Board:            ESP32S3 Dev Module
USB Mode:         Hardware CDC and JTAG
USB CDC On Boot:  Enabled
PSRAM:            Disabled
Flash Size:       16MB (128Mb)
```

依赖库（Arduino Library Manager 安装）：Adafruit GFX Library、Adafruit ST7789 Library、ESP_I2S（Arduino-ESP32 3.x 内置）。

### 2. 安装 Python 依赖

```
pip install pyserial            # 必需
pip install numpy pillow        # screen_mirror / pattern_test 等位图示例需要
```

### 3. 外设自检

```
cd sdk/python
python -B vckb/examples/self_test.py
```

屏幕显示按键状态、编码器位置、麦克风峰值。

### 4. 番茄钟

```
python -B vckb/examples/tomato.py
```

KEY1 开始/暂停，KEY5 重置，编码器调时长。

### 5. 屏幕镜像

```
python -B vckb/examples/screen_mirror.py
```

把 PC 屏幕实时投射到设备 320×240 屏（KEY1 暂停，KEY5 退出）。
USB Full Speed 带宽下全屏约 6–7 FPS，静止/局部变化时差分只传变化区域，帧率更高。

### 6. 显示通路自检

```
python -B vckb/examples/solid_test.py     # 纯色矩形: 验证位图分块/颜色
python -B vckb/examples/pattern_test.py   # 全屏色带: 验证整屏绘制
```

---

## 硬件

| 组件 | 型号 | GPIO |
|------|------|------|
| MCU | ESP32-S3-WROOM-1-N16R8 | — |
| 屏幕 | 2.8" TFT 320×240 (ST7789) | CS10 DC8 RST9 MOSI11 SCK12 |
| 按键 ×5 | 机械轴 | 3, 4, 5, 6, 7 |
| 拨动开关 | ST-0-102-A01 | 17 |
| 编码器 | PEC11L-4210F | A=45 B=46 BTN=42 |
| 麦克风 | GSA4030H10-F26-8P (PDM) | CLK=14 DATA=15 |

详见 `doc/PINOUT.md`（本地维护）。

---

## Python SDK

```python
from vckb import VCKeyboard, RED, WHITE

with VCKeyboard() as kb:
    kb.fill(RED)
    kb.text(10, 20, "Hello!", size='L', color=WHITE)

    @kb.on_key('KEY1', 'down')
    def on_k1():
        print("KEY1 pressed!")

    kb.run()
```

| 方法 | 说明 |
|------|------|
| `fill(color)` | 全屏填充 |
| `rect(x,y,w,h,color)` | 填充矩形 |
| `text(x,y,text,size,color)` | 显示文字 (S/M/L/X) |
| `push_frame(x,y,w,h,rgb565)` | 推送 RGB565 位图 |
| `mic_start()` / `mic_stop()` | 开启/停止麦克风流 |
| `on_key(key,action)` | 注册按键回调 |
| `on_encoder(divider=N)` | 注册编码器回调, divider 调灵敏度 |
| `on_switch()` | 注册拨动开关回调 |
| `on_audio()` | 注册音频数据回调 |

---

## 文档

> `doc/` 与 `scripts/` 已 `.gitignore`（本地维护，不入库）。下表带 † 为本地文档。

| 文档 | 内容 |
|------|------|
| `doc/PINOUT.md` † | 硬件引脚 + 驱动总结 |
| `doc/DESIGN.md` † | 总体设计 + 实施计划 |
| `doc/PROTOCOL.md` † | 串口协议规范 (给写 app 的人看) |
| `doc/ARCHITECTURE.md` † | 通信原理深度解析 |
| `doc/SDK_PITFALLS.md` † | 开发踩坑记录 |
| `doc/PERFORMANCE_PLAN.md` † | 帧率架构改进计划（压缩/差分/TinyUSB 取舍） |

---

## 性能说明

- **位图传输**: USB-Serial-JTAG 为 USB Full Speed (~1 MB/s)，全屏 320×240×2≈143KB 受带宽限制约 6–7 FPS 上限。SDK 已做：字节取反查表化、按 ≤3072B 分块逐块 OK 流控、固件整块 block write + 80MHz SPI、screen_mirror 行差分 + BILINEAR。
- **ESP32-S3 USB OTG 仅支持 Full Speed（无 HS PHY）**，切 TinyUSB 不能突破物理带宽。突破 7 FPS 软上限需减少数据量（软件压缩/细粒度差分），方案见 `doc/PERFORMANCE_PLAN.md` †。

---

## 项目结构

```
vc-keyboard/
├── README.md
├── CLAUDE.md                     ← Claude 项目上下文 (入库)
├── .gitignore                    ← doc/ 与 scripts/ 本地维护
├── doc/  †                       ← 本地文档 (PINOUT/DESIGN/PROTOCOL/ARCHITECTURE/SDK_PITFALLS/PERFORMANCE_PLAN)
├── scripts/ †                    ← 本地工具脚本
├── firmware/
│   └── arduino/
│       ├── vc-keyboard-pc/       ← 通用 PC 外设固件 (烧录这个)
│       ├── backup/               ← 旧版固件
│       └── test/                 ← 手动测试固件
└── sdk/python/vckb/
    ├── device.py                 ← 设备驱动
    ├── framebuf.py               ← 帧缓冲 + 行差分推送
    └── examples/
        ├── self_test.py          ← 全外设自检
        ├── tomato.py             ← 番茄钟
        ├── paint.py              ← 画板
        ├── screen_mirror.py      ← PC 屏幕镜像
        ├── solid_test.py         ← 纯色矩形 (位图通路自检)
        ├── pattern_test.py       ← 全屏色带 (整屏绘制自检)
        ├── mini_test.py          ← 单帧传输对比
        └── frame_test.py         ← 渐变帧自检
```
