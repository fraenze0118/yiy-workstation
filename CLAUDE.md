# Yiy-Workstation — Claude 项目上下文

## 项目概述

这是 ESP32-S3 驱动的多功能桌面外设（原名VC-Keyboard）。硬件通过 USB CDC Serial 连接 PC，PC 负责所有逻辑，设备负责 IO（显示、按键、编码器、麦克风）。

## 关键文件

> `doc/` 与 `scripts/` 已在 `.gitignore` 中（本地维护，不入库）；下表中带 † 的为本地文档。
> 仓库内持久维护的是 `firmware/`、`sdk/`、`launcher/`、`CLAUDE.md`、`README.md`。

| 文件 | 用途 |
|------|------|
| `firmware/arduino/vc-keyboard-pc/vc-keyboard-pc.ino` | 通用 PC 外设固件（仅需烧录一次） |
| `sdk/python/vckb/device.py` | Python SDK 设备驱动 |
| `sdk/python/vckb/framebuf.py` | 帧缓冲 + 行差分推送 |
| `sdk/python/vckb/apps/` | v0.2.0 应用模块（标准接口：`APP` + `main()`） |
| `sdk/python/vckb/examples/` | 开发用 thin wrapper（import from apps/） |
| `launcher/` | Electron + Vue 3 GUI Launcher（v0.2.0） |
| `doc/PINOUT.md` † | 硬件引脚和驱动总结 |
| `doc/DESIGN.md` † | 总体设计文档 |
| `doc/PROTOCOL.md` † | 串口协议规范 |
| `doc/ARCHITECTURE.md` † | 通信原理 |
| `doc/SDK_PITFALLS.md` † | 开发踩坑记录 |
| `doc/PERFORMANCE_PLAN.md` † | 帧率架构改进计划（压缩/差分/TinyUSB 取舍） |
| `doc/v0.2.0-design.md` † | GUI Launcher 设计方案 |
| `doc/v0.2.1-design.md` † | Voice Meter 应用设计 |

## USB 架构 (v0.4.0+)

固件使用 **USB-OTG (TinyUSB)**，PID `0x4001` (旧 Hardware CDC 为 `0x1001`)。当前 Phase 1 仅 CDC，后续加 HID Keyboard + UAC Microphone。Launcher/SDK 按 VID `0x303A` 检测设备 (与 PID 无关，新旧固件均可检测)。

## 通信协议

文本命令（`\n` 定界）+ 位图数据混传：

**下行 (PC→设备)**:
- 文本命令: `F,0000\n` / `R,10,10,100,50,F800\n` / `T,20,30,M,FFFF,Hello\n`
- 位图命令: `B,x,y,w,h\n` + w\*h\*2 字节 RGB565 原始数据。**SDK 按行分块推送**（单块 ≤ `MAX_CHUNK_BYTES=3072`，远小于固件 4096 RX 缓冲），每块等固件 `OK` 再发下一块（逐块流控）。固件小块整块 `drawRGBBitmap` block write，大块退化为逐行。

**上行 (设备→PC)**:
- 按键事件: `K:D:KEY1\n` / `K:U:KEY3\n`
- 编码器: `E:CW:3\n` / `E:CCW:1\n` / `E:BTN\n`
- 开关: `SW:ON\n` / `SW:OFF\n`
- 音频流: `\xCC\xDD` + 2B 长度 LE + PCM16 数据
- 位图应答: 每块处理完成发 `OK\n`；行读取超时（字节丢失）发 `B:ERR:rd=N\n`（或 `B:ERR:row=N\n`）并排空 RX 残留，PC 收到后重发该块

## 硬件外设

| 外设 | GPIO | 关键驱动细节 |
|------|------|------------|
| TFT ST7789 | CS10 DC8 RST9 MOSI11 SCK12 | SPI_MODE2, 横屏 setRotation(1) |
| 按键 ×5 | 3, 4, 5, 6, 7 | INPUT_PULLUP, 低电平触发, 30ms 去抖 |
| 拨动开关 | 17 | INPUT_PULLUP |
| 编码器 PEC11L | A=45 B=46 BTN=42 | ISR: 边沿+电平判断, REG_READ(GPIO_IN1_REG) 原子读取 AB |
| 麦克风 GSA4030H10 | CLK=14 DATA=15 | 必须用 ESP_I2S.h (非 driver/i2s.h) |

