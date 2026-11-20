import subprocess
import sys


def ensure_dependencies():
    try:
        import win32api  # noqa: F401
        import win32con  # noqa: F401
        import win32gui  # noqa: F401
    except ImportError:
        print("Installing required dependency: pywin32...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pywin32"])


ensure_dependencies()

import win32api
import win32con
import win32gui

WM_MOUSEHWHEEL = 0x020E
VK_OEM_PLUS = 0xBB
VK_OEM_MINUS = 0xBD


class Canvas:

    def __init__(self, parent_hwnd, width=1600, height=1200):
        self.parent_hwnd = parent_hwnd
        self.base_width = width
        self.base_height = height
        self.width = width
        self.height = height
        self.zoom = 1.0
        self.hwnd = None

        self.wc = win32gui.WNDCLASS()
        self.wc.lpfnWndProc = self.wnd_proc
        self.wc.lpszClassName = "PythonWin32CanvasChildClass"
        self.wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        self.wc.hbrBackground = win32gui.GetStockObject(win32con.WHITE_BRUSH)

        try:
            win32gui.RegisterClass(self.wc)
        except win32gui.error:
            pass

        self.create_window()

    def create_window(self):
        style = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_BORDER
        self.hwnd = win32gui.CreateWindow(
            self.wc.lpszClassName,
            "",
            style,
            0,
            0,
            self.width,
            self.height,
            self.parent_hwnd,
            0,
            self.wc.hInstance,
            None,
        )

    def set_zoom(self, zoom):
        self.zoom = zoom
        self.width = max(1, int(round(self.base_width * self.zoom)))
        self.height = max(1, int(round(self.base_height * self.zoom)))
        win32gui.InvalidateRect(self.hwnd, None, True)

    def update_position(self, x, y):
        win32gui.SetWindowPos(
            self.hwnd,
            0,
            x,
            y,
            self.width,
            self.height,
            win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE,
        )

    def wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_PAINT:
            hdc, ps = win32gui.BeginPaint(hwnd)
            pen = win32gui.CreatePen(win32con.PS_SOLID, 1, win32api.RGB(220, 225, 230))
            old_pen = win32gui.SelectObject(hdc, pen)

            step = max(10, int(round(50 * self.zoom)))
            for gx in range(0, self.width, step):
                win32gui.MoveToEx(hdc, gx, 0)
                win32gui.LineTo(hdc, gx, self.height)
            for gy in range(0, self.height, step):
                win32gui.MoveToEx(hdc, 0, gy)
                win32gui.LineTo(hdc, self.width, gy)

            win32gui.SelectObject(hdc, old_pen)
            win32gui.DeleteObject(pen)
            win32gui.EndPaint(hwnd, ps)
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)


