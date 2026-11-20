import subprocess
import sys


def ensure_dependencies():
    try:
        import win32api
        import win32con
        import win32gui
    except ImportError:
        print("Installing required dependency: pywin32...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pywin32"])


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
        canvas_width=1600,
        canvas_height=1200,
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

        self.wc = win32gui.WNDCLASS()
        self.wc.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
        self.wc.lpfnWndProc = self.wnd_proc
        self.wc.lpszClassName = "CanvasWindowClass"
        self.wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        self.wc.hbrBackground = win32con.COLOR_WINDOW + 1

        win32gui.RegisterClass(self.wc)
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

        max_x = max(0, self.canvas_width - self.client_width)
        self.scroll_x = min(self.scroll_x, max_x)
        si_x = (
            win32con.SIF_RANGE | win32con.SIF_PAGE | win32con.SIF_POS,
            0,
            max(0, self.canvas_width - 1),
            self.client_width,
            self.scroll_x,
            0,
        )
        win32gui.SetScrollInfo(self.hwnd, win32con.SB_HORZ, si_x, True)

        max_y = max(0, self.canvas_height - self.client_height)
        self.scroll_y = min(self.scroll_y, max_y)
        si_y = (
            win32con.SIF_RANGE | win32con.SIF_PAGE | win32con.SIF_POS,
            0,
            max(0, self.canvas_height - 1),
            self.client_height,
            self.scroll_y,
            0,
        )
        win32gui.SetScrollInfo(self.hwnd, win32con.SB_VERT, si_y, True)

    def handle_scroll(self, bar, wparam):
        action = win32api.LOWORD(wparam)
        si = win32gui.GetScrollInfo(self.hwnd, bar)
        pos = si[4]
        min_pos, max_pos, page = si[1], si[2], si[3]
        max_scroll = max(0, max_pos - page + 1)
        step = 20

        if action == win32con.SB_LINELEFT:  # Also SB_LINEUP
            pos -= step
        elif action == win32con.SB_LINERIGHT:  # Also SB_LINEDOWN
            pos += step
        elif action == win32con.SB_PAGELEFT:  # Also SB_PAGEUP
            pos -= page
        elif action == win32con.SB_PAGERIGHT:  # Also SB_PAGEDOWN
            pos += page
        elif action in (win32con.SB_THUMBTRACK, win32con.SB_THUMBPOSITION):
            pos = si[5]
        elif action == win32con.SB_TOP:  # Also SB_LEFT
            pos = min_pos
        elif action == win32con.SB_BOTTOM:  # Also SB_RIGHT
            pos = max_scroll

        pos = max(min_pos, min(pos, max_scroll))

        if bar == win32con.SB_HORZ:
            dx = self.scroll_x - pos
            if dx != 0:
                self.scroll_x = pos
                win32gui.SetScrollPos(self.hwnd, win32con.SB_HORZ, pos, True)
                win32gui.ScrollWindowEx(
                    self.hwnd, dx, 0, None, None, 0, None, win32con.SW_INVALIDATE | win32con.SW_ERASE
                )
        elif bar == win32con.SB_VERT:
            dy = self.scroll_y - pos
            if dy != 0:
                self.scroll_y = pos
                win32gui.SetScrollPos(self.hwnd, win32con.SB_VERT, pos, True)
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
        title="My Resizable Canvas App",
        width=640,
        height=480,
        canvas_width=1600,
        canvas_height=1200,
    )
    app.show()
