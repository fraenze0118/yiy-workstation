"""
测试图案传输 — 纯 numpy 生成 RGB565, 排除截屏环节干扰

图案: 全屏色块 (红→绿→蓝→白→黑), 颜色正确与否一目了然
"""

import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
from vckb import VCKeyboard, BLACK, WHITE
from vckb.framebuf import DISPLAY_W, DISPLAY_H

MAX_ROWS_PER_PUSH = 102  # uint16 payload 限制


def make_test_pattern():
    """生成 320×240 RGB565 测试图案: 5 条竖色带 + 文字标注区域"""
    rgb = np.zeros((DISPLAY_H, DISPLAY_W, 3), dtype=np.uint8)

    # 5 条竖色带, 各占 64 像素宽
    stripe_w = DISPLAY_W // 5  # 64
    colors_rgb = [
        (255,   0,   0),   # 红
        (  0, 255,   0),   # 绿
        (  0,   0, 255),   # 蓝
        (255, 255, 255),   # 白
        (  0,   0,   0),   # 黑
    ]

    for i, (r_val, g_val, b_val) in enumerate(colors_rgb):
        x0 = i * stripe_w
        x1 = x0 + stripe_w
        rgb[:, x0:x1, 0] = r_val
        rgb[:, x0:x1, 1] = g_val
        rgb[:, x0:x1, 2] = b_val

    # 底部白色横条便于观察
    rgb[DISPLAY_H - 20:DISPLAY_H, :, :] = 255

    return rgb


def rgb888_to_rgb565_bytes(rgb):
    """(H, W, 3) uint8 RGB → RGB565 bytes (little-endian)"""
    r = rgb[:, :, 0].astype('<u2')
    g = rgb[:, :, 1].astype('<u2')
    b = rgb[:, :, 2].astype('<u2')
    rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    return rgb565.astype('<u2').tobytes()


def push_full_frame(kb, rgb565_data):
    """分块推送全屏 (320×240)"""
    row_bytes = DISPLAY_W * 2
    for start_row in range(0, DISPLAY_H, MAX_ROWS_PER_PUSH):
        end_row = min(start_row + MAX_ROWS_PER_PUSH, DISPLAY_H)
        h = end_row - start_row
        data = rgb565_data[start_row * row_bytes : end_row * row_bytes]
        kb.push_frame(0, start_row, DISPLAY_W, h, data)
        print(f"  chunk: rows {start_row}-{end_row-1} ({h} rows, {len(data)} bytes)")


def main():
    with VCKeyboard() as kb:
        kb.clear()
        kb.text(10, 5, "Pattern Test", size='S', color=WHITE)

        # 生成测试图案
        print("Generating test pattern...")
        rgb = make_test_pattern()
        rgb565_data = rgb888_to_rgb565_bytes(rgb)
        print(f"RGB565 data: {len(rgb565_data)} bytes (expected {DISPLAY_W*DISPLAY_H*2})")

        # 全屏推送
        print("Pushing full screen...")
        t0 = time.time()
        push_full_frame(kb, rgb565_data)
        elapsed = time.time() - t0
        print(f"Done. {elapsed*1000:.0f}ms")

        print("\nExpected display: 5 vertical stripes")
        print("  RED | GREEN | BLUE | WHITE | BLACK")
        print("  (with white bar at bottom)")
        print("\nPress Ctrl+C to exit.")
        while True:
            kb.poll()
            time.sleep(0.1)


if __name__ == '__main__':
    main()
