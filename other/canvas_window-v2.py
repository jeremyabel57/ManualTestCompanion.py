import importlib.util
import subprocess
import sys


def ensure_dependencies():
    """Check for required packages and auto-install them if missing."""
    required = {"win32gui": "pywin32"}
    for module_name, package_name in required.items():
        if importlib.util.find_spec(module_name) is None:
            print(f"Installing missing dependency: {package_name}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])


ensure_dependencies()

import win32api
import win32con
import win32gui


class CanvasWindow:
    def __init__(
        self,
        title="Canvas Window",
        width=800,
        height=600,
        canvas_width=2000,
        canvas_height=2000,
    ):
        self.title = title
        self.width = width
        self.height = height
        self.client_width = width
        self.client_height = height
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.scroll_x = 0
        self.scroll_y = 0
        self.hwnd = None

        # Register the window class
        self.wc = win32gui.WNDCLASS()
        self.wc.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
        self.wc.lpfnWndProc = self.wnd_proc
        self.wc.hInstance = win32api.GetModuleHandle(None)
        self.wc.lpszClassName = "CanvasWindowClass"
        self.wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        self.wc.hbrBackground = win32con.COLOR_WINDOW + 1

        try:
            win32gui.RegisterClass(self.wc)
        except win32gui.error:
            pass

        # Create the resizable window with scrollbars
        self.create_window()

    def create_window(self):
        style = (
            win32con.WS_OVERLAPPEDWINDOW
            | win32con.WS_HSCROLL
            | win32con.WS_VSCROLL
        )
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

    def update_scrollbars(self):
        if not self.hwnd:
            return

        # Clamp current scroll positions to valid bounds
        max_x = max(0, self.canvas_width - self.client_width)
        max_y = max(0, self.canvas_height - self.client_height)
        self.scroll_x = max(0, min(self.scroll_x, max_x))
        self.scroll_y = max(0, min(self.scroll_y, max_y))

        # Horizontal SCROLLINFO: (fMask, nMin, nMax, nPage, nPos, nTrackPos)
        si_h = (
            win32con.SIF_RANGE | win32con.SIF_PAGE | win32con.SIF_POS,
            0,
            max(0, self.canvas_width - 1),
            self.client_width,
            self.scroll_x,
            0,
        )
        win32gui.SetScrollInfo(self.hwnd, win32con.SB_HORZ, si_h, True)

        # Vertical SCROLLINFO: (fMask, nMin, nMax, nPage, nPos, nTrackPos)
        si_v = (
            win32con.SIF_RANGE | win32con.SIF_PAGE | win32con.SIF_POS,
            0,
            max(0, self.canvas_height - 1),
            self.client_height,
            self.scroll_y,
            0,
        )
        win32gui.SetScrollInfo(self.hwnd, win32con.SB_VERT, si_v, True)

    def handle_scroll(self, bar, wparam):
        action = win32api.LOWORD(wparam)
        si = win32gui.GetScrollInfo(self.hwnd, bar, win32con.SIF_ALL)
        # si tuple: (fMask, nMin, nMax, nPage, nPos, nTrackPos)
        n_min, n_max, n_page, pos, track_pos = si[1], si[2], si[3], si[4], si[5]
        max_pos = max(0, n_max - n_page + 1)

        step = 20
        if action == win32con.SB_LINEUP:  # Also SB_LINELEFT
            pos -= step
        elif action == win32con.SB_LINEDOWN:  # Also SB_LINERIGHT
            pos += step
        elif action == win32con.SB_PAGEUP:  # Also SB_PAGELEFT
            pos -= n_page
        elif action == win32con.SB_PAGEDOWN:  # Also SB_PAGERIGHT
            pos += n_page
        elif action in (win32con.SB_THUMBTRACK, win32con.SB_THUMBPOSITION):
            pos = track_pos
        elif action == win32con.SB_TOP:  # Also SB_LEFT
            pos = n_min
        elif action == win32con.SB_BOTTOM:  # Also SB_RIGHT
            pos = max_pos

        pos = max(n_min, min(pos, max_pos))

        # Apply updated position exclusively using SetScrollInfo
        si_update = (
            win32con.SIF_POS,
            0,
            0,
            0,
            pos,
            0,
        )
        win32gui.SetScrollInfo(self.hwnd, bar, si_update, True)

        if bar == win32con.SB_HORZ:
            dx = self.scroll_x - pos
            self.scroll_x = pos
            if dx != 0:
                win32gui.ScrollWindowEx(
                    self.hwnd, dx, 0, None, None, 0, None, win32con.SW_INVALIDATE | win32con.SW_ERASE
                )
        elif bar == win32con.SB_VERT:
            dy = self.scroll_y - pos
            self.scroll_y = pos
            if dy != 0:
                win32gui.ScrollWindowEx(
                    self.hwnd, 0, dy, None, None, 0, None, win32con.SW_INVALIDATE | win32con.SW_ERASE
                )

    def wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_SIZE:
            self.client_width = win32api.LOWORD(lparam)
            self.client_height = win32api.HIWORD(lparam)
            self.update_scrollbars()
            return 0
        elif msg == win32con.WM_HSCROLL:
            self.handle_scroll(win32con.SB_HORZ, wparam)
            return 0
        elif msg == win32con.WM_VSCROLL:
            self.handle_scroll(win32con.SB_VERT, wparam)
            return 0
        elif msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def show(self):
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        win32gui.UpdateWindow(self.hwnd)
        win32gui.PumpMessages()


if __name__ == "__main__":
    app = CanvasWindow(
        title="Resizable Win32 Canvas",
        width=800,
        height=600,
        canvas_width=2000,
        canvas_height=2000,
    )
    app.show()
