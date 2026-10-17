# DualSense USB Audio

Windows CMD 原生助手：让 DualSense / DualSense Edge 的马达跟随电脑声音振动。

本仓库只包含命令行 USB 助手。无需浏览器，不含网页测试器，也不含蓝牙功能。

## 下载和使用

下载 `DualSense-USB-Audio-v1.0.1-windows-x64.zip`，完整解压后双击 `Start-USB-Native.cmd`。发布包自带运行环境，不需要安装 Python。

1. 用 USB 数据线连接一只 DualSense 或 DualSense Edge。
2. 在 Windows 的传统声音控制面板中，选择手柄的扬声器 → 配置 → 四声道。关闭手柄音频增强（若有）。
3. Windows 默认声音输出保持为电脑音箱或耳机，别设为手柄。
4. 关闭其他软件或网页的手柄音频播放，再双击 CMD 启动。
5. 在电脑正常播放音乐、视频或游戏。音箱继续出声，程序把默认输出的回环音频送到手柄后两个声道，驱动马达。

输入峰值始终是 0 表示当前默认输出没有捕获到声音。切换系统默认输出后请停止并重新启动助手。不支持同时连接多只 USB 手柄；未找到唯一的四声道输出时会停止并提示。

## 按键和强度

| 按键 | 功能 |
| --- | --- |
| `+` / `-` | 强度增减 5%，范围 0～200%，默认 100%（与原版增益设置一致） |
| 空格 | 立即静音 / 恢复马达 |
| `Q` / `Ctrl+C` | 停止并关闭手柄音频输出 |

这些按键在 CMD 窗口获得焦点时生效。不要点击窗口进入文本选择状态，以免暂停控制台进程；停止时优先使用 Q 或 Ctrl+C。

“马达音量”就是送给马达的信号强度。电脑音箱/耳机音量仍由 Windows 控制。程序不会把声音重复播放到手柄扬声器，也不会修改默认输出设备。

也可以从终端启动：

```bat
Start-USB-Native.cmd --gain 50
Start-USB-Native.cmd --gain 30 --seconds 60
```

## 软件保护

保护始终开启，仅作用于马达信号：

- 20 Hz 高通移除直流偏置；每改变 100% 强度，约 100 毫秒渐变。
- 允许瞬时输出达到归一化满幅 1.0，不再把所有片段的峰值限制为 0.5。
- 以约 1 秒时间常数跟踪每声道实际输出能量，能量估计的平方根上限仍为 0.18；短促信号可使用剩余能量空间，持续强信号会衰减。两个马达分别计算。
- 增益设置与原版一致，保护仍会改变持续强信号，因此不承诺与原版在所有声音下振动完全相同；高通、系统音量和设备设置也会影响实际效果。
- 运行 20 分钟后静音休息 30 秒，再自动恢复。
- 无效数值清零；输入中断时输出静音，超过 3 秒自动退出；阻止同时运行多个助手实例。

这些是未经厂商认证的软件限制，程序无法测量马达温度，不能保证任何情况下都不损坏。明显发热或异常声音时请停止并冷却。正常退出和可捕获异常会关闭音频流并静音；断电或强制终止进程时无法保证执行清理代码。

## 隐私和适用范围

只实时读取 Windows 默认输出的回环音频，不录制、不保存、不上传声音。保持输入采样率，由 Windows WASAPI 共享引擎转换到手柄声卡格式；不变速或变调。电脑原有播放信号不经过本程序处理。

本机已验证普通 DualSense USB 回环输出可振动。Edge 设备 ID 已支持，但未完成 Edge 实物验证。不同电脑的驱动和声卡配置仍需实际测试。

## 从源码运行

需要 Windows x64 和 Python 3.12 x64。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-usb.txt
.\Start-USB-Native.cmd
```

运行信号保护测试（含瞬时满幅、持续能量限制与静音后能量恢复）：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s native_tests -v
```

## 构建发布包

```powershell
python -m venv .build-venv
.\.build-venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\build-windows.ps1 -Python .\.build-venv\Scripts\python.exe
```

生成的 ZIP 和 SHA256 校验文件位于 `artifacts`。包内附第三方许可证。使用 PyInstaller 打包，未进行代码签名。

## 来源与许可

MIT License。保留 [daidr/dualsense-tester](https://github.com/daidr/dualsense-tester) 的原始署名及许可证。此助手源于该项目系统声音跟随功能的本地开发和诊断，使用其 DualSense 音频路由约定；本仓库独立提供 Windows 原生回环路径。与 Sony 无隶属关系。

使用 NumPy、python-sounddevice、PyAudioWPatch、hidapi、PortAudio 及 Python；其许可见发布包 `THIRD-PARTY-NOTICES.txt` 和 `licenses/`。
