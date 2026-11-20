import subprocess
import sys

def ensure_dependencies(packages):
    """Checks for required packages and installs any that are missing."""
    for import_name, pip_name in packages.items():
        try:
            __import__(import_name)
        except ImportError:
            print(f"Installing missing dependency: {pip_name}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])

# Ensure pywin32 is installed before importing win32 modules
ensure_dependencies({"win32gui": "pywin32"})

import win32con
import win32gui


class MainWindow:

    def __init__(self, title="Win32 Window", width=800, height=600):
        self.title = title
        self.width = width
        self.height = height
        self.hwnd = None

        # Register the window class
        self.wc = win32gui.WNDCLASS()
        self.wc.lpfnWndProc = self.wnd_proc
        self.wc.lpszClassName = "BasicPythonWin32Class"
        self.wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        self.wc.hbrBackground = win32con.COLOR_WINDOW + 1

        win32gui.RegisterClass(self.wc)

        # Create the window
        self.create_window()

    def create_window(self):
        style = win32con.WS_OVERLAPPEDWINDOW
        self.hwnd = win32gui.CreateWindow(
            self.wc.lpszClassName,
            self.title,
            style,
            win32con.CW_USEDEFAULT,
            win32con.CW_USEDEFAULT,
            self.width,
            self.height,
            0,
            0,
            self.wc.hInstance,
            None,
        )

    def wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def show(self):
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        win32gui.UpdateWindow(self.hwnd)

        # Run the message loop
        win32gui.PumpMessages()


if __name__ == "__main__":
    app = MainWindow(title="My Win32 App", width=640, height=480)
    app.show()