## 开发中的重要约束

1. **麦克风驱动**: 只能 `#include <ESP_I2S.h>`，不能同时 include `driver/i2s.h`（类型冲突）。ESP32-S3 只有 I2S0 支持 PDM。
2. **串口缓冲**: 固件必须 `Serial.setRxBufferSize(8192)` 在 `Serial.begin()` 之前。TinyUSB 模式下这是 Arduino 层软件缓冲，低层 `CFG_TUD_CDC_RX_BUFSIZE=512` (见 `build_opt.h`). B 命令逐块读 + `delay(0)` yield 给 USB task, 不依赖大缓冲.
3. **编码器 ISR**: 用 `REG_READ(GPIO_IN1_REG)` 一次读 A 和 B，避免竞态。边沿+电平判断方向，不用状态机 LUT。
4. **屏幕**: 横屏 320×240 (`setRotation(1)`)，不是竖屏。
5. **协议**: 无握手无校验，USB CDC 可靠传输。文本命令以 `\n` 定界。
6. **位图推送（已修复）**: 使用 `B,x,y,w,h\n` + 原始 RGB565 数据。固件采用**逐行读取+逐行绘制**（每行 w*2 字节，`delay(0)` 让出 CPU 防 USB 任务饿死）。**Python 侧按行分块推送**（`push_frame` → `_push_chunk`，单块 ≤ `MAX_CHUNK_BYTES=2048` 字节，远小于固件 4096 RX 缓冲），每块等固件 `OK\n` 应答再发下一块（逐块流控）。固件行读取超时（字节丢失）时回 `B:ERR:row=N` 并排空 RX 残留，Python 收到后重发该块。**单块必须 < 4096**：整帧一次性推送会撑满 RX 缓冲，固件忙于 SPI 绘制时丢字节 → 行错位/字节交换花屏（绿→红、蓝→绿、黄→紫 是奇数字节偏移的指纹）。
7. **Python poll**: 不用 `in_waiting`（Windows USB CDC 不可靠），用 `ser.timeout=0.1` + `ser.read(4096)`。音频包可能跨 read() 边界，需要累积解析。
8. **颜色取反补偿**: ST7789 的 INVON 会使显示颜色取反。Python 侧在 `push_frame` 中对每字节预先取反 (`~b & 0xFF`)，双重取反后颜色正确。
9. **uint16 载荷限制**: `\xAA\xBB` 帧的 `payload_len` 是 uint16（最大 65535）；但当前 `B,` 文本方案受 RX 缓冲约束，单块 ≤ 2048 字节（见第 6 条），全屏 320×240 按行分多块推送。

## 固件 B 命令处理器

`B,x,y,w,h\n` 命令的处理流程（`execute_command` 中）：

```
1. 解析 x,y,w,h
2. malloc(w*2) 分配一行缓冲区
3. for row in 0..h-1:
     busy-wait 读取 w*2 字节 (含 delay(0) yield)
     drawRGBBitmap(x, y+row, line, w, 1)  逐行绘制
     行读取超时(5s) → ok=false, break
4. free(line)
5. ok ? Serial.println("OK") : 排空 RX 残留 + Serial.println("B:ERR:row=N")
```

**为什么逐行而不是全缓冲**：
- 全缓冲 malloc(w\*h\*2) 量大，`drawRGBBitmap` 整帧绘制时阻塞太久
- 逐行只有 640 字节/行缓冲，每行绘制快，数据读取和绘制交替进行
- `delay(0)` 在每行忙等循环中至关重要：ESP32 的 USB 接收依赖 FreeRTOS 任务，忙等不让出 CPU 会饿死 USB 任务，导致数据永远进不来

**为什么 Python 侧还要按行分块（`_push_chunk`）**：
- 固件在 `drawRGBBitmap`（SPI）期间不读串口，若一次性推送 w\*h\*2 字节，4096 RX 环形缓冲会被撑满 → 字节丢失 → 行错位（奇数字节偏移 → RGB565 低/高字节交换，纯色变成字节交换色）
- 单块 ≤ 2048 字节保证整块都能落入 RX 缓冲，不溢出；逐块 `OK` 应答提供流控，PC 不会超过固件消化速度
- 固件 `B:ERR` + RX 排空保证失败可被 PC 检测并重发，且不污染下一条命令

## ~~`\xAA\xBB` 二进制帧协议~~ (已移除)

