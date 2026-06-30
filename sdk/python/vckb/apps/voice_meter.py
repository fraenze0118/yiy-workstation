"""
语音电平表 + 频谱可视化

  实时显示麦克风音频的频谱柱状图 + 波形图 + 峰值电平。

  ST7789 INVON 硬件取反所有颜色, 两条渲染路径补偿方式不同:
    - 位图路径 (push_frame): device.py 已对每字节取反, 双重取反=原始色
      → 频谱/波形帧缓冲用 *原始色* 即可正确显示.
    - 文本/矩形命令路径 (kb.text/kb.rect): 固件 *不* 补偿 INVON
      → 顶栏颜色需发送 ~c (inv()), INVON 取反后显示 c.

  渲染架构: 数据采集 (on_audio, 高频轻量) 与渲染 (主循环节流, ~5 FPS) 分离.
  频谱/波形用 numpy 帧缓冲 + push_frame 整块推送 (带逐块 OK 流控, 不丢字节,
  不残留重叠). 这取代了旧版每帧 ~390 条无流控文本命令 (固件 4KB RX 缓冲溢出
  丢命令 → 文字/柱状图重叠、波形残缺) 的实现.

  依赖: numpy (FFT)
  操作: KEY5 = 退出
"""

import os, pathlib, struct, time
from collections import deque

from vckb.apps.base import AppDefinition

APP = AppDefinition(
    id="voice_meter",
    name="Voice Meter",
    name_zh="语音电平表",
    description="Real-time audio spectrum & waveform visualization",
    icon="🎤",
    category="tool",
    controls={"KEY5": "退出"},
    module="vckb.apps.voice_meter",
    requires=["numpy"],
)

# ── 布局 ──
TOP_H = 18
SPEC_H = 180
WAVE_H = 36
N_BARS = 64
BAR_W = 5
FFT_SIZE = 1024

DISPLAY_W = 320
SPEC_Y0 = TOP_H                  # 18
SPEC_Y1 = SPEC_Y0 + SPEC_H       # 198
WAVE_Y0 = SPEC_Y1 + 2            # 200
WAVE_MID = WAVE_Y0 + WAVE_H // 2  # 218

RENDER_INTERVAL = 0.18   # ~5 FPS, 匹配 USB Full Speed 带宽上限
WAVE_GAIN = 6.0          # PDM 信号偏弱, 固定增益 + 限幅 (配合去 DC)


