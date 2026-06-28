"""
番茄钟 Demo
  KEY1 = 开始/暂停
  KEY5 = 重置
  编码器旋转 = 调时长
  拨动开关 = 暂停/恢复
"""

import sys, os, time as _time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from vckb import VCKeyboard, BLACK, WHITE, RED, GREEN, YELLOW, GRAY

def draw(kb, remain, total, running, focus_mins):
    """全屏重绘"""
    kb.fill(BLACK)

    # 标题栏
    kb.rect(0, 0, 320, 16, 0x2104)
    kb.text(4, 2, f"FOCUS: {focus_mins} min", size='S', color=WHITE)
    state = "WORK" if running else "PAUSE"
    sc = GREEN if running else YELLOW
    kb.rect(320-50, 1, 48, 14, sc)
    kb.text(320-46, 2, state, size='S', color=BLACK)

    # 中间大时间
    mins = int(remain // 60)
    secs = int(remain % 60)
    time_str = f"{mins:02d}:{secs:02d}"
    kb.text(95, 80, time_str, size='X', color=WHITE)

    # 进度条
    bar_w = 280
    kb.rect(20, 150, bar_w, 20, 0x4208)  # 背景
    if total > 0:
        p = int(bar_w * (1 - remain / total))
        kb.rect(20, 150, p, 20, GREEN if running else YELLOW)

    # 底部提示
    kb.text(8, 220, "K1:start  K5:reset  ENC:time  SW:pause", size='S', color=0x8410)

def main():
    with VCKeyboard() as kb:
        focus_mins = 25
        total = focus_mins * 60
        remain = total
        running = False
        last_tick = _time.time()
        last_draw = 0

        draw(kb, remain, total, running, focus_mins)

        def do_tick():
            nonlocal remain, running
            if running and remain > 0:
                remain -= 1
                if remain == 0:
                    running = False
                    for _ in range(3):
                        kb.fill(RED); _time.sleep(0.15)
                        kb.fill(BLACK); _time.sleep(0.15)

        @kb.on_key('KEY1', 'down')
        def k1():
            nonlocal running, remain, total
            if remain == 0: remain = total
            running = not running

        @kb.on_key('KEY5', 'down')
        def k5():
            nonlocal running, remain, total
            running = False; remain = total

        @kb.on_encoder(divider=4)
        def enc(direction, steps):
            nonlocal focus_mins, total, remain, running
            if not running:
                focus_mins = max(1, min(60, focus_mins + (1 if direction=='cw' else -1)))
                total = focus_mins * 60; remain = total

        @kb.on_switch()
        def sw(state):
            nonlocal running
            if remain > 0: running = (state == 'ON')

        print("Tomato Clock: K1=start K5=reset ENC=time SW=pause")
        while True:
            kb.poll()
            now = _time.time()
            if running and now - last_tick >= 1.0:
                last_tick = now; do_tick()
            if now - last_draw >= 1.0:
                last_draw = now; draw(kb, remain, total, running, focus_mins)

if __name__ == '__main__':
    main()
