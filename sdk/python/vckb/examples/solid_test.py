"""
单色矩形测试 — 排除图案复杂度, 只测尺寸/位置是否正确
"""

import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
from vckb import VCKeyboard, BLACK, WHITE, RED, GREEN, BLUE

MAX_ROWS = 102


def push_solid(kb, x, y, w, h, rgb888_tuple):
    """推送纯色矩形"""
    rv, gv, bv = rgb888_tuple

    # 手动构建 RGB565 (不用 numpy, 与 frame_test 完全一致)
    color = ((rv & 0xF8) << 8) | ((gv & 0xFC) << 3) | (bv >> 3)
    row_bytes = w * 2
    line = bytearray(row_bytes)
    for i in range(0, row_bytes, 2):
        line[i] = color & 0xFF
        line[i + 1] = (color >> 8) & 0xFF

    data = line * h  # 每行相同
    kb.push_frame(x, y, w, h, bytes(data))


def push_solid_np(kb, x, y, w, h, rgb888_tuple):
    """推送纯色矩形 (numpy 版本)"""
    rv, gv, bv = rgb888_tuple
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    rgb[:, :, 0] = rv
    rgb[:, :, 1] = gv
    rgb[:, :, 2] = bv
    r = rgb[:, :, 0].astype('<u2')
    g = rgb[:, :, 1].astype('<u2')
    b = rgb[:, :, 2].astype('<u2')
    rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    kb.push_frame(x, y, w, h, rgb565.astype('<u2').tobytes())


def main():
    with VCKeyboard() as kb:
        kb.clear()

        # 测试 1: 小矩形 (手动, 与 frame_test 完全一致)
        print("Test 1: manual 100x80 RED at (0,10)")
        push_solid(kb, 0, 10, 100, 80, (255, 0, 0))
        kb.text(105, 40, "manual", size='S', color=WHITE)
        time.sleep(2)

        # 测试 2: 小矩形 (numpy)
        print("Test 2: numpy 100x80 GREEN at (110,10)")
        push_solid_np(kb, 110, 10, 100, 80, (0, 255, 0))
        kb.text(215, 40, "numpy", size='S', color=WHITE)
        time.sleep(2)

        # 测试 3: 小矩形 (手动) 在下方
        print("Test 3: manual 100x80 BLUE at (0,100)")
        push_solid(kb, 0, 100, 100, 80, (0, 0, 255))
        time.sleep(2)

        # 测试 4: 小矩形 (numpy) 在下方
        print("Test 4: numpy 100x80 WHITE at (110,100)")
        push_solid_np(kb, 110, 100, 100, 80, (255, 255, 255))
        time.sleep(2)

        # 测试 5: 全宽单色条 (手动) 320x40 at bottom
        print("Test 5: manual 320x40 YELLOW at (0,180)")
        push_solid(kb, 0, 180, 320, 40, (255, 255, 0))
        time.sleep(2)

        print("\nSummary:")
        print("  Test 1: RED 100x80 manual  → should be solid red, 100w x 80h")
        print("  Test 2: GREEN 100x80 numpy → should be solid green, same size")
        print("  Test 3: BLUE 100x80 manual  → should be solid blue, same size")
        print("  Test 4: WHITE 100x80 numpy  → should be solid white, same size")
        print("  Test 5: YELLOW 320x40 manual → should be full-width yellow bar")

        kb.text(10, 220, "Check sizes/colors. KEY5=exit", size='S', color=WHITE)

        running = True

        @kb.on_key('KEY5', 'down')
        def quit_app():
            nonlocal running
            running = False

        while running:
            kb.poll()
            time.sleep(0.1)

        kb.clear()


if __name__ == '__main__':
    main()
