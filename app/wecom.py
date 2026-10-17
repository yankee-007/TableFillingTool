"""WeCom window inspection and open-only search, extracted without messaging code.

Native calls are made only by an explicit user action in the application. Tests inject
a fake desktop; importing this module never enumerates windows or presses keys.
"""
from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import PureWindowsPath

from .matching import name_in_title


@dataclass(frozen=True)
class Window:
    handle: int
    pid: int
    title: str
    executable: str

    @property
    def is_wecom(self):
        return PureWindowsPath(self.executable).name.casefold() in ("wxwork.exe", "wecom.exe")


class NativeDesktop:
    def __init__(self):
        if sys.platform != "win32":
            raise RuntimeError("企业微信联系人和聊天跟随需要 Windows")
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.user.GetForegroundWindow.restype = wintypes.HWND
        self.user.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        self.user.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.user.IsWindow.argtypes = [wintypes.HWND]
        self.user.IsWindowVisible.argtypes = [wintypes.HWND]
        self.user.IsIconic.argtypes = [wintypes.HWND]
        self.user.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user.SetForegroundWindow.argtypes = [wintypes.HWND]
        self.kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.kernel.OpenProcess.restype = wintypes.HANDLE
        self.kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]

    def inspect(self, handle) -> Window | None:
        if not handle or not self.user.IsWindow(handle):
            return None
        size = self.user.GetWindowTextLengthW(handle) + 1
        title = ctypes.create_unicode_buffer(size)
        self.user.GetWindowTextW(handle, title, size)
        pid = wintypes.DWORD()
        self.user.GetWindowThreadProcessId(handle, ctypes.byref(pid))
        process = self.kernel.OpenProcess(0x1000, False, pid.value)
        if not process:
            return None
        try:
            buffer = ctypes.create_unicode_buffer(32768)
            length = wintypes.DWORD(len(buffer))
            if not self.kernel.QueryFullProcessImageNameW(process, 0, buffer, ctypes.byref(length)):
                return None
            return Window(int(handle), pid.value, title.value.strip(), buffer.value)
        finally:
            self.kernel.CloseHandle(process)

    def foreground(self) -> Window | None:
        return self.inspect(self.user.GetForegroundWindow())

    def main_window(self) -> Window:
        windows = []
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        @callback_type
        def callback(hwnd, _):
            if self.user.IsWindowVisible(hwnd):
                window = self.inspect(hwnd)
                if window and window.is_wecom and window.title in ("企业微信", "WeCom"):
                    windows.append(window)
            return True

        self.user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
        self.user.EnumWindows(callback, 0)
        if not windows:
            raise RuntimeError("请先打开并登录企业微信主窗口")
        if len(windows) != 1:
            raise RuntimeError("检测到多个企业微信主窗口，请先保留一个目标窗口")
        return windows[0]

    def activate(self, window: Window):
        if self.user.IsIconic(window.handle):
            self.user.ShowWindow(window.handle, 9)
        if not self.user.SetForegroundWindow(window.handle):
            current = self.foreground()
            if not current or current.handle != window.handle:
                raise RuntimeError("无法激活企业微信，请手动打开主窗口后重试")

    def clipboard_text(self):
        self.user.OpenClipboard.argtypes = [wintypes.HWND]
        self.user.GetClipboardData.argtypes = [wintypes.UINT]
        self.user.GetClipboardData.restype = wintypes.HANDLE
        self.kernel.GlobalLock.argtypes = [wintypes.HANDLE]
        self.kernel.GlobalLock.restype = ctypes.c_void_p
        self.kernel.GlobalUnlock.argtypes = [wintypes.HANDLE]
        if not self.user.OpenClipboard(None):
            raise RuntimeError("无法核对搜索剪贴板，请稍后重试")
        try:
            handle = self.user.GetClipboardData(13)  # CF_UNICODETEXT
            address = self.kernel.GlobalLock(handle) if handle else None
            if not address:
                return None
            try:
                return ctypes.wstring_at(address)
            finally:
                self.kernel.GlobalUnlock(handle)
        finally:
            self.user.CloseClipboard()

    def keys(self, *keys):
        # Include the full INPUT union so sizeof(INPUT) is correct on both x86/x64.
        ulong_ptr = ctypes.c_size_t

        class Keyboard(ctypes.Structure):
            _fields_ = [("vk", wintypes.WORD), ("scan", wintypes.WORD),
                        ("flags", wintypes.DWORD), ("time", wintypes.DWORD), ("extra", ulong_ptr)]

        class Mouse(ctypes.Structure):
            _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("data", wintypes.DWORD),
                        ("flags", wintypes.DWORD), ("time", wintypes.DWORD), ("extra", ulong_ptr)]

        class Hardware(ctypes.Structure):
            _fields_ = [("msg", wintypes.DWORD), ("low", wintypes.WORD), ("high", wintypes.WORD)]

        class Union(ctypes.Union):
            _fields_ = [("keyboard", Keyboard), ("mouse", Mouse), ("hardware", Hardware)]

        class Input(ctypes.Structure):
            _anonymous_ = ("value",)
            _fields_ = [("type", wintypes.DWORD), ("value", Union)]

        codes = {"ctrl": 0x11, "enter": 0x0D, "f": 0x46, "a": 0x41,
                 "v": 0x56, "o": 0x4F, "w": 0x57}
        events = [Input(type=1, keyboard=Keyboard(vk=codes[key])) for key in keys]
        events += [Input(type=1, keyboard=Keyboard(vk=codes[key], flags=2)) for key in reversed(keys)]
        array = (Input * len(events))(*events)
        self.user.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int]
        count = self.user.SendInput(len(events), array, ctypes.sizeof(Input))
        if count != len(events):
            # Release modifiers if the OS accepted only part of the input sequence.
            for key in keys:
                release = Input(type=1, keyboard=Keyboard(vk=codes[key], flags=2))
                self.user.SendInput(1, ctypes.byref(release), ctypes.sizeof(Input))
            raise RuntimeError("系统拒绝键盘输入，请确认企业微信与工具使用相同权限级别")


