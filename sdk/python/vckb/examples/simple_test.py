"""极简测试: 发送命令 + 读音频"""
import serial, struct, time

ser = serial.Serial('COM9', 115200, timeout=1.0)
time.sleep(0.8)

# 握手
ser.write(b"*IDN?\n")
print("IDN:", ser.readline().decode().strip())

# 发送一些显示命令 (模拟 self_test 行为)
ser.write(b"F,0000\n")
ser.write(b"R,10,50,100,60,F800\n")
ser.write(b"T,10,10,M,FFFF,Hello World\n")
time.sleep(0.3)  # 等固件处理

# 开启麦克风
ser.write(b"MIC:ON\n")
time.sleep(0.5)

# 读数据
ser.timeout = 0.1
audio_count = 0
peak = 0
t0 = time.time()
while time.time() - t0 < 3:
    raw = ser.read(4096)
    if not raw:
        continue
    # 找 MIC 响应
    if b'MIC:' in raw:
        for line in raw.split(b'\n'):
            if b'MIC:' in line:
                print("GOT:", line.decode().strip())
    # 找音频包
    pos = 0
    while pos < len(raw):
        if raw[pos] == 0xCC and pos+1 < len(raw) and raw[pos+1] == 0xDD and pos+4 < len(raw):
            dlen = struct.unpack_from('<H', raw, pos+2)[0]
            if pos+4+dlen <= len(raw):
                audio_count += 1
                pcm = raw[pos+4:pos+4+dlen]
                for i in range(0, len(pcm), 2):
                    s = abs(struct.unpack_from('<h', pcm, i)[0])
                    if s > peak: peak = s
                pos += 4 + dlen
                continue
        pos += 1

print(f"\nAudio packets: {audio_count}, peak: {peak}")
ser.close()
