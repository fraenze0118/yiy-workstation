"""
画板 Demo: 用编码器控制画笔

  编码器旋转 → 移动光标
  编码器按下 → 切换画笔/橡皮/颜色
  KEY1 → 画点 / 开始画线
  KEY5 → 清屏

用法: python paint.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from vckb import VCKeyboard, BLACK, WHITE, RED, GREEN, BLUE, YELLOW, CYAN

def main():
    with VCKeyboard() as kb:
        kb.fill(BLACK)

        # 画笔状态
        PALETTE = [WHITE, RED, GREEN, BLUE, YELLOW, CYAN, 0xF81F, 0x07FF]
        colors  = ["WHITE","RED","GREEN","BLUE","YELLOW","CYAN","MAGENTA","CYAN2"]
        color_i = 0
        cx, cy  = 160, 120
        drawing = False

        def draw_ui():
            kb.rect(0, 0, 320, 14, 0x2104)
            kb.text(3, 2, f"Color:{colors[color_i]} Cursor:{cx},{cy}",
                    size='S', color=WHITE)

        def draw_cursor():
            # 十字准星
            kb.hline(cx-5, cy, 11, WHITE)
            kb.vline(cx, cy-5, 11, WHITE)

        draw_ui()
        draw_cursor()

        @kb.on_encoder(divider=2)
        def on_enc(direction, steps):
            nonlocal cx, cy, color_i
            if direction == 'cw':
                cx = min(319, cx + 2)
            elif direction == 'ccw':
                cx = max(0, cx - 2)
            elif direction == 'btn':
                color_i = (color_i + 1) % len(PALETTE)

            # 擦旧光标
            kb.vline(cx-8, cy-5, 1, BLACK)
            kb.rect(0, 0, 320, 14, 0x2104)
            draw_ui()
            draw_cursor()

        @kb.on_key('KEY5', 'down')
        def clear_screen():
            kb.fill(BLACK)
            draw_ui()
            draw_cursor()

        # 主循环: 用 KEY1 画点
        print("Move cursor with encoder, press KEY1 to paint")
        while True:
            kb.poll(timeout=0.05)

if __name__ == '__main__':
    main()
