# 巴法云 MQTT 远程唤醒/关机

通过巴法云 MQTT 推送指令，远程唤醒和关机局域网内的 Windows 电脑。

## 功能

- 推送 `on` → 通过 Wake-on-LAN 魔术包唤醒电脑
- 推送 `off` → 通过 Samba 远程关机电脑

## 文件清单

| 文件 | 作用 |
|------|------|
| `wol.py` | 主程序：连接巴法云 MQTT 服务器并订阅指令；收到 `on` 发送 WOL 魔术包唤醒电脑，收到 `off` 调用 Samba 远程关机 |
| `config.py` | 真实配置文件：存放巴法云私钥、设备名、MAC 地址、广播 IP、电脑用户名密码等。**被 .gitignore 忽略，不会上传到仓库**，需自行创建 |
| `config.example.py` | 配置模板：克隆仓库后复制为 `config.py` 并填入自己的配置即可使用 |
| `Dockerfile` | Docker 镜像构建文件：基于 `python:3.12-slim`，安装 `samba`（提供 `net rpc shutdown` 关机命令）和 `paho-mqtt`（MQTT 客户端库） |
| `docker-compose.yml` | Docker Compose 编排文件：使用 `host` 网络模式（才能发送广播包唤醒电脑），容器异常退出时自动重启 |
| `.gitignore` | Git 忽略规则：忽略 `config.py`（防止密钥泄露）和 `__pycache__/`、`.pyc` 等 Python 缓存文件 |

## 配置方法

1. 复制模板文件为 `config.py`：
   ```
   copy config.example.py config.py
   ```
2. 编辑 `config.py`，填入你的真实配置：

```python
# 巴法云配置
HOST = "mqtt.bemfa.com"            # 巴法云 MQTT 服务器地址（默认即可）
PORT = 9501                        # 巴法云 MQTT 端口（默认即可）
CLIENT_ID = "你的巴法云私钥"          # 巴法云控制台 → 账号中心 → 私钥
TOPIC = "你的巴法云设备名"            # 巴法云控制台 → 设备管理 → 设备名称

# 唤醒配置
MAC_ADDR = "AA:BB:CC:DD:EE:FF"     # 被控电脑的 MAC 地址
BROADCAST_IP = "192.168.1.255"     # 你家的广播地址（网段最后一位改成255）
                                       # 例：电脑IP是 192.168.1.10，就填 192.168.1.255

# 远程关机配置
PC_IP = "192.168.1.2"              # 被控电脑的局域网 IP
PC_USER = "你的Windows用户名"         # 被控电脑的 Windows 用户名
PC_PASS = "你的Windows登录密码"       # 被控电脑的 Windows 登录密码（不是 PIN）
```

> ⚠️ `config.py` 已在 `.gitignore` 中忽略，不会被提交到仓库，放心填写。

---

## 一、Windows 被控电脑配置（一次性）

### 1.1 开启 BIOS Wake-on-LAN（唤醒必须）

1. 重启电脑，按 `Del` / `F2` / `F10`（看开机提示）进入 BIOS
2. 找到 `Wake on LAN` / `Power On By PCI-E` / `PME Event Wake Up`
3. 设为 **Enabled**，保存退出

### 1.2 允许网卡唤醒（唤醒必须）

1. 右键开始菜单 → **设备管理器**
2. 展开"网络适配器"，找到你的网卡 → 右键 → **属性**
3. 切换到"电源管理"标签
4. ✅ 勾选 **"允许此设备唤醒计算机"**
5. 切换到"高级"标签
6. 找到 `Wake on Magic Packet` → 设为 **Enabled**

### 1.3 允许远程关机（关机必须）

1. 按 `Win + R`，输入 **`regedit`**，回车
2. 粘贴路径跳转：
   ```
   HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System
   ```
3. 右侧空白处 → 右键 → **新建** → **DWORD (32 位) 值**
4. 名称填：`LocalAccountTokenFilterPolicy`
5. 双击它，数值填 **`1`**，确定
6. **重启电脑**生效

### 1.4 防火墙放行文件共享（关机必须）

1. 按 `Win` 搜 **"Windows Defender 防火墙"**，打开
2. 左侧点 **"允许应用或功能通过 Windows Defender 防火墙"**
3. 找到 **"文件和打印机共享"**，"专用"列打 ✅，确定
4. 检查网络类型：右下角网络图标 → 当前网络 → 网络配置文件 → 设为 **专用**（不是公用）

### 1.5 确认 MAC 地址和 IP

打开命令行（`Win + R` → `cmd` → 回车），执行：

```cmd
ipconfig /all
```

记下：
- **物理地址**（MAC）：例 `AA-BB-CC-DD-EE-FF`，可以用冒号或横杠
- **IPv4 地址**：例 `192.168.1.10`

### 1.6 确认用户名和密码

- **用户名**：命令行执行 `whoami`，反斜杠后面的就是用户名
- **密码**：Windows 登录密码（PIN 码不能用于远程关机）。如果只设了 PIN，去 **设置 → 账户 → 登录选项 → 密码 → 添加** 设置一个

