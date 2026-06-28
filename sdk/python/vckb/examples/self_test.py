"""
VC-Keyboard 设备自检

验证所有外设:
  - 屏幕: 显示色块 + 文本
  - 按键: 按下/释放回调
  - 编码器: 旋转 + 按下
  - 拨动开关: ON/OFF
  - 麦克风: 音频峰值

用法: python self_test.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from vckb import VCKeyboard, BLACK, WHITE, RED, GREEN, BLUE, YELLOW, CYAN

def main():
    with VCKeyboard() as kb:
        print("VC-Keyboard self-test started")
        print("Press Ctrl+C to exit\n")

        # ── 屏幕测试 ──
        kb.fill(BLACK)
        kb.text(10, 10, "VC-Keyboard Self-Test", size='L', color=WHITE)
        kb.rect(10, 50, 100, 60, RED)
        kb.text(15, 80, "KEY TEST", size='S', color=WHITE)
        kb.rect(120, 50, 100, 60, GREEN)
        kb.text(125, 80, "ENCODER", size='S', color=BLACK)
        kb.rect(230, 50, 80, 60, BLUE)
        kb.text(235, 80, "SW", size='S', color=WHITE)
        kb.rect(10, 120, 300, 2, WHITE)

        # ── 状态显示 ──
        last_key = "none"; last_enc = "0  "; last_sw = "?"

        def redraw_status():
            kb.rect(10, 130, 300, 100, BLACK)
            kb.text(15, 140, f"Key  : {last_key}", size='M', color=WHITE)
            kb.text(15, 170, f"Enc  : {last_enc}", size='M', color=WHITE)
            kb.text(15, 200, f"SW   : {last_sw}", size='M', color=WHITE)
        redraw_status()

        # ── 按键回调 ──
        @kb.on_key('KEY1', 'down')
        def k1d(): nonlocal last_key; last_key = "KEY1 DOWN"; redraw_status()
        @kb.on_key('KEY1', 'up')
        def k1u(): nonlocal last_key; last_key = "KEY1 UP  "; redraw_status()
        @kb.on_key('KEY2', 'down')
        def k2d(): nonlocal last_key; last_key = "KEY2 DOWN"; redraw_status()
        @kb.on_key('KEY2', 'up')
        def k2u(): nonlocal last_key; last_key = "KEY2 UP  "; redraw_status()
        @kb.on_key('KEY3', 'down')
        def k3d(): nonlocal last_key; last_key = "KEY3 DOWN"; redraw_status()
        @kb.on_key('KEY3', 'up')
        def k3u(): nonlocal last_key; last_key = "KEY3 UP  "; redraw_status()
        @kb.on_key('KEY4', 'down')
        def k4d(): nonlocal last_key; last_key = "KEY4 DOWN"; redraw_status()
        @kb.on_key('KEY4', 'up')
        def k4u(): nonlocal last_key; last_key = "KEY4 UP  "; redraw_status()
        @kb.on_key('KEY5', 'down')
        def k5d(): nonlocal last_key; last_key = "KEY5 DOWN"; redraw_status()
        @kb.on_key('KEY5', 'up')
        def k5u(): nonlocal last_key; last_key = "KEY5 UP  "; redraw_status()

        # ── 编码器回调 ──
        enc_pos = 0
        @kb.on_encoder()
        def on_enc(direction, steps):
            nonlocal enc_pos, last_enc
            if direction == 'cw':
                enc_pos += steps
            elif direction == 'ccw':
                enc_pos -= steps
            elif direction == 'btn':
                enc_pos = 0
            last_enc = f"{enc_pos:4d}"
            redraw_status()

        # ── 拨动开关回调 ──
        @kb.on_switch()
        def on_sw(state):
            nonlocal last_sw
            last_sw = state
            redraw_status()

        # ── 麦克风峰值测试 ──
        kb.mic_start()
        mic_peak = 0

        @kb.on_audio()
        def on_audio(pcm):
            nonlocal mic_peak
            import struct
            for i in range(0, len(pcm), 2):
                s = abs(struct.unpack_from('<h', pcm, i)[0])
                if s > mic_peak: mic_peak = s

        # 定期更新 MIC 峰值
        import time as _time
        last_mic_update = _time.time()
        def update_mic():
            nonlocal mic_peak, last_mic_update
            now = _time.time()
            if now - last_mic_update > 0.3:
                kb.rect(120, 50, 180, 60, GREEN)
                kb.text(125, 65, f"MIC peak", size='S', color=BLACK)
                kb.text(125, 85, f"{mic_peak:5d}", size='M', color=BLACK)
                mic_peak = 0
                last_mic_update = now

        # ── 主循环 ──
        print("Press buttons, turn encoder, toggle switch, speak...")
        while True:
            kb.poll(timeout=0.05)
            update_mic()

if __name__ == '__main__':
    main()
