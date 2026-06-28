"""
番茄钟 — Pomodoro Timer

按键:
  KEY1 = 开始/暂停
  KEY5 = 重置
  编码器 = 调整时长 (1-60 min)
"""

import time, os, pathlib

from vckb.apps.base import AppDefinition

APP = AppDefinition(
    id="tomato",
    name="Tomato",
    name_zh="番茄钟",
    description="Pomodoro timer — 25min focus sessions",
    icon="🍅",
    category="tool",
    controls={
        "KEY1": "开始/暂停",
        "KEY5": "重置",
        "编码器": "调整时长",
    },
    module="vckb.apps.tomato",
    requires=[],
)


def main():
    from vckb import VCKeyboard, BLACK, WHITE, RED, GREEN

    stop_signal = os.environ.get("VCKB_STOP_SIGNAL", "")

    with VCKeyboard() as kb:
        kb.fill(BLACK)

        minutes = 25
        remaining = minutes * 60
        running = False
        last_tick = 0

        def draw():
            kb.fill(BLACK)
            m = remaining // 60
            s = remaining % 60
            kb.text(80, 80, f"{m:02d}:{s:02d}", size='X', color=GREEN if running else WHITE)

            # 进度条
            total = minutes * 60
            if total > 0:
                bar_w = int(200 * (total - remaining) / total)
                kb.rect(60, 160, 200, 20, 0x4208)       # 背景
                kb.rect(60, 160, bar_w, 20, GREEN)       # 进度

            kb.text(60, 200, f"{minutes} min", size='M', color=WHITE)
            kb.text(200, 200, "KEY5=Reset", size='S', color=0x8410)

            state_text = "RUNNING" if running else ("PAUSED" if remaining < minutes * 60 else "READY")
            kb.text(10, 10, state_text, size='S', color=GREEN if running else WHITE)

        draw()

        @kb.on_key('KEY1', 'down')
        def toggle():
            nonlocal running, last_tick
            running = not running
            if running:
                last_tick = time.time()
            draw()

        @kb.on_key('KEY5', 'down')
        def reset():
            nonlocal running, remaining
            running = False
            remaining = minutes * 60
            draw()

        @kb.on_encoder(divider=2)
        def on_enc(direction, steps):
            nonlocal minutes, remaining, running
            if not running:
                if direction == 'cw':
                    minutes = min(60, minutes + 1)
                elif direction == 'ccw':
                    minutes = max(1, minutes - 1)
                remaining = minutes * 60
                draw()

        while True:
            kb.poll(timeout=0.1)

            # 停止信号检查
            if stop_signal and pathlib.Path(stop_signal).exists():
                kb.clear()
                pathlib.Path(stop_signal).unlink(missing_ok=True)
                break

            if running:
                now = time.time()
                if now - last_tick >= 1.0:
                    remaining -= 1
                    last_tick = now
                    if remaining <= 0:
                        running = False
                        remaining = 0
                    draw()