---

## 二、NAS 端部署

### 2.1 前置要求

- 已安装 **Docker** + **Docker Compose**（飞牛/群晖/极空间应用商店直接搜 Docker）
- NAS 和被控电脑在**同一局域网**（同一网段，比如都是 `192.168.3.x`）
- NAS 能访问外网 `mqtt.bemfa.com:9501`

### 2.2 上传文件

先在本地把 `config.example.py` 复制为 `config.py` 并填入真实配置，然后把四个文件上传到 NAS 同一个目录，例如 `/docker/nas-pcwol/`：

```
/docker/nas-pcwol/
├── wol.py
├── config.py
├── Dockerfile
└── docker-compose.yml
```

### 2.3 修复权限（重要！）

```bash
cd /你的/docker/nas-pcwol/
chmod 644 Dockerfile docker-compose.yml wol.py config.py
chmod 755 .
```

### 2.4 一键构建启动

```bash
docker compose up -d --build
```

### 2.5 查看日志确认

```bash
docker compose logs -f wol-mqtt
```

看到以下输出就是成功：
```
🚀 启动巴法云 MQTT 唤醒/关机服务...
✅ MQTT连接成功，订阅主题: 你的设备名
```

### 2.6 常用命令

```bash
docker compose logs -f wol-mqtt       # 实时看日志
docker compose restart wol-mqtt        # 重启
docker compose stop                   # 停止
docker compose down                   # 停止并删除容器
docker compose pull && docker compose up -d  # 更新重启
```

---

## 三、使用说明

1. 登录 [巴法云控制台](https://cloud.bemfa.com/)
2. 找到你的设备（设备名 = `wol.py` 里的 TOPIC）
3. 在设备详情页输入指令：
   - 输入 **`on`** → 唤醒电脑（电脑关机/睡眠状态下）
   - 输入 **`off`** → 远程关机电脑（电脑开机状态下）
4. 查看 NAS 日志 `docker compose logs -f wol-mqtt` 确认收到指令

---

## 四、快速排查

### 4.1 唤醒不了？

| 检查项 | 命令/方法 |
|--------|-----------|
| MAC 地址对不对 | Windows `ipconfig /all` 查 |
| 广播地址对不对 | 网段最后一位改成 255 |
| BIOS 开了 WOL | 进 BIOS 看 Wake on LAN |
| 电源设置 | 网卡属性 → 电源管理 → 允许唤醒 |

在 NAS 上手动测试：
```bash
docker exec -it wol-mqtt python -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
# 把 MAC 改成你的，广播地址也改
import sys
mac = 'AA:BB:CC:DD:EE:FF'.replace(':','')
data = b'\xff'*6 + bytes.fromhex(mac)*16
s.sendto(data, ('192.168.1.255', 9))
print('魔术包已发送')
"
```

### 4.2 关机报 `Access Denied`？

- 检查注册表 `LocalAccountTokenFilterPolicy` 是不是 = 1，有没有重启过
- 检查用户名密码对不对（PIN 不能用）
- 手动测试：在电脑上 `Win + R` 输入 `shutdown /a` 看有没有取消正在进行的关机
- 在 NAS 上手动测 `net rpc shutdown -I 电脑IP -U 用户名%密码 -f`

### 4.3 关机超时 / 电脑不在线？

- 检查电脑 IP 是不是变了（路由器 DHCP 可能会换）
- 检查防火墙有没有开"文件和打印机共享"
- 检查网络类型是不是"专用"
- 在 NAS 上测试端口通不通：
  ```bash
  timeout 3 bash -c 'echo > /dev/tcp/电脑IP/445' && echo "✅ 445通" || echo "❌ 445不通"
  ```

### 4.4 MQTT 连接不上？

- 确认 CLIENT_ID 是**巴法云私钥**（不是设备名）
- 确认 NAS 能出网：`ping mqtt.bemfa.com`
- 确认 topic 是**设备名本身**（不是带手机号前缀的长字符串）

### 4.5 Docker 构建慢？

Docker Hub 拉镜像慢，在 NAS Docker 设置里加镜像加速器：
```
https://docker.1ms.run
```

或者用 compose 覆盖：
```bash
docker compose build --build-arg HTTP_PROXY=http://你的代理:端口
```

### 4.6 容器重启后命令丢失？

如果 `net rpc shutdown` 报 `command not found`，说明镜像没正确构建。强制重建：
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

---

## 五、完整流程示例

```
┌─────────┐    推 on/off     ┌──────────┐    MQTT     ┌─────────┐    SMB/WOL    ┌──────────┐
│ 手机/网页 │ ──────────────→ │ 巴法云服务器 │ ◄─────────→ │  NAS     │ ──────────────→ │  Windows │
└─────────┘                  └──────────┘             └─────────┘                 └──────────┘
                                                           │
                                                     wol.py 订阅消息
                                                     收到 on → 发魔术包唤醒
                                                     收到 off → 远程关机
```