class ContactSearch:
    def __init__(self, desktop, *, wait=0.5, timeout=3.0, sleep=time.sleep,
                 clock=time.monotonic, cancelled=lambda: False):
        self.desktop, self.wait, self.timeout = desktop, wait, timeout
        self.sleep, self.clock, self.cancelled = sleep, clock, cancelled

    def check(self, expected: Window):
        if self.cancelled():
            raise RuntimeError("打开操作已取消")
        current = self.desktop.foreground()
        if (not current or not current.is_wecom or current.handle != expected.handle
                or current.pid != expected.pid or current.title != expected.title):
            raise RuntimeError("企业微信窗口或焦点已变化，已停止操作")

    def press(self, expected, *keys):
        self.check(expected)
        self.desktop.keys(*keys)

    def open(self, contact: str, *, verify=True, keep_float=True) -> str:
        contact = contact.strip()
        if not contact or any(ch in contact for ch in "\r\n\0"):
            raise ValueError("联系人不能为空或包含换行")
        main = self.desktop.main_window()
        if not main.is_wecom:
            raise RuntimeError("目标窗口不是企业微信")
        self.desktop.activate(main)
        self.sleep(self.wait)
        self.press(main, "ctrl", "f")
        self.sleep(self.wait)
        self.press(main, "ctrl", "a")
        # The GUI temporarily placed the immutable search query on the clipboard.
        if self.desktop.clipboard_text() != contact:
            raise RuntimeError("剪贴板已变化，已停止搜索；请重新打开联系人")
        self.press(main, "ctrl", "v")
        self.sleep(self.wait)
        self.press(main, "enter")
        self.sleep(self.wait)
        if not verify:
            self.check(main)
            return "已搜索（未验证），请人工核对：" + contact
        self.press(main, "ctrl", "o")
        deadline = self.clock() + self.timeout
        while self.clock() < deadline:
            if self.cancelled():
                raise RuntimeError("打开操作已取消")
            current = self.desktop.foreground()
            if current and current.handle != main.handle:
                if current.pid != main.pid or not current.is_wecom:
                    raise RuntimeError("焦点已转到其他程序，已停止操作")
                if not name_in_title("".join(contact.split()), "".join(current.title.split())):
                    raise RuntimeError("联系人窗口标题不匹配，已停止；请人工核对")
                self.check(current)
                if not keep_float:
                    self.press(current, "ctrl", "w")
                    self.sleep(self.wait)
                    self.check(main)
                return ("已打开联系人独立聊天窗：" if keep_float else "已定位联系人：") + contact
            self.sleep(0.1)
        raise RuntimeError("未打开联系人独立聊天窗，请检查 Ctrl+O 快捷键或搜索结果")
