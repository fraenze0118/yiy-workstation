"""
PC 屏幕镜像 → VC-Keyboard 设备 (320×240 实时小分屏)

依赖: pip install numpy pillow

原理:
  1. PIL 截取 PC 屏幕 → 缩放到 320×240 (BILINEAR, 性能优先)
  2. numpy 转 RGB565 → 帧缓冲按行差分
  3. 只推送变化的连续行段 → push_frame 按 ≤3KB 分块 + 逐块 OK 流控

性能:
  USB-Serial-JTAG 为 USB Full Speed (~1MB/s), 全屏刷新 ~143KB 受带宽限制
  约 6-7 FPS 上限; 静止/局部变化时差分只传变化区域, 帧率显著更高.

按键:
  KEY1 = 暂停/继续
  KEY5 = 退出
  ENC  = 无操作 (预留)
"""

import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
from PIL import Image, ImageGrab

from vckb import VCKeyboard, BLACK, WHITE
from vckb.framebuf import DISPLAY_W, DISPLAY_H

STATUS_BAR_H = 16  # 顶部状态栏高度 (像素)

def rgb_to_565(r, g, b):
    """numpy 向量化 RGB888 → RGB565 (先转 uint16 防溢出)"""
    r16 = r.astype('<u2')
    g16 = g.astype('<u2')
    b16 = b.astype('<u2')
    return ((r16 & 0xF8) << 8) | ((g16 & 0xFC) << 3) | (b16 >> 3)

def capture_screen():
    """截取整个屏幕 → 缩放到 320×240 RGB"""
    pil = ImageGrab.grab()  # PIL 直接截屏, 返回 RGB Image, 无 raw bytes 歧义
    # BILINEAR 比 LANCZOS 快约 3x, 320×240 缩略图画质足够; 性能优先
    return pil.resize((DISPLAY_W, DISPLAY_H), Image.BILINEAR)

def pil_to_rgb565(pil):
    """PIL Image → RGB565 bytes"""
    arr = np.array(pil, dtype=np.uint8)
    r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    rgb565 = rgb_to_565(r, g, b).astype('<u2')
    return rgb565.tobytes()

def main():
    with VCKeyboard() as kb:
        kb.clear()
        kb.text(50, 100, "Screen Mirror", size='L', color=0x07E0)
        kb.text(40, 130, "Starting...", size='M', color=0xFFFF)
        time.sleep(1)

        running = True
        paused = False

        @kb.on_key('KEY5', 'down')
        def quit_app():
            nonlocal running
            running = False

        @kb.on_key('KEY1', 'down')
        def toggle_pause():
            nonlocal paused
            paused = not paused
            kb.rect(0, 0, 320, 16, 0x2104)
            kb.text(4, 2, "PAUSED" if paused else "LIVE", size='S', color=0xFFE0 if paused else 0x07E0)

        kb.rect(0, 0, 320, 16, 0x2104)
        kb.text(4, 2, "LIVE", size='S', color=0x07E0)

        prev_frame = None
        frame_count = 0
        fps_time = time.time()

        print("Screen Mirror started. KEY1=pause, KEY5=quit")

        while running:
            kb.poll()

            if paused:
                time.sleep(0.1)
                continue

            t0 = time.time()

            # 截屏
            pil = capture_screen()
            rgb565_data = pil_to_rgb565(pil)

            # 首帧全屏推送 (跳过状态栏区域, 由文字命令绘制)
            if prev_frame is None:
                row_bytes = DISPLAY_W * 2
                off = STATUS_BAR_H * row_bytes
                h = DISPLAY_H - STATUS_BAR_H
                kb.push_frame(0, STATUS_BAR_H, DISPLAY_W, h, rgb565_data[off:])
            else:
                _push_diff(kb, prev_frame, rgb565_data)
            prev_frame = rgb565_data

            frame_count += 1
            elapsed = time.time() - t0

            # 每秒打印 FPS
            if time.time() - fps_time >= 1.0:
                kb.rect(200, 0, 120, 16, 0x2104)
                kb.text(204, 2, f"FPS:{frame_count}", size='S', color=WHITE)
                print(f"FPS: {frame_count}, last frame: {elapsed*1000:.0f}ms")
                frame_count = 0
                fps_time = time.time()

        kb.clear()

def _push_chunk(kb, curr: bytes, start_row: int, h: int):
    """推送一块连续变化行 (push_frame 内部会按 MAX_CHUNK_BYTES 再拆分)"""
    row_bytes = DISPLAY_W * 2
    off = start_row * row_bytes
    kb.push_frame(0, start_row, DISPLAY_W, h, curr[off : off + h * row_bytes])

def _push_diff(kb, prev: bytes, curr: bytes):
    """按行差分: 只推送变化的连续行段 (跳过状态栏区域).

    用 numpy 一次性算出每行是否变化, 再用轻量 Python 循环合并连续行段,
    避免逐行切片比较的 Python 开销.
    """
    row_bytes = DISPLAY_W * 2
    # 整帧按行 reshape, 一次比较得到每行的变化标志 (bool 数组)
    prev_rows = np.frombuffer(prev, dtype=np.uint8).reshape(DISPLAY_H, row_bytes)
    curr_rows = np.frombuffer(curr, dtype=np.uint8).reshape(DISPLAY_H, row_bytes)
    row_changed = np.any(prev_rows != curr_rows, axis=1)

    start_row = -1
    for row in range(STATUS_BAR_H, DISPLAY_H):
        if row_changed[row]:
            if start_row < 0:
                start_row = row
        elif start_row >= 0:
            _push_chunk(kb, curr, start_row, row - start_row)
            start_row = -1

    if start_row >= 0:
        _push_chunk(kb, curr, start_row, DISPLAY_H - start_row)

if __name__ == '__main__':
    main()
