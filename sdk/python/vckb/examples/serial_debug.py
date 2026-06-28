"""串口调试: 连接设备, 看能收到什么数据"""
import serial, time, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# 手动打开串口
ser = serial.Serial('COM9', 115200, timeout=1.0)
time.sleep(0.5)

# 握手
ser.write(b"*IDN?\n")
t0 = time.time()
while time.time() - t0 < 3:
    line = ser.readline()
    if line:
        print(f"  <- {repr(line)}")
        if b'VCK:' in line:
            break

print("\nSending MIC:ON ...")
ser.write(b"MIC:ON\n")

# 读 3 秒
print("Reading for 3 seconds...\n")
ser.timeout = 0.1
t0 = time.time()
total_bytes = 0
while time.time() - t0 < 3:
    raw = ser.read(4096)
    if raw:
        total_bytes += len(raw)
        # 检查开头几个字节
        preview = ' '.join(f'{b:02X}' for b in raw[:20])
        print(f"  +{len(raw)} bytes: {preview} ...")
        # 检查文本行
        lines = raw.split(b'\n')
        for l in lines:
            if l and all(32 <= c < 127 or c == 10 for c in l):
                print(f"    TEXT: {l.decode('ascii', errors='ignore')}")

print(f"\nTotal bytes read: {total_bytes}")
ser.close()
