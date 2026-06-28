"""
最小传输测试 — 单帧 100×80 色块, 与已验证的 frame_test 对比

目的: 确认 push_frame 单帧是否正确, 排除分块/全屏问题
"""

import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
from vckb import VCKeyboard, BLACK, WHITE


def main():
    with VCKeyboard() as kb:
        kb.clear()
        kb.text(10, 5, "Small Pattern Test", size='S', color=WHITE)

        # ── 方式 A: numpy 生成 RGB565 (与 screen_mirror 同路径) ──
        w, h = 100, 80
        rgb = np.zeros((h, w, 3), dtype=np.uint8)

        # 5 条竖色带
        stripe = w // 5
        rgb[:, 0*stripe:1*stripe, 0] = 255  # 红
        rgb[:, 1*stripe:2*stripe, 1] = 255  # 绿
        rgb[:, 2*stripe:3*stripe, 2] = 255  # 蓝
        rgb[:, 3*stripe:4*stripe, :] = 255  # 白
        # 第 5 条保持 0 (黑)

        r = rgb[:, :, 0].astype('<u2')
        g = rgb[:, :, 1].astype('<u2')
        b = rgb[:, :, 2].astype('<u2')
        rgb565_np = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        data_np = rgb565_np.astype('<u2').tobytes()

        # ── 方式 B: 手动循环生成 RGB565 (与 frame_test 同路径) ──
        data_manual = bytearray(w * h * 2)
        for row in range(h):
            for col in range(w):
                if col < stripe:
                    rv, gv, bv = 255, 0, 0       # 红
                elif col < stripe * 2:
                    rv, gv, bv = 0, 255, 0       # 绿
                elif col < stripe * 3:
                    rv, gv, bv = 0, 0, 255       # 蓝
                elif col < stripe * 4:
                    rv, gv, bv = 255, 255, 255   # 白
                else:
                    rv, gv, bv = 0, 0, 0         # 黑

                color = ((rv & 0xF8) << 8) | ((gv & 0xFC) << 3) | (bv >> 3)
                off = (row * w + col) * 2
                data_manual[off] = color & 0xFF
                data_manual[off + 1] = (color >> 8) & 0xFF

        # 对比两种方式
        print(f"numpy bytes:  {len(data_np)}")
        print(f"manual bytes: {len(data_manual)}")
        print(f"identical: {data_np == bytes(data_manual)}")

        # 先推送 numpy 版本
        print("\nPushing NUMPY version (top-left, should see: R|G|B|W|BLK stripes)")
        kb.push_frame(0, 20, w, h, data_np)
        time.sleep(3)

        # 再推送手动版本
        print("Pushing MANUAL version (below numpy, same pattern)")
        kb.push_frame(0, 110, w, h, bytes(data_manual))
        time.sleep(5)

        print("Compare the two: should be identical color bars.")
        print("If numpy version is wrong but manual is correct → numpy byte order issue")
        print("If both are wrong → firmware protocol issue")
        print("If both are correct → the bug is in full-screen chunking")

        kb.clear()


if __name__ == '__main__':
    main()
