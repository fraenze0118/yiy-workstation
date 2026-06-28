"""
VC-Keyboard Python SDK
"""

import serial, serial.tools.list_ports, struct, time
from typing import Optional

BLACK=0x0000; WHITE=0xFFFF; RED=0xF800; GREEN=0x07E0; BLUE=0x001F
YELLOW=0xFFE0; CYAN=0x07FF; MAGENTA=0xF81F; ORANGE=0xFD20; GRAY=0x8410

# 单块位图数据上限 (字节). 固件 USB CDC RX 环形缓冲为 4096, 单块远小于此值
# 可保证即便固件在 drawRGBBitmap(SPI) 期间不读串口, 缓冲也不会溢出丢字节.
# 3072B → 320px 宽时 4 行/块 (留余量给命令头), 比 2048 减少 25% 往返次数.
MAX_CHUNK_BYTES = 3072

# 字节取反查找表 (ST7789 INVON 颜色取反补偿). bytes.translate 走 C 实现,
# 比 `bytes(~b & 0xFF for b in data)` 快约 40x (全屏 153KB: ~40ms → ~1ms).
_COMPLEMENT_TABLE = bytes(b ^ 0xFF for b in range(256))

def rgb565(r,g,b):
    return ((r&0xF8)<<8)|((g&0xFC)<<3)|(b>>3)