class ViewportWindow:

    def __init__(
        self,
        title="Viewport & Canvas Window",
        width=800,
        height=600,
        canvas_width=1600,
        canvas_height=1200,
    ):
        self.base_title = title
        self.width = width
        self.height = height
        self.client_width = width
        self.client_height = height
        self.scroll_x = 0
        self.scroll_y = 0
        self.zoom = 1.0
        self.min_zoom = 0.25
        self.max_zoom = 4.0
        self.zoom_step = 1.15
        self.hwnd = None
        self.canvas = None

        self.wc = win32gui.WNDCLASS()
        self.wc.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
        self.wc.lpfnWndProc = self.wnd_proc
        self.wc.lpszClassName = "ResizableViewportWindowClass"
        self.wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        self.wc.hbrBackground = win32con.COLOR_APPWORKSPACE + 1

        try:
            win32gui.RegisterClass(self.wc)
        except win32gui.error:
            pass

        self.create_window()
        self.canvas = Canvas(self.hwnd, width=canvas_width, height=canvas_height)
        self.update_title()

    def create_window(self):
        style = (
            win32con.WS_OVERLAPPEDWINDOW
            | win32con.WS_HSCROLL
            | win32con.WS_VSCROLL
            | win32con.WS_CLIPCHILDREN
        )
        self.hwnd = win32gui.CreateWindow(
            self.wc.lpszClassName,
            self.base_title,
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

    def update_title(self):
        if self.hwnd:
            pct = int(round(self.zoom * 100))
            win32gui.SetWindowText(self.hwnd, f"{self.base_title} ({pct}%)")

    def position_canvas(self):
        if self.canvas and self.canvas.hwnd:
            self.canvas.update_position(-self.scroll_x, -self.scroll_y)

    def apply_zoom(self, new_zoom, anchor_x=None, anchor_y=None):
        if not self.canvas:
            return

        new_zoom = max(self.min_zoom, min(self.max_zoom, new_zoom))
        if abs(new_zoom - self.zoom) < 1e-6:
            return

        if anchor_x is None:
            anchor_x = self.client_width // 2
        if anchor_y is None:
            anchor_y = self.client_height // 2

        canvas_x = (self.scroll_x + anchor_x) / self.zoom
        canvas_y = (self.scroll_y + anchor_y) / self.zoom

        self.zoom = new_zoom
        self.canvas.set_zoom(self.zoom)

        self.scroll_x = int(round(canvas_x * self.zoom - anchor_x))
        self.scroll_y = int(round(canvas_y * self.zoom - anchor_y))

        self.update_scrollbars()
        self.update_title()

    def update_scrollbars(self):
        if not self.canvas:
            return

        max_x = max(0, self.canvas.width - self.client_width)
        self.scroll_x = max(0, min(self.scroll_x, max_x))

        si_h = (
            win32con.SIF_RANGE | win32con.SIF_PAGE | win32con.SIF_POS,
            0,
            max(0, self.canvas.width - 1),
            self.client_width,
            self.scroll_x,
            0,
        )
        win32gui.SetScrollInfo(self.hwnd, win32con.SB_HORZ, si_h, True)

        max_y = max(0, self.canvas.height - self.client_height)
        self.scroll_y = max(0, min(self.scroll_y, max_y))

        si_v = (
            win32con.SIF_RANGE | win32con.SIF_PAGE | win32con.SIF_POS,
            0,
            max(0, self.canvas.height - 1),
            self.client_height,
            self.scroll_y,
            0,
        )
        win32gui.SetScrollInfo(self.hwnd, win32con.SB_VERT, si_v, True)

        self.position_canvas()

    def handle_scroll(self, bar, wparam):
        if not self.canvas:
            return

        scroll_type = win32api.LOWORD(wparam)
        is_horz = bar == win32con.SB_HORZ

        current_pos = self.scroll_x if is_horz else self.scroll_y
        page_size = self.client_width if is_horz else self.client_height
        content_size = self.canvas.width if is_horz else self.canvas.height
        max_pos = max(0, content_size - page_size)
        line_step = 20

        if scroll_type == win32con.SB_LINELEFT:  # Also SB_LINEUP
            new_pos = current_pos - line_step
        elif scroll_type == win32con.SB_LINERIGHT:  # Also SB_LINEDOWN
            new_pos = current_pos + line_step
        elif scroll_type == win32con.SB_PAGELEFT:  # Also SB_PAGEUP
            new_pos = current_pos - page_size
        elif scroll_type == win32con.SB_PAGERIGHT:  # Also SB_PAGEDOWN
            new_pos = current_pos + page_size
        elif scroll_type in (win32con.SB_THUMBTRACK, win32con.SB_THUMBPOSITION):
            si = win32gui.GetScrollInfo(self.hwnd, bar, win32con.SIF_TRACKPOS)
            new_pos = si[5]
        elif scroll_type == win32con.SB_TOP:  # Also SB_LEFT
            new_pos = 0
        elif scroll_type == win32con.SB_BOTTOM:  # Also SB_RIGHT
            new_pos = max_pos
        else:
            return

        new_pos = max(0, min(new_pos, max_pos))
        if new_pos != current_pos:
            if is_horz:
                self.scroll_x = new_pos
            else:
                self.scroll_y = new_pos

            si = (win32con.SIF_POS, 0, 0, 0, new_pos, 0)
            win32gui.SetScrollInfo(self.hwnd, bar, si, True)
            self.position_canvas()

    def scroll_by(self, bar, delta_pixels):
        if not self.canvas:
            return

        is_horz = bar == win32con.SB_HORZ
        current_pos = self.scroll_x if is_horz else self.scroll_y
        page_size = self.client_width if is_horz else self.client_height
        content_size = self.canvas.width if is_horz else self.canvas.height
        max_pos = max(0, content_size - page_size)

        new_pos = max(0, min(current_pos + delta_pixels, max_pos))
        if new_pos != current_pos:
            if is_horz:
                self.scroll_x = new_pos
            else:
                self.scroll_y = new_pos

            si = (win32con.SIF_POS, 0, 0, 0, new_pos, 0)
            win32gui.SetScrollInfo(self.hwnd, bar, si, True)
            self.position_canvas()

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
        elif msg == win32con.WM_KEYDOWN:
            ctrl_pressed = (win32api.GetKeyState(win32con.VK_CONTROL) & 0x8000) != 0
            if ctrl_pressed:
                if wparam in (VK_OEM_PLUS, win32con.VK_ADD):
                    self.apply_zoom(self.zoom * self.zoom_step)
                    return 0
                elif wparam in (VK_OEM_MINUS, win32con.VK_SUBTRACT):
                    self.apply_zoom(self.zoom / self.zoom_step)
                    return 0
                elif wparam in (ord("0"), win32con.VK_NUMPAD0):
                    self.apply_zoom(1.0)
                    return 0
        elif msg == win32con.WM_MOUSEWHEEL:
            fw_keys = win32api.LOWORD(wparam)
            z_delta = win32api.HIWORD(wparam)
            if z_delta >= 0x8000:
                z_delta -= 0x10000

            if fw_keys & win32con.MK_CONTROL:
                screen_x = win32api.LOWORD(lparam)
                screen_y = win32api.HIWORD(lparam)
                if screen_x >= 0x8000:
                    screen_x -= 0x10000
                if screen_y >= 0x8000:
                    screen_y -= 0x10000
                client_x, client_y = win32gui.ScreenToClient(hwnd, (screen_x, screen_y))

                steps = z_delta / 120.0
                factor = self.zoom_step ** steps
                self.apply_zoom(self.zoom * factor, client_x, client_y)
                return 0

            scroll_lines = 3
            line_step = 20
            delta_pixels = -int((z_delta / 120.0) * scroll_lines * line_step)

            if fw_keys & win32con.MK_SHIFT:
                self.scroll_by(win32con.SB_HORZ, delta_pixels)
            else:
                self.scroll_by(win32con.SB_VERT, delta_pixels)
            return 0
        elif msg == WM_MOUSEHWHEEL:
            z_delta = win32api.HIWORD(wparam)
            if z_delta >= 0x8000:
                z_delta -= 0x10000

            scroll_lines = 3
            line_step = 20
            delta_pixels = int((z_delta / 120.0) * scroll_lines * line_step)
            self.scroll_by(win32con.SB_HORZ, delta_pixels)
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
    app = ViewportWindow(
        title="Viewport & Canvas Window",
        width=640,
        height=480,
        canvas_width=1600,
        canvas_height=1200,
    )
    app.show()
