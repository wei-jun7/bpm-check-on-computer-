import asyncio
import threading
import tkinter as tk
from tkinter import ttk
from bleak import BleakClient, BleakScanner
import queue
import pystray
from PIL import Image, ImageDraw
from tkinter import simpledialog, messagebox
import sys


# -------------------- 全局变量 --------------------
heart_queue = queue.Queue()
TARGET_ADDRESS = None
TARGET_NAME = None
root = None
icon = None
icon_created = False
TRANSPARENT = False

heart_count = 0
heart_sum = 0
heart_max = 0
heart_min = 0
stop_event = threading.Event()
BLE_LOOP = None

# -------------------- 心率解析 --------------------
def parse_heart_rate(data: bytearray) -> int:
    flags = data[0]
    hr_format = flags & 0x01
    if hr_format == 0:
        return data[1]
    else:
        return int.from_bytes(data[1:3], byteorder="little")

def notification_handler(sender, data):
    global heart_count, heart_sum, heart_max, heart_min
    hr = parse_heart_rate(data)
    heart_queue.put(hr)
    heart_count += 1
    heart_sum += hr
    heart_max = max(hr, heart_max) if heart_count > 1 else hr
    heart_min = min(hr, heart_min) if heart_count > 1 else hr
    print(f"❤️ 心率: {hr} bpm")

# -------------------- BLE 后台线程 --------------------
async def ble_task(address, uuid):
    try:
        while not stop_event.is_set():
            try:
                async with BleakClient(address) as client:
                    print(f"✅ 已连接 {TARGET_NAME}, 开始接收心率...")
                    await client.start_notify(uuid, notification_handler)
                    while not stop_event.is_set() and client.is_connected:
                        await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                if not stop_event.is_set():
                    print(f"⚠️ BLE 异常: {e}, 5秒后重连")
                    await asyncio.sleep(5)
    finally:
        print("✅ ble_task 已退出")

def start_ble_loop(address, uuid):
    global BLE_LOOP
    loop = asyncio.new_event_loop()
    BLE_LOOP = loop
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(ble_task(address, uuid))
    except Exception as e:
        print(f"⚠️ BLE 循环异常: {e}")
    finally:
        try:
            # 取消所有未完成任务
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception as e:
            print(f"⚠️ 关闭 BLE 循环时异常: {e}")
        finally:
            loop.close()
            print("✅ BLE 循环已关闭")

# -------------------- 托盘 --------------------
def create_image():
    img = Image.new('RGB', (64, 64), color='white')
    d = ImageDraw.Draw(img)
    d.ellipse((16, 16, 48, 48), fill='red')
    return img

def quit_app(icon_obj, item):
    print("🛑 正在退出程序...")

    # 停止托盘图标
    try:
        icon_obj.stop()
    except Exception:
        pass

    # 通知 BLE 循环退出
    stop_event.set()
    try:
        if BLE_LOOP is not None:
            for task in asyncio.all_tasks(BLE_LOOP):
                task.cancel()
    except Exception:
        pass

    # Tk 主窗口退出
    if root:
        try:
            root.after(0, root.destroy)
        except Exception:
            try:
                root.destroy()
            except Exception:
                pass

    print("✅ 程序退出完成")
    sys.exit(0)

def restore_window(icon_obj, item):
    if not root:
        return

    def _restore():
        root.deiconify()
        if TRANSPARENT:
            root.overrideredirect(True)
            root.attributes("-topmost", True)
        else:
            root.overrideredirect(False)
            try:
                notebook.pack(expand=True, fill="both")
            except Exception:
                pass
        try:
            icon.visible = False
        except Exception:
            pass

    try:
        root.after(0, _restore)
    except Exception:
        _restore()

def minimize_to_tray():
    global icon, icon_created
    root.withdraw()
    if not icon_created:
        icon = pystray.Icon("HeartMonitor", create_image(), "心率监控")
        icon.menu = pystray.Menu(
            pystray.MenuItem("显示窗口", restore_window),
            pystray.MenuItem("退出", quit_app)
        )
        threading.Thread(target=icon.run, daemon=True).start()
        icon_created = True
    else:
        icon.visible = True