固件曾实现 `\xAA\xBB` 二进制帧协议（`handle_frame_byte`/`start_binary_frame`），但 Python SDK 一直使用 `B,` 文本命令方案，该路径是带状态机 bug 的死代码，且 `process_serial` 里的 0xAA 帧头检测存在隐患（`T,` 文本命令正文中若出现 `0xAA 0xBB` 字节序列会被误判进入二进制模式）。已整体删除：状态变量 `bf_*`/`frame_*`、`handle_frame_byte`/`start_binary_frame` 函数、`process_serial` 中的 `have_pending`/`pending_byte` 预读缓存与 0xAA 检测全部移除，`process_serial` 现仅做 `\n` 定界的文本解析。位图数据由 `B` 分支内部直接 `Serial.read()`，不经过 `process_serial`，故数据中的任意字节都不会干扰文本解析。

## 屏幕镜像 (screen_mirror.py)

当前使用 `PIL.ImageGrab.grab()` 截屏（非 mss），因为 PIL 直接返回 RGB Image 对象，无 raw bytes 格式歧义。

关键实现细节：
- `rgb_to_565`: 必须先 `.astype('<u2')` 转 uint16 再做位运算，**uint8 左移 8 位会溢出归零**
- 截屏缩放用 `Image.BILINEAR`（非 LANCZOS，性能优先，320×240 缩略图画质足够）
- 首帧全屏推送（跳过顶部 16 行状态栏，帧数据只推第 16 行以下）
- 后续帧按行差分推送（`_push_diff`）：numpy 一次性算出每行变化标志（`np.any(prev!=curr, axis=1)`），再用轻量 Python 循环合并连续变化行段
- 变化行段经 `_push_chunk` → `push_frame`，由 SDK 按 `MAX_CHUNK_BYTES=3072` 自动拆分（不再用旧的 102 行/块 uint16 限制）

## 性能上限与优化

USB-Serial-JTAG 外设为 **USB Full Speed（~1MB/s）**，全屏刷新 320×224×2≈143KB 受带宽限制，**理论约 6-7 FPS 上限**，无法靠软件突破（除非减数据量或换 USB High Speed）。

已做的提速优化：
- SDK 字节取反用 `bytes.translate` 查表（全屏 ~40ms → ~1ms），替代逐字节生成器
- 固件 `B` 命令小块（≤4KB）整块读入 + 单次 `drawRGBBitmap` block write，省逐行 `startWrite/setAddrWindow/endWrite` 开销；大块退化为逐行流式
- 固件 SPI 速率 `tft.setSPISpeed(80000000)`（默认 32MHz），整屏绘制提速 ~2x（走线不稳降回 40MHz）
- `MAX_CHUNK_BYTES` 2048→3072，减少 25% 逐块 OK 往返

进一步突破带宽上限的选项（未实现，详见 `doc/PERFORMANCE_PLAN.md`）：软件压缩（行类型编码/LZ4，主推）、块级/行内 run 差分。注意 ESP32-S3 的 USB OTG 集成 PHY **仅支持 Full Speed（12Mbps）**，切 TinyUSB 不能突破物理带宽（早期"480Mbps"说法有误）。

## Arduino IDE 配置

**v0.4.0+ (TinyUSB)**:
```
Board: ESP32S3 Dev Module
USB Mode: USB-OTG (TinyUSB)
USB CDC On Boot: Enabled
USB Firmware MSC On Boot: Disabled
PSRAM: Disabled
Flash Size: 16MB (128Mb)
```
> PID 覆写为 `0x4001` (旧 Hardware CDC 为 `0x1001`), 见 `build_opt.h`.

**v0.3.x 及之前 (Hardware CDC, 已废弃)**:
```
USB Mode: Hardware CDC and JTAG
```

## 依赖库

- Adafruit GFX Library
- Adafruit ST7789 Library
- ESP_I2S (Arduino-ESP32 3.x 内置)
- Python: pyserial, numpy, pillow
- Node.js 18+ (仅 Launcher 开发, 用户端打包后无需)

## v0.2.1 — Voice Meter

实时麦克风音频可视化: 64 频段 FFT 频谱 + 波形图 + dB 峰值。详见 `doc/v0.2.1-design.md`。

### 当前应用列表 (5 apps)