def main():
    import numpy as np
    from vckb import VCKeyboard

    stop_signal = os.environ.get("VCKB_STOP_SIGNAL", "")

    def inv(c):
        """固件文本/矩形命令不补偿 INVON: 发送 ~c → INVON 取反 → 显示 c"""
        return (~c) & 0xFFFF

    with VCKeyboard() as kb:
        kb.fill(inv(0x0000))   # 黑底 (发送 0xFFFF, INVON→0x0000)

        # ── 缓冲区 ──
        fft_buf = deque(maxlen=FFT_SIZE)
        wave_buf = deque(maxlen=DISPLAY_W)
        bar_heights = np.zeros(N_BARS, dtype=np.float32)

        # ── 状态 ──
        peak_db = -60.0
        speaking = False
        fft_ready = False
        last_render = 0.0
        prev_top_peak = None       # 顶栏仅在整数 dB 变化时重绘
        prev_top_speaking = None

        # ── FFT 预计算 ──
        hann = np.hanning(FFT_SIZE)
        freqs = np.fft.rfftfreq(FFT_SIZE, 1 / 44100)
        lo_idx = np.searchsorted(freqs, 50)
        hi_idx = np.searchsorted(freqs, 20000)
        log_freqs = np.logspace(np.log10(50), np.log10(20000), N_BARS + 1)
        band_map = []
        for i in range(N_BARS):
            b0 = np.searchsorted(freqs, log_freqs[i])
            b1 = np.searchsorted(freqs, log_freqs[i + 1])
            b0 = max(b0, lo_idx)
            b1 = min(b1, hi_idx)
            band_map.append((b0, max(b0 + 1, b1)))

        # ── 彩虹色 (原始 RGB565; 走 push_frame 时 INVON 自动补偿, 显示正确色) ──
        def _hsv565(h_deg):
            """h_deg 0..360, S=1 V=1 → RGB565 (原始色)"""
            h = h_deg / 60
            s = int(h) % 6
            f = h - int(h)
            p, q, t = 0, 1 - f, f
            r, g, b = [(1, t, p), (q, 1, p), (p, 1, t),
                       (p, q, 1), (t, p, 1), (1, p, q)][s]
            r = int(r * 255); g = int(g * 255); b = int(b * 255)
            return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

        # 64 bar 彩虹色: 低频红→中频黄绿→高频蓝紫 (色相 0°→270°)
        RAINBOW = [_hsv565(i / (N_BARS - 1) * 270) for i in range(N_BARS)]

        # ── 顶栏 (文本命令路径, 颜色用 inv() 取反发送) ──
        def draw_top_bar():
            kb.rect(0, 0, DISPLAY_W, TOP_H, inv(0x2104))             # 深蓝条
            kb.text(3, 3, "Voice Meter", size="S", color=inv(0xFFFF))  # 白字
            if peak_db > -60:
                kb.text(110, 3, f"PEAK:{peak_db:+.0f}dB", size="S",
                        color=inv(0xF800) if speaking else inv(0x7BEF))
            else:
                kb.text(110, 3, "PEAK: ---", size="S", color=inv(0x7BEF))
            kb.rect(232, 4, 10, 10,
                    inv(0xF800) if speaking else inv(0x18E3))
            kb.text(246, 3, "SPK" if speaking else "---", size="S",
                    color=inv(0xF800) if speaking else inv(0x7BEF))

        # ── 频谱区: numpy 帧缓冲 → push_frame ──
        def render_spectrum():
            spec = np.zeros((SPEC_H, DISPLAY_W), dtype='<u2')
            for i in range(N_BARS):
                h = int(bar_heights[i])
                if h < 2:
                    continue
                color = RAINBOW[i]  # 彩虹色: 低频红→中频黄绿→高频蓝紫
                x0 = i * BAR_W
                spec[SPEC_H - h:SPEC_H, x0:x0 + BAR_W] = color
            spec[SPEC_H - 1, :] = 0x18E3   # 基准线
            kb.push_frame(0, SPEC_Y0, DISPLAY_W, SPEC_H, spec.tobytes())

        # ── 波形区: numpy 帧缓冲 → push_frame (去 DC + 增益) ──
        def render_waveform():
            wave = np.zeros((WAVE_H, DISPLAY_W), dtype='<u2')
            mid = WAVE_H // 2
            wave[mid, :] = 0x18E3          # 基线
            if len(wave_buf) < 2:
                kb.push_frame(0, WAVE_Y0, DISPLAY_W, WAVE_H, wave.tobytes())
                return

            samples = np.array(list(wave_buf), dtype=np.float32)
            samples -= samples.mean()                       # 去 DC, 波形居中
            v_norm = np.clip(samples * WAVE_GAIN / 32768.0, -1.0, 1.0)
            half = mid - 2
            y = (mid - v_norm * half).astype(np.int32)
            y = np.clip(y, 1, WAVE_H - 2)

            color = 0xF800   # 原始红, push_frame+INVON 显示红
            n = len(y)
            for x in range(n):
                yx = int(y[x])
                if yx < mid:
                    wave[yx:mid + 1, x] = color
                else:
                    wave[mid:yx + 1, x] = color
            kb.push_frame(0, WAVE_Y0, DISPLAY_W, WAVE_H, wave.tobytes())

        # ── FFT + 平滑 (更新 bar_heights) ──
        def compute_spectrum():
            nonlocal fft_ready
            if not fft_ready or len(fft_buf) < FFT_SIZE:
                return
            fft_ready = False
            fft_data = np.array(list(fft_buf)[-FFT_SIZE:], dtype=np.float32)
            windowed = fft_data * hann
            spectrum = np.abs(np.fft.rfft(windowed)) / FFT_SIZE
            for i, (b0, b1) in enumerate(band_map):
                mag = np.max(spectrum[b0:b1]) if b1 > b0 else 0.0
                if mag > 1e-6:
                    db = 20 * np.log10(mag)
                    new_h = max(0, min(SPEC_H, (db + 40) / 40 * SPEC_H))
                else:
                    new_h = 0
                bar_heights[i] = bar_heights[i] * 0.55 + new_h * 0.45

        # ── 音频回调: 只攒数据, 不渲染 (保持 poll 轻量) ──
        @kb.on_audio()
        def on_audio(pcm):
            nonlocal peak_db, speaking, fft_ready
            n_samples = len(pcm) // 2
            if n_samples == 0:
                return
            arr = np.array(struct.unpack(f"<{n_samples}h", pcm), dtype=np.float32)

            rms = float(np.sqrt(np.mean(arr ** 2)))
            db = 20 * np.log10(rms / 32768.0) if rms > 0 else -60.0

            if db > peak_db:
                peak_db = db
            else:
                peak_db = max(-60.0, peak_db - 0.5)
            speaking = db > -30

            fft_buf.extend(arr)
            wave_buf.extend(arr)
            if len(fft_buf) >= FFT_SIZE:
                fft_ready = True

        # ── 初始顶栏 ──
        draw_top_bar()
        prev_top_peak = int(peak_db)
        prev_top_speaking = speaking

        kb.mic_start()

        running = True

        @kb.on_key("KEY5", "down")
        def on_exit():
            nonlocal running
            running = False

        try:
            while running:
                kb.poll(timeout=0.02)

                if stop_signal and pathlib.Path(stop_signal).exists():
                    running = False
                    break

                now = time.time()
                if now - last_render < RENDER_INTERVAL:
                    continue
                last_render = now

                # 渲染前暂停 mic: 固件 B 命令回 OK\n, 但 mic 上行音频包是二进制
                # (含 0x0A / ASCII 字节), 会污染 _push_chunk 的 readline() 应答读取
                # → push_frame 超时. 暂停 + 清缓冲后 push_frame 走干净链路 (同 screen_mirror).
                kb.mic_pause()
                kb.flush_input()
                compute_spectrum()
                render_spectrum()
                render_waveform()

                # 顶栏: 仅在 peak 整数变化或 speaking 翻转时重绘 (低频, 不拥塞)
                cur_peak = int(peak_db)
                if cur_peak != prev_top_peak or speaking != prev_top_speaking:
                    draw_top_bar()
                    prev_top_peak = cur_peak
                    prev_top_speaking = speaking
                kb.mic_resume()
        finally:
            # 崩溃也保证停 mic + 清屏, 避免 mic_streaming 残留污染下次串口通信
            kb.mic_stop()
            kb.fill(inv(0x0000))
            if stop_signal:
                pathlib.Path(stop_signal).unlink(missing_ok=True)