class VCKeyboard:
    def __init__(self, port:Optional[str]=None):
        self._ser = None; self._port = port
        self._cb = {'key':{}, 'encoder':[], 'switch':[], 'audio':[], 'ready':[]}
        self._line_buf = bytearray()
        self._raw = bytearray()

    # ── connect ──
    @staticmethod
    def _find_port():
        for p in serial.tools.list_ports.comports():
            if p.vid == 0x303A: return p.device
        raise RuntimeError("ESP32 not found")
    def connect(self):
        if self._port is None: self._port = self._find_port()
        self._ser = serial.Serial(self._port, 115200, timeout=1.0)
        self._ser.set_buffer_size(rx_size=65536, tx_size=65536)
        time.sleep(0.8)
        self._ser.reset_input_buffer()
        self._send(b"*IDN?\n")
        t0=time.time()
        while time.time()-t0<3:
            line=self._ser.readline()
            if b'VCK:' in line: break
        else: raise TimeoutError("No response")
        for cb in self._cb['ready']: cb()
    def close(self):
        if self._ser and self._ser.is_open: self._ser.close()
    def __enter__(self): self.connect(); return self
    def __exit__(self,*a): self.close()

    # ── send ──
    def _send(self, data:bytes): self._ser.write(data)
    def _cmd(self, s:str): self._send((s+'\n').encode())

    # ── display ──
    def fill(self,c):            self._cmd(f"F,{c:04X}")
    def rect(self,x,y,w,h,c):    self._cmd(f"R,{x},{y},{w},{h},{c:04X}")
    def hline(self,x,y,w,c):     self._cmd(f"H,{x},{y},{w},{c:04X}")
    def vline(self,x,y,h,c):     self._cmd(f"V,{x},{y},{h},{c:04X}")
    def text(self,x,y,t,size='M',color=WHITE):
        self._cmd(f"T,{x},{y},{size},{color:04X},{t}")
    def clear(self): self.fill(BLACK)
    def push_frame(self,x,y,w,h,rgb565:bytes):
        """推送 RGB565 位图, 按行分块以防 USB CDC RX 缓冲溢出丢字节.

        NOTE: 固件 drawRGBBitmap 路径会对每个字节取反 (~byte),
        因此 Python 侧预先取反一次, 双重取反 = 原始值.
        TODO: 定位固件/显示库层面取反根因后移除此 workaround.

        根因修复: 一次性推送 w*h*2 字节会撑满固件 4096 RX 缓冲, 在固件忙于
        SPI 绘制时丢失字节 → 行错位/字节交换花屏. 这里按 MAX_CHUNK_BYTES 拆成
        多个 B 子块, 每块等固件 OK 应答再发下一块 (逐块流控), 固件超时丢行时回
        B:ERR, 由 _push_chunk 重发该块.
        """
        inverted = rgb565.translate(_COMPLEMENT_TABLE)
        row_bytes = w * 2
        rows_per_chunk = max(1, MAX_CHUNK_BYTES // row_bytes)
        print(f"[PY] push_frame: {w}x{h} @({x},{y}) {len(inverted)}B "
              f"→ chunks of {rows_per_chunk} rows")
        for row_start in range(0, h, rows_per_chunk):
            chunk_h = min(rows_per_chunk, h - row_start)
            off = row_start * row_bytes
            chunk = inverted[off : off + chunk_h * row_bytes]
            self._push_chunk(x, y + row_start, w, chunk_h, chunk)

    def _push_chunk(self, x, y, w, h, data, retries=3):
        """推送单个分块: B,x,y,w,h\\n + 数据, 等固件 OK; 遇 B:ERR 重发.

        成功静默 (避免全屏推送时每块 OK 刷屏), 仅在 B:ERR/超时重试时打印.
        """
        pkt = f"B,{x},{y},{w},{h}\n".encode() + data
        for attempt in range(retries):
            self._send(pkt)
            t0 = time.time()
            got_err = False
            while time.time() - t0 < 5:
                line = self._ser.readline()
                if not line:
                    continue
                decoded = line.decode('ascii', 'ignore').strip()
                if decoded == 'OK':
                    return
                if decoded.startswith('B:ERR'):
                    print(f"[FW] {decoded} (retry {attempt+1}/{retries})")
                    got_err = True
                    break
            if not got_err:
                print(f"[PY] chunk B,{x},{y},{w},{h} timeout "
                      f"(retry {attempt+1}/{retries})")
        raise RuntimeError(
            f"push_chunk failed at B,{x},{y},{w},{h} after {retries} retries")

    # ── callbacks ──
    def on_key(self,key,action='down'):
        def d(fn): self._cb['key'][(key,action)]=fn; return fn
        return d
    def on_encoder(self, divider=4):
        """注册编码器回调, divider=累积步数阈值 (默认 4)"""
        def d(fn):
            self._cb['encoder'].append([fn, divider, 0])  # [fn, div, acc]
            return fn
        return d
    def on_switch(self):
        def d(fn): self._cb['switch'].append(fn); return fn
        return d
    def on_audio(self):
        def d(fn): self._cb['audio'].append(fn); return fn
        return d
    def on_ready(self):
        def d(fn): self._cb['ready'].append(fn); return fn
        return d

    # ── mic ──
    def mic_start(self): self._cmd("MIC:ON"); time.sleep(0.3)
    def mic_stop(self):  self._cmd("MIC:OFF")

    # ── system ──
    def ping(self): self._cmd("PING")
    def reset(self): self._cmd("*RST")

    # ── poll ──
    def poll(self, timeout=None):
        if not self._ser or not self._ser.is_open: return False
        try:
            self._ser.timeout = 0.1
            raw = self._ser.read(4096)
            if raw:
                self._raw.extend(raw)
                self._parse()
                return True
            return False
        except serial.SerialException:
            return False

    def _parse(self):
        raw = self._raw; pos = 0; n = len(raw)
        while pos < n:
            if raw[pos]==0xCC and pos+3<n and raw[pos+1]==0xDD:
                dlen = struct.unpack_from('<H',raw,pos+2)[0]
                end = pos+4+dlen
                if end <= n:
                    for cb in self._cb['audio']: cb(raw[pos+4:end])
                    pos = end; continue
                else:
                    break  # 不完整的音频包, 等下次 read
            self._line_buf.append(raw[pos])
            if raw[pos]==0x0A:
                line = bytes(self._line_buf).decode('ascii','ignore').strip()
                self._line_buf.clear()
                if line: self._dispatch(line)
                # 打印固件位图错误 (B:ERR), 其余调试标签已随 \xAA\xBB 路径移除
                if line.startswith('B:'):
                    print(f"[FW] {line}")
            elif len(self._line_buf) > 1024:
                self._line_buf.clear()  # 垃圾数据, 丢弃
            pos += 1
        self._raw = self._raw[pos:]

    def _dispatch(self, line:str):
        if line.startswith('K:'):
            p=line.split(':')
            if len(p)==3:
                a='down' if p[1]=='D' else 'up'
                fn=self._cb['key'].get((p[2],a))
                if fn: fn()
        elif line.startswith('E:'):
            p=line.split(':')
            if p[1]=='BTN':
                for entry in self._cb['encoder']:
                    entry[0]('btn', 1)
            elif len(p)==3:
                step = int(p[2]) * (1 if p[1]=='CW' else -1)
                for entry in self._cb['encoder']:
                    fn, div, acc = entry
                    acc += step
                    # 达到阈值触发, 每次触发回调 steps=1
                    while acc >= div:
                        fn('cw', 1); acc -= div
                    while acc <= -div:
                        fn('ccw', 1); acc += div
                    entry[2] = acc
        elif line.startswith('SW:'):
            for fn in self._cb['switch']: fn(line.split(':')[1])

    def run(self):
        try:
            while True: self.poll()
        except KeyboardInterrupt: pass
