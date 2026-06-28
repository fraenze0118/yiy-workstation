"""
位图传输综合测试 — 4 阶段自动验证 push_frame 通路

  Stage 1: 渐变帧 — 100×80 RGB 渐变矩形
  Stage 2: 编码对比 — numpy vs manual RGB565 色带
  Stage 3: 纯色矩形 — 5 个不同颜色/尺寸/位置的矩形
  Stage 4: 全屏色带 — 320×240 红|绿|蓝|白|黑 条纹

按键: KEY5 = 跳过当前阶段 / 退出
"""

import os, pathlib, time

from vckb.apps.base import AppDefinition

APP = AppDefinition(
    id="image_test",
    name="Image Test",
    name_zh="位图传输测试",
    description="4-stage push_frame validation: gradient, compare, solids, full-screen",
    icon="🖼️",
    category="test",
    controls={
        "KEY5": "跳过当前阶段 / 退出",
    },
    module="vckb.apps.image_test",
    requires=["numpy", "pillow"],
)

STAGE_WAIT = 3  # seconds between auto-advance


def _label(kb, text, sub=""):
    """Draw a stage label at the top of the screen."""
    from vckb import BLACK, WHITE
    kb.rect(0, 0, 320, 20, 0x2104)
    kb.text(4, 3, text, size="S", color=WHITE)
    if sub:
        kb.text(160, 3, sub, size="S", color=0x8410)


