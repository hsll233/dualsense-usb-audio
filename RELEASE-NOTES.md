# DualSense USB Audio v1.0.0

Windows CMD 原生 USB 系统声音跟随助手。

下载 `DualSense-USB-Audio-v1.0.0-windows-x64.zip`，完整解压，双击 `Start-USB-Native.cmd`，无需安装 Python。

- Windows 默认输出保持为电脑音箱或耳机，手柄 USB 音频配置为四声道。
- `+` / `-` 调整振动强度；空格静音/恢复；`Q` 或 `Ctrl+C` 停止。
- 包含去直流、限幅、每块 RMS 限制、强度渐变及定时休息。软件保护未经厂商认证，不能保证绝不损坏马达。
- 仅 USB，不含网页或蓝牙功能；不录制或上传声音。

验证：4 项信号保护测试通过；本机原生 USB 回环已验证可振动；打包程序依赖加载、版本/帮助及重复启动保护验证通过。尚未在全新 Windows 环境验证，也未完成 DualSense Edge 实物测试。

ZIP 的 SHA256 校验值见同名 `.sha256` 附件。保留原项目署名和 MIT 许可证；发布包附第三方许可证。
