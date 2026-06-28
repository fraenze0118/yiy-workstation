"""测试 push_frame 是否正常工作"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from vckb import VCKeyboard, BLACK, RED, GREEN, BLUE, WHITE

with VCKeyboard() as kb:
    kb.clear()
    kb.text(10, 10, "Frame test...", size='M', color=WHITE)

    # 画一个 100x80 的红绿蓝渐变矩形
    w, h = 100, 80
    data = bytearray(w * h * 2)
    for row in range(h):
        for col in range(w):
            # RGB565: 红色渐变从左到右, 绿色从上到下
            r = (col * 255 // w) & 0xF8
            g = (row * 255 // h) & 0xFC
            b = 0
            color = (r << 8) | (g << 3) | (b >> 3)
            off = (row * w + col) * 2
            data[off] = color & 0xFF
            data[off+1] = (color >> 8) & 0xFF

    print("Pushing small frame (100x80)...")
    kb.push_frame(10, 30, w, h, bytes(data))
    print("Done. Check screen.")
    time.sleep(5)
    kb.clear()