def stage1_gradient(kb):
    """100×80 red-green gradient rectangle (from frame_test)."""
    _label(kb, "Stage 1/4: Gradient Frame", "w=100 h=80")
    w, h = 100, 80
    data = bytearray(w * h * 2)
    for row in range(h):
        for col in range(w):
            r = (col * 255 // w) & 0xF8
            g = (row * 255 // h) & 0xFC
            color = (r << 8) | (g << 3)
            off = (row * w + col) * 2
            data[off] = color & 0xFF
            data[off + 1] = (color >> 8) & 0xFF
    kb.push_frame(10, 60, w, h, bytes(data))
    kb.text(120, 90, "R→Gradient", size="S", color=0xFFFF)


def stage2_compare(kb):
    """numpy vs manual RGB565 — top-left vs bottom-right (from mini_test)."""
    import numpy as np
    from vckb import WHITE

    _label(kb, "Stage 2/4: numpy vs manual", "100x80 x2")

    w, h = 100, 80
    stripe = w // 5

    # numpy version
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    rgb[:, 0 * stripe : 1 * stripe, 0] = 255
    rgb[:, 1 * stripe : 2 * stripe, 1] = 255
    rgb[:, 2 * stripe : 3 * stripe, 2] = 255
    rgb[:, 3 * stripe : 4 * stripe, :] = 255
    r = rgb[:, :, 0].astype("<u2")
    g = rgb[:, :, 1].astype("<u2")
    b = rgb[:, :, 2].astype("<u2")
    rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    kb.push_frame(0, 28, w, h, rgb565.astype("<u2").tobytes())
    kb.text(0, 110, "numpy", size="S", color=WHITE)

    # manual version
    data = bytearray(w * h * 2)
    for row in range(h):
        for col in range(w):
            if col < stripe:
                rv, gv, bv = 255, 0, 0
            elif col < stripe * 2:
                rv, gv, bv = 0, 255, 0
            elif col < stripe * 3:
                rv, gv, bv = 0, 0, 255
            elif col < stripe * 4:
                rv, gv, bv = 255, 255, 255
            else:
                rv, gv, bv = 0, 0, 0
            color = ((rv & 0xF8) << 8) | ((gv & 0xFC) << 3) | (bv >> 3)
            off = (row * w + col) * 2
            data[off] = color & 0xFF
            data[off + 1] = (color >> 8) & 0xFF
    kb.push_frame(110, 130, w, h, bytes(data))
    kb.text(110, 212, "manual", size="S", color=WHITE)
    kb.text(0, 230, "Should be identical R|G|B|W|BLK stripes", size="S", color=0x8410)


def stage3_solids(kb):
    """5 solid rectangles: R, G, B manual + W, Y numpy (from solid_test)."""
    import numpy as np
    from vckb import BLACK, WHITE

    _label(kb, "Stage 3/4: Solid Rectangles", "manual: R/G/B, numpy: W/Y")

    def push_solid(x, y, w, h, rv, gv, bv):
        color = ((rv & 0xF8) << 8) | ((gv & 0xFC) << 3) | (bv >> 3)
        row_bytes = w * 2
        line = bytearray(row_bytes)
        for i in range(0, row_bytes, 2):
            line[i] = color & 0xFF
            line[i + 1] = (color >> 8) & 0xFF
        kb.push_frame(x, y, w, h, bytes(line * h))

    def push_solid_np(x, y, w, h, rv, gv, bv):
        rgb = np.zeros((h, w, 3), dtype=np.uint8)
        rgb[:, :, 0] = rv
        rgb[:, :, 1] = gv
        rgb[:, :, 2] = bv
        r = rgb[:, :, 0].astype("<u2")
        g = rgb[:, :, 1].astype("<u2")
        b = rgb[:, :, 2].astype("<u2")
        rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        kb.push_frame(x, y, w, h, rgb565.astype("<u2").tobytes())

    push_solid(0, 28, 100, 60, 255, 0, 0)        # RED manual
    kb.text(30, 70, "R-man", size="S", color=WHITE)
    push_solid_np(110, 28, 100, 60, 0, 255, 0)    # GREEN numpy
    kb.text(140, 70, "G-np", size="S", color=BLACK)
    push_solid(220, 28, 90, 60, 0, 0, 255)        # BLUE manual
    kb.text(240, 70, "B-man", size="S", color=WHITE)

    push_solid_np(0, 130, 150, 50, 255, 255, 255) # WHITE numpy
    kb.text(40, 160, "W-np", size="S", color=BLACK)
    push_solid_np(160, 130, 160, 50, 255, 255, 0)  # YELLOW numpy
    kb.text(200, 160, "Y-np", size="S", color=BLACK)

    push_solid(0, 200, 320, 24, 0, 200, 255)       # Light blue bar
    kb.text(100, 208, "full-width bar", size="S", color=WHITE)


def stage4_fullscreen(kb):
    """Full-screen 5-stripe pattern (from pattern_test)."""
    import numpy as np
    from vckb.framebuf import DISPLAY_W, DISPLAY_H

    _label(kb, "Stage 4/4: Full-Screen Stripes", "320x240 R|G|B|W|BLK")

    rgb = np.zeros((DISPLAY_H, DISPLAY_W, 3), dtype=np.uint8)
    stripe_w = DISPLAY_W // 5
    colors = [
        (255, 0, 0),     # R
        (0, 255, 0),     # G
        (0, 0, 255),     # B
        (255, 255, 255), # W
        (0, 0, 0),       # BLK
    ]
    for i, (rv, gv, bv) in enumerate(colors):
        x0 = i * stripe_w
        rgb[:, x0 : x0 + stripe_w, 0] = rv
        rgb[:, x0 : x0 + stripe_w, 1] = gv
        rgb[:, x0 : x0 + stripe_w, 2] = bv

    # White bar at bottom for visibility
    rgb[DISPLAY_H - 20 : DISPLAY_H, :, :] = 255

    r = rgb[:, :, 0].astype("<u2")
    g = rgb[:, :, 1].astype("<u2")
    b = rgb[:, :, 2].astype("<u2")
    rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

    row_bytes = DISPLAY_W * 2
    for start_row in range(0, DISPLAY_H, 102):
        end_row = min(start_row + 102, DISPLAY_H)
        h = end_row - start_row
        kb.push_frame(0, start_row, DISPLAY_W, h,
                      rgb565.astype("<u2").tobytes()[
                          start_row * row_bytes : end_row * row_bytes
                      ])


def main():
    from vckb import VCKeyboard, BLACK, WHITE

    stop_signal = os.environ.get("VCKB_STOP_SIGNAL", "")

    stages = [
        ("Gradient", stage1_gradient),
        ("Compare", stage2_compare),
        ("Solids", stage3_solids),
        ("Full Screen", stage4_fullscreen),
    ]

    with VCKeyboard() as kb:
        kb.fill(BLACK)
        stage_idx = 0
        skip = False

        def next_stage():
            nonlocal stage_idx, skip
            skip = True

        @kb.on_key("KEY5", "down")
        def on_key5():
            nonlocal stage_idx
            if stage_idx >= len(stages):
                nonlocal running
                running = False
            else:
                next_stage()

        while stage_idx < len(stages):
            name, fn = stages[stage_idx]
            skip = False

            # Clear and run stage
            kb.fill(BLACK)
            fn(kb)

            # Show progress
            kb.text(280, 230, f"{stage_idx + 1}/{len(stages)}", size="S", color=0x8410)

            # Wait for auto-advance or skip
            deadline = time.time() + STAGE_WAIT
            while time.time() < deadline and not skip:
                kb.poll(timeout=0.1)
                if stop_signal and pathlib.Path(stop_signal).exists():
                    kb.clear()
                    pathlib.Path(stop_signal).unlink(missing_ok=True)
                    return

            stage_idx += 1

        # Done — show summary
        kb.fill(BLACK)
        kb.text(40, 100, "All 4 stages complete!", size="L", color=0x07E0)
        kb.text(60, 150, "Check results above", size="M", color=WHITE)
        kb.text(50, 180, "KEY5 = exit", size="S", color=0x8410)

        running = True
        while running:
            kb.poll(timeout=0.1)
            if stop_signal and pathlib.Path(stop_signal).exists():
                running = False
                break

        kb.clear()
        if stop_signal:
            pathlib.Path(stop_signal).unlink(missing_ok=True)
