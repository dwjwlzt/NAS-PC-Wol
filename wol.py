import paho.mqtt.client as mqtt
import socket
import subprocess
from config import *

def wake_on_lan(mac):
    mac_clean = mac.replace(":", "").replace("-", "")
    try:
        mac_bytes = bytes.fromhex(mac_clean)
    except ValueError:
        print(f"❌ MAC 地址格式无效: {mac}")
        return
    magic_packet = b'\xff' * 6 + mac_bytes * 16
    print(f"📤 发送魔术包 -> MAC:{mac} 广播:{BROADCAST_IP}:9")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(magic_packet, (BROADCAST_IP, 9))
    except Exception as e:
        print(f"❌ 发送魔术包失败: {e}")

def remote_shutdown():
    print(f"📤 远程关机 -> {PC_IP}")
    try:
        result = subprocess.run([
            "net", "rpc", "shutdown",
            "-I", PC_IP,
            "-U", f"{PC_USER}%{PC_PASS}",
            "-f",
        ], capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            print("✅ 远程关机命令发送成功")
        else:
            print(f"❌ 远程关机失败: {result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        print("❌ 远程关机超时，电脑可能不在线")
    except FileNotFoundError:
        print("❌ net 命令未找到，请确认 samba 已安装")
    except Exception as e:
        print(f"❌ 远程关机失败: {e}")

def on_connect(client, userdata, connect_flags, reason_code, properties):
    if reason_code == 0:
        print(f"✅ MQTT连接成功，订阅主题: {TOPIC}")
        client.subscribe(TOPIC)
    else:
        print(f"❌ MQTT连接失败, reason_code={reason_code}")

def on_message(client, userdata, message):
    payload = message.payload.decode('utf-8').strip()
    print(f"📨 收到消息 -> Topic:[{message.topic}] 内容:[{payload}]")
    if payload == "on":
        print("🔔 收到 on 指令，执行唤醒...")
        wake_on_lan(MAC_ADDR)
    elif payload == "off":
        print("🔔 收到 off 指令，执行远程关机...")
        remote_shutdown()

print("🚀 启动巴法云 MQTT 唤醒/关机服务...")
print(f"   服务器:   {HOST}:{PORT}")
print(f"   主题:     {TOPIC}")
print(f"   唤醒 MAC: {MAC_ADDR}")
print(f"   广播:     {BROADCAST_IP}:9")
print(f"   关机 PC:  {PC_IP} ({PC_USER})")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, CLIENT_ID)
client.on_connect = on_connect
client.on_message = on_message
client.connect(HOST, PORT, 60)
client.loop_forever()