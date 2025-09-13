# Heart Rate Monitor (Python)

基于 Python 的蓝牙心率监控工具，支持实时心率显示、透明悬浮模式和系统托盘最小化。

---

## 功能特性

- 使用 [Bleak](https://github.com/hbldh/bleak) 连接蓝牙心率设备。
- 实时接收和显示心率数据。
- GUI 显示，可切换：
  - 普通窗口模式（带 Tab）
  - 透明悬浮模式（只显示红色心率文字）
- 支持最小化到系统托盘，后台运行。
- 自动统计心率：
  - 当前心率
---

## 安装依赖

确保 Python >= 3.10，然后安装所需依赖：

```bash
pip install bleak pystray pillow


UI 说明

普通模式
显示心率和选项 Tab。

透明悬浮模式
仅显示红色心率数字，可拖动位置，适合桌面常驻显示。

托盘最小化
关闭窗口时自动最小化到系统托盘，右键菜单可恢复窗口或退出。

代码结构

heart_monitor.py — 主程序

BLE 连接与心率数据接收 (BleakClient)

GUI (tkinter, ttk)

托盘图标 (pystray, PIL)

异步数据处理 (queue, threading)




注意事项

设备必须支持 BLE 心率服务。

蓝牙连接可能不稳定，程序会自动尝试重连。

Windows 系统透明窗口可能对某些版本支持有限。

对于大多数 BLE 心率设备，UUID 通常为 00002a37-0000-1000-8000-00805f9b34fb。