| ID | 名称 | 说明 |
|----|------|------|
| tomato | 番茄钟 | Pomodoro timer |
| screen_mirror | 屏幕镜像 | PC 屏幕投射 ~6 FPS |
| voice_meter | 语音电平表 | FFT 频谱 + 波形 |
| self_test | 外设自检 | 全外设验证 |
| image_test | 位图测试 | 4 阶段 push_frame 验证 |

### Python 包名 vs import 名

pip 包名 `pillow` → Python `import PIL`。Launcher 的 checkPythonPkg 中有映射表。

### PYTHONPATH 自动注入

Launcher 启动子进程时自动将本地 `sdk/python/` 加入 `PYTHONPATH`，无需 `pip install -e`。

## v0.2.0 — GUI Launcher

Electron + Vue 3 + Tailwind CSS 桌面应用，作为用户入口。详见 `doc/v0.2.0-design.md`。

```
launcher/
├── src/
│   ├── main/           # Electron Main Process (Node.js)
│   │   ├── index.ts         # 窗口 + 生命周期
│   │   ├── device-manager.ts # serialport 设备检测
│   │   ├── app-runner.ts    # Python 子进程管理
│   │   ├── app-registry.ts  # 应用注册表 (5 apps)
│   │   └── ipc-handlers.ts  # IPC 路由
│   ├── preload/        # contextBridge 安全桥
│   └── renderer/       # Vue 3 前端
│       └── src/components/  # 6 个 SFC 组件
└── electron-builder.yml      # Windows .exe 打包
```

### 开发命令

```
cd launcher
npm install          # 安装依赖
npm run dev          # Electron + Vue HMR 开发
npm run build        # 生产构建
npm run package:win  # 构建 + 打包 Windows .exe
```

### 应用模块规范

每个 `vckb/apps/<id>.py` 提供：
- `APP: AppDefinition` — 元数据（id, name, icon, category, controls, module, requires）
- `main()` — 入口函数，内部创建 `VCKeyboard()` 并运行事件循环
- 主循环中检查 `os.environ.get("VCKB_STOP_SIGNAL")` 信号文件以支持干净停止

### Launcher 停止应用的三级策略

```
L1 (0s):  写入信号文件 → Python poll 检测 → 自行清理退出
L2 (3s):  SIGTERM → 优雅退出
L3 (5s):  SIGKILL → 强制终止
```

### 固件 INVON 补偿宏

ST7789 INVON 取反全部颜色。固件侧直接绘制（fillScreen/setTextColor/drawRect 等）需用 `INV(c)` 宏包裹每个颜色值：`#define INV(c) ((uint16_t)(~(c)))`

## 已知未解决问题

- ST7789 INVON 颜色取反的根因需在显示库初始化层面定位并修复（当前 Python 侧 byte complement 是 workaround）

## 已修复问题

- **位图字节丢失导致行错位/花屏**（solid_test 底部花屏、frame_test 高度不足）：根因是一次性推送 w\*h\*2 字节撑满固件 4096 RX 缓冲，固件 SPI 绘制期间丢字节。修复：Python `push_frame` 按行分块（单块 ≤ `MAX_CHUNK_BYTES=3072`）+ 逐块 `OK` 流控（`_push_chunk`）；固件 `B` 分支超时改回 `B:ERR` 并排空 RX 残留，Python 检测后重发。指纹：奇数字节偏移使纯色变成字节交换色（绿 0x07E0→红、蓝 0x001F→绿、黄 0xFFE0→紫）。后续提速：取反查表化、固件小块整块 block write、SPI 80MHz、`MAX_CHUNK_BYTES` 2048→3072（详见「性能上限与优化」）。
- **`drawRGBBitmap` 逐行绘制 (h=1) "底部花屏"**：经分块修复后 pattern_test / screen_mirror 全屏渐变与镜像均无花屏，确认该症状本就是位图字节丢失 bug 的表现，非独立显示层问题。
- **`\xAA\xBB` 二进制帧死代码移除**：删除带状态机 bug 的 `handle_frame_byte` 路径及 `process_serial` 的 0xAA 帧头检测/`have_pending` 预读缓存，消除 `T,` 文本含 `0xAA 0xBB` 时误入二进制模式的隐患。
- **逐块调试刷屏**：移除固件 `execute_command` 的 `EXEC:` 打印；SDK `_push_chunk` 成功静默，仅 `B:ERR`/超时重试时打印。