# -------------------- GUI --------------------
def set_transparent(enable: bool):
    global TRANSPARENT
    TRANSPARENT = enable
    if root is None:
        return

    if TRANSPARENT:
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg="white")
        root.attributes("-transparentcolor", "white")

        notebook.pack_forget()
        float_label.config(bg="white", fg="red")
        float_label.place(relx=0.5, rely=0.5, anchor="center")
        float_label.bind("<Button-1>", start_move)
        float_label.bind("<B1-Motion>", do_move)
    else:
        root.overrideredirect(False)
        root.attributes("-transparentcolor", "")
        root.configure(bg="lightgray")

        float_label.place_forget()
        float_label.unbind("<Button-1>")
        float_label.unbind("<B1-Motion>")
        notebook.pack(expand=True, fill="both")

def start_move(event):
    root._drag_x = event.x_root - root.winfo_x()
    root._drag_y = event.y_root - root.winfo_y()

def do_move(event):
    x = event.x_root - root._drag_x
    y = event.y_root - root._drag_y
    root.geometry(f"+{x}+{y}")

def gui_app():
    global root, notebook, float_label
    root = tk.Tk()
    root.title("心率监控")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    window_width = 250
    window_height = 120
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = screen_width - window_width - 100
    y = screen_height - window_height - 100
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    notebook = ttk.Notebook(root)
    notebook.pack(expand=True, fill="both")

    tab_heart = ttk.Frame(notebook)
    notebook.add(tab_heart, text="心率")
    current_heart_rate = tk.StringVar(value="等待数据...")
    normal_label = tk.Label(tab_heart, textvariable=current_heart_rate,
                            font=("Arial", 32), fg="red", bg="lightgray")
    normal_label.pack(expand=True, padx=10, pady=10)

    tab_options = ttk.Frame(notebook)
    notebook.add(tab_options, text="显示选项")
    transparent_var = tk.BooleanVar(value=False)
    tk.Checkbutton(tab_options, text="透明显示", variable=transparent_var,
                   command=lambda: set_transparent(transparent_var.get())).pack(pady=10)

    float_label = tk.Label(root, textvariable=current_heart_rate, font=("Arial", 32),
                           fg="red", bg="white")

    def update_gui():
        while not heart_queue.empty():
            hr = heart_queue.get()
            current_heart_rate.set(f"{hr} bpm")
        root.after(500, update_gui)

    root.after(500, update_gui)

    # ==== 新增退出确认 ====
    def on_close():
        if messagebox.askyesno("退出确认", "是否退出程序？"):
            quit_app(icon, None)
        else:
            minimize_to_tray()

    root.protocol("WM_DELETE_WINDOW", on_close)

    root.mainloop()

# -------------------- 蓝牙 --------------------
async def select_device():
    devices = await BleakScanner.discover()
    if not devices:
        messagebox.showerror("错误", "未找到蓝牙设备")
        return None, None

    options = [f"{i}: {d.name or '未知设备'} ({d.address})" for i, d in enumerate(devices)]
    choice = simpledialog.askinteger("选择设备", 
                                     "扫描到以下设备：\n" + "\n".join(options) + "\n\n请输入编号：")
    if choice is None or choice < 0 or choice >= len(devices):
        messagebox.showerror("错误", "选择无效")
        return None, None

    d = devices[choice]
    return d.address, d.name

async def select_heart_uuid(address):
    async with BleakClient(address) as client:
        notify_chars = [c.uuid for s in client.services for c in s.characteristics if "notify" in c.properties]
        if not notify_chars:
            messagebox.showerror("错误", "没有可通知特征")
            return None

        options = []
        for i, uuid in enumerate(notify_chars):
            if uuid.lower() == "00002a37-0000-1000-8000-00805f9b34fb":
                options.append(f"{i}: {uuid}   ← 心率特征")
            else:
                options.append(f"{i}: {uuid}")

        choice = simpledialog.askinteger("选择特征", 
                                         "可用特征：\n" + "\n".join(options) + "\n\n请输入编号：")
        if choice is None or choice < 0 or choice >= len(notify_chars):
            messagebox.showerror("错误", "选择无效")
            return None

        return notify_chars[choice]

# -------------------- 主程序 --------------------
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    TARGET_ADDRESS, TARGET_NAME = loop.run_until_complete(select_device())
    if not TARGET_ADDRESS:
        sys.exit(1)

    HEART_UUID = loop.run_until_complete(select_heart_uuid(TARGET_ADDRESS))
    if not HEART_UUID:
        sys.exit(1)

    t = threading.Thread(target=start_ble_loop, args=(TARGET_ADDRESS, HEART_UUID), daemon=True)
    t.start()

    gui_app()
    print("🛑 主线程结束")
    sys.exit(0)
