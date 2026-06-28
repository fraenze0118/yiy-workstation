"""
屏幕镜像 — PC 屏幕实时投射到设备 (320×240)

原理:
  1. PIL 截取 PC 屏幕 → 缩放到 320×240
  2. numpy 转 RGB565 → 按行差分推送
  3. 只推送变化区域，节省带宽

按键:
  KEY1 = 暂停/继续
  KEY5 = 退出
"""

import os, pathlib, time

from vckb.apps.base import AppDefinition

APP = AppDefinition(
    id="screen_mirror",
    name="Screen Mirror",
    name_zh="屏幕镜像",
    description="Real-time PC screen mirroring at ~6 FPS",
    icon="🖥️",
    category="tool",
    controls={
        "KEY1": "暂停/继续",
        "KEY5": "退出",
    },
    module="vckb.apps.screen_mirror",
    requires=["numpy", "pillow"],
)


def main():
    import numpy as np
    from PIL import Image, ImageGrab

    from vckb import VCKeyboard, BLACK, WHITE
    from vckb.framebuf import DISPLAY_W, DISPLAY_H

    stop_signal = os.environ.get("VCKB_STOP_SIGNAL", "")

    STATUS_BAR_H = 16

    def rgb_to_565(r, g, b):
        r16 = r.astype('<u2')
        g16 = g.astype('<u2')
        b16 = b.astype('<u2')
        return ((r16 & 0xF8) << 8) | ((g16 & 0xFC) << 3) | (b16 >> 3)

    def capture_screen():
        pil = ImageGrab.grab()
        return pil.resize((DISPLAY_W, DISPLAY_H), Image.BILINEAR)

    def pil_to_rgb565(pil):
        arr = np.array(pil, dtype=np.uint8)
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        rgb565 = rgb_to_565(r, g, b).astype('<u2')
        return rgb565.tobytes()

    def push_chunk(kb, curr, start_row, h):
        row_bytes = DISPLAY_W * 2
        off = start_row * row_bytes
        kb.push_frame(0, start_row, DISPLAY_W, h, curr[off: off + h * row_bytes])

    def push_diff(kb, prev, curr):
        row_bytes = DISPLAY_W * 2
        prev_rows = np.frombuffer(prev, dtype=np.uint8).reshape(DISPLAY_H, row_bytes)
        curr_rows = np.frombuffer(curr, dtype=np.uint8).reshape(DISPLAY_H, row_bytes)
        row_changed = np.any(prev_rows != curr_rows, axis=1)

        start_row = -1
        for row in range(STATUS_BAR_H, DISPLAY_H):
            if row_changed[row]:
                if start_row < 0:
                    start_row = row
            elif start_row >= 0:
                push_chunk(kb, curr, start_row, row - start_row)
                start_row = -1

        if start_row >= 0:
            push_chunk(kb, curr, start_row, DISPLAY_H - start_row)

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
            kb.text(4, 2, "PAUSED" if paused else "LIVE",
                    size='S', color=0xFFE0 if paused else 0x07E0)

        kb.rect(0, 0, 320, 16, 0x2104)
        kb.text(4, 2, "LIVE", size='S', color=0x07E0)

        prev_frame = None
        frame_count = 0
        fps_time = time.time()

        while running:
            kb.poll()

            # 停止信号检查
            if stop_signal and pathlib.Path(stop_signal).exists():
                running = False
                break

            if paused:
                time.sleep(0.1)
                continue

            t0 = time.time()

            pil = capture_screen()
            rgb565_data = pil_to_rgb565(pil)

            if prev_frame is None:
                row_bytes = DISPLAY_W * 2
                off = STATUS_BAR_H * row_bytes
                h = DISPLAY_H - STATUS_BAR_H
                kb.push_frame(0, STATUS_BAR_H, DISPLAY_W, h, rgb565_data[off:])
            else:
                push_diff(kb, prev_frame, rgb565_data)
            prev_frame = rgb565_data

            frame_count += 1

            if time.time() - fps_time >= 1.0:
                kb.rect(200, 0, 120, 16, 0x2104)
                kb.text(204, 2, f"FPS:{frame_count}", size='S', color=WHITE)
                frame_count = 0
                fps_time = time.time()

        kb.clear()
        if stop_signal:
            pathlib.Path(stop_signal).unlink(missing_ok=True)
