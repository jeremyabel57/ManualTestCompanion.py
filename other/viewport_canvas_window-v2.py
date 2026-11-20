import importlib.util
import subprocess
import sys


def ensure_dependencies():
    if importlib.util.find_spec("win32gui") is None:
        print("pywin32 not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pywin32"])


ensure_dependencies()

import win32api
import win32con
import win32gui

WM_MOUSEHWHEEL = getattr(win32con, "WM_MOUSEHWHEEL", 0x020E)


class ViewportWindow:

    def __init__(
        self,
        title="Viewport & Canvas Window",
        width=800,
        height=600,
        canvas_width=2000,
        canvas_height=2000,
    ):
        self.title = title
        self.width = width
        self.height = height
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height

        self.scroll_x = 0
        self.scroll_y = 0
        self.wheel_step = 40

        self.hwnd = None
        self.canvas_hwnd = None

        self.register_classes()
        self.create_windows()

    def register_classes(self):
        # Register Viewport Window Class
        self.vp_wc = win32gui.WNDCLASS()
        self.vp_wc.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
        self.vp_wc.lpfnWndProc = self.viewport_wnd_proc
        self.vp_wc.lpszClassName = "PythonWin32ViewportClass"
        self.vp_wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        self.vp_wc.hbrBackground = win32con.COLOR_APPWORKSPACE + 1
        win32gui.RegisterClass(self.vp_wc)

        # Register Child Canvas Window Class
        self.canvas_wc = win32gui.WNDCLASS()
        self.canvas_wc.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
        self.canvas_wc.lpfnWndProc = self.canvas_wnd_proc
        self.canvas_wc.lpszClassName = "PythonWin32CanvasClass"
        self.canvas_wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        self.canvas_wc.hbrBackground = win32con.COLOR_WINDOW + 1
        win32gui.RegisterClass(self.canvas_wc)

    def create_windows(self):
        vp_style = (
            win32con.WS_OVERLAPPEDWINDOW
            | win32con.WS_HSCROLL
            | win32con.WS_VSCROLL
            | win32con.WS_CLIPCHILDREN
        )
        self.hwnd = win32gui.CreateWindow(
            self.vp_wc.lpszClassName,
            self.title,
            vp_style,
            win32con.CW_USEDEFAULT,
            win32con.CW_USEDEFAULT,
            self.width,
            self.height,
            0,
            0,
            self.vp_wc.hInstance,
            None,
        )

        canvas_style = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_BORDER
        self.canvas_hwnd = win32gui.CreateWindow(
            self.canvas_wc.lpszClassName,
            "Canvas",
            canvas_style,
            0,
            0,
            self.canvas_width,
            self.canvas_height,
            self.hwnd,
            0,
            self.canvas_wc.hInstance,
            None,
        )

    def update_canvas_position(self):
        if self.canvas_hwnd:
            win32gui.SetWindowPos(
                self.canvas_hwnd,
                0,
                -self.scroll_x,
                -self.scroll_y,
                self.canvas_width,
                self.canvas_height,
                win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE,
            )

    def update_scrollbars(self, client_width, client_height):
        # Horizontal scrollbar
        max_scroll_x = max(0, self.canvas_width - client_width)
        self.scroll_x = max(0, min(self.scroll_x, max_scroll_x))
        si_h = (
            win32con.SIF_RANGE | win32con.SIF_PAGE | win32con.SIF_POS,
            0,
            max(0, self.canvas_width - 1),
            client_width,
            self.scroll_x,
            0,
        )
        win32gui.SetScrollInfo(self.hwnd, win32con.SB_HORZ, si_h, True)

        # Vertical scrollbar
        max_scroll_y = max(0, self.canvas_height - client_height)
        self.scroll_y = max(0, min(self.scroll_y, max_scroll_y))
        si_v = (
            win32con.SIF_RANGE | win32con.SIF_PAGE | win32con.SIF_POS,
            0,
            max(0, self.canvas_height - 1),
            client_height,
            self.scroll_y,
            0,
        )
        win32gui.SetScrollInfo(self.hwnd, win32con.SB_VERT, si_v, True)

        self.update_canvas_position()

    def handle_scroll(self, bar, wparam):
        si = win32gui.GetScrollInfo(self.hwnd, bar, win32con.SIF_ALL)
        n_min, n_max, n_page, n_pos, n_track_pos = si[1], si[2], si[3], si[4], si[5]
        max_pos = max(0, n_max - n_page + 1)

        scroll_code = win32api.LOWORD(wparam)
        step = 20

        if scroll_code == win32con.SB_LINEUP:
            new_pos = n_pos - step
        elif scroll_code == win32con.SB_LINEDOWN:
            new_pos = n_pos + step
        elif scroll_code == win32con.SB_PAGEUP:
            new_pos = n_pos - n_page
        elif scroll_code == win32con.SB_PAGEDOWN:
            new_pos = n_pos + n_page
        elif scroll_code in (win32con.SB_THUMBTRACK, win32con.SB_THUMBPOSITION):
            new_pos = n_track_pos
        elif scroll_code == win32con.SB_TOP:
            new_pos = n_min
        elif scroll_code == win32con.SB_BOTTOM:
            new_pos = max_pos
        else:
            return

        new_pos = max(n_min, min(new_pos, max_pos))
        if new_pos != n_pos:
            win32gui.SetScrollInfo(
                self.hwnd, bar, (win32con.SIF_POS, 0, 0, 0, new_pos, 0), True
            )
            if bar == win32con.SB_HORZ:
                self.scroll_x = new_pos
            else:
                self.scroll_y = new_pos
            self.update_canvas_position()

    def scroll_by_offset(self, bar, delta_pixels):
        si = win32gui.GetScrollInfo(self.hwnd, bar, win32con.SIF_ALL)
        n_min, n_max, n_page, n_pos = si[1], si[2], si[3], si[4]
        max_pos = max(0, n_max - n_page + 1)

        new_pos = max(n_min, min(n_pos + delta_pixels, max_pos))
        if new_pos != n_pos:
            win32gui.SetScrollInfo(
                self.hwnd, bar, (win32con.SIF_POS, 0, 0, 0, new_pos, 0), True
            )
            if bar == win32con.SB_HORZ:
                self.scroll_x = new_pos
            else:
                self.scroll_y = new_pos
            self.update_canvas_position()

    def viewport_wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_SIZE:
            client_width = win32api.LOWORD(lparam)
            client_height = win32api.HIWORD(lparam)
            self.update_scrollbars(client_width, client_height)
            return 0

        elif msg == win32con.WM_HSCROLL:
            self.handle_scroll(win32con.SB_HORZ, wparam)
            return 0

        elif msg == win32con.WM_VSCROLL:
            self.handle_scroll(win32con.SB_VERT, wparam)
            return 0

        elif msg == win32con.WM_MOUSEWHEEL:
            # Signed 16-bit wheel delta (120 per notch)
            raw_delta = win32api.HIWORD(wparam)
            if raw_delta >= 32768:
                raw_delta -= 65536
            notches = raw_delta / 120.0

            # Shift + Vertical Wheel scrolls horizontally
            fw_keys = win32api.LOWORD(wparam)
            if fw_keys & win32con.MK_SHIFT:
                self.scroll_by_offset(
                    win32con.SB_HORZ, -int(notches * self.wheel_step)
                )
            else:
                self.scroll_by_offset(
                    win32con.SB_VERT, -int(notches * self.wheel_step)
                )
            return 0

        elif msg == WM_MOUSEHWHEEL:
            # Horizontal tilt wheel / touchpad horizontal swipe (positive = right)
            raw_delta = win32api.HIWORD(wparam)
            if raw_delta >= 32768:
                raw_delta -= 65536
            notches = raw_delta / 120.0
            self.scroll_by_offset(
                win32con.SB_HORZ, int(notches * self.wheel_step)
            )
            return 0

        elif msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return 0

        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def canvas_wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_PAINT:
            hdc, ps = win32gui.BeginPaint(hwnd)
            # Draw grid lines so scrolling is clearly visible
            pen = win32gui.CreatePen(win32con.PS_SOLID, 1, win32api.RGB(220, 220, 220))
            old_pen = win32gui.SelectObject(hdc, pen)

            for x in range(0, self.canvas_width, 100):
                win32gui.MoveToEx(hdc, x, 0)
                win32gui.LineTo(hdc, x, self.canvas_height)
                win32gui.TextOut(hdc, x + 5, 5, f"X:{x}")

            for y in range(0, self.canvas_height, 100):
                win32gui.MoveToEx(hdc, 0, y)
                win32gui.LineTo(hdc, self.canvas_width, y)
                win32gui.TextOut(hdc, 5, y + 5, f"Y:{y}")

            win32gui.SelectObject(hdc, old_pen)
            win32gui.DeleteObject(pen)
            win32gui.EndPaint(hwnd, ps)
            return 0

        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def show(self):
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        win32gui.UpdateWindow(self.hwnd)
        win32gui.PumpMessages()


if __name__ == "__main__":
    app = ViewportWindow(
        title="Viewport & Canvas Window",
        width=800,
        height=600,
        canvas_width=2000,
        canvas_height=2000,
    )
    app.show()
