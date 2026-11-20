import subprocess
import sys


def ensure_dependencies():
    try:
        import win32api  # noqa: F401
        import win32con  # noqa: F401
        import win32gui  # noqa: F401
    except ImportError:
        print("pywin32 not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pywin32"])


ensure_dependencies()

import win32api
import win32con
import win32gui

WM_MOUSEHWHEEL = 0x020E
MK_CONTROL = 0x0008
MK_SHIFT = 0x0004


class ViewportWindow:

    def __init__(
        self,
        title="Viewport Window",
        width=800,
        height=600,
        canvas_width=1600,
        canvas_height=1200,
    ):
        self.title = title
        self.width = width
        self.height = height

        # Base (unscaled) canvas dimensions
        self.base_canvas_width = canvas_width
        self.base_canvas_height = canvas_height

        # Zoom parameters
        self.zoom = 1.0
        self.min_zoom = 0.25
        self.max_zoom = 4.0
        self.zoom_step = 0.1

        # Current scaled canvas dimensions
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height

        self.client_width = 0
        self.client_height = 0
        self.scroll_x = 0
        self.scroll_y = 0

        self.hwnd = None
        self.canvas_hwnd = None

        self.register_classes()
        self.create_windows()

    def register_classes(self):
        hinst = win32api.GetModuleHandle(None)

        # Register Viewport Window Class
        self.wc_viewport = win32gui.WNDCLASS()
        self.wc_viewport.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
        self.wc_viewport.lpfnWndProc = self.viewport_wnd_proc
        self.wc_viewport.hInstance = hinst
        self.wc_viewport.lpszClassName = "PythonWin32ViewportClass"
        self.wc_viewport.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        self.wc_viewport.hbrBackground = win32con.COLOR_APPWORKSPACE + 1
        win32gui.RegisterClass(self.wc_viewport)

        # Register Canvas Child Window Class
        self.wc_canvas = win32gui.WNDCLASS()
        self.wc_canvas.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
        self.wc_canvas.lpfnWndProc = self.canvas_wnd_proc
        self.wc_canvas.hInstance = hinst
        self.wc_canvas.lpszClassName = "PythonWin32CanvasClass"
        self.wc_canvas.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        self.wc_canvas.hbrBackground = win32con.COLOR_WINDOW + 1
        win32gui.RegisterClass(self.wc_canvas)

    def create_windows(self):
        hinst = win32api.GetModuleHandle(None)

        # Create the Viewport (parent) window
        viewport_style = (
            win32con.WS_OVERLAPPEDWINDOW
            | win32con.WS_HSCROLL
            | win32con.WS_VSCROLL
            | win32con.WS_CLIPCHILDREN
        )
        self.hwnd = win32gui.CreateWindow(
            self.wc_viewport.lpszClassName,
            self.title,
            viewport_style,
            win32con.CW_USEDEFAULT,
            win32con.CW_USEDEFAULT,
            self.width,
            self.height,
            0,
            0,
            hinst,
            None,
        )

        # Create the Canvas (child) window positioned underneath the viewport
        canvas_style = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_BORDER
        self.canvas_hwnd = win32gui.CreateWindow(
            self.wc_canvas.lpszClassName,
            "",
            canvas_style,
            0,
            0,
            self.canvas_width,
            self.canvas_height,
            self.hwnd,
            0,
            hinst,
            None,
        )

    def position_canvas(self):
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
            win32gui.InvalidateRect(self.canvas_hwnd, None, True)

    def update_title(self):
        if self.hwnd:
            zoom_pct = int(round(self.zoom * 100))
            win32gui.SetWindowText(self.hwnd, f"{self.title} ({zoom_pct}%)")

    def update_scrollbars(self):
        if not self.hwnd:
            return

        # Horizontal scrollbar
        max_scroll_x = max(0, self.canvas_width - self.client_width)
        self.scroll_x = max(0, min(self.scroll_x, max_scroll_x))
        si_h = (
            win32con.SIF_RANGE | win32con.SIF_PAGE | win32con.SIF_POS,
            0,
            max(0, self.canvas_width - 1),
            self.client_width,
            self.scroll_x,
            0,
        )
        win32gui.SetScrollInfo(self.hwnd, win32con.SB_HORZ, si_h, True)

        # Vertical scrollbar
        max_scroll_y = max(0, self.canvas_height - self.client_height)
        self.scroll_y = max(0, min(self.scroll_y, max_scroll_y))
        si_v = (
            win32con.SIF_RANGE | win32con.SIF_PAGE | win32con.SIF_POS,
            0,
            max(0, self.canvas_height - 1),
            self.client_height,
            self.scroll_y,
            0,
        )
        win32gui.SetScrollInfo(self.hwnd, win32con.SB_VERT, si_v, True)

        self.position_canvas()

    def set_scroll_pos(self, bar, new_pos):
        if bar == win32con.SB_HORZ:
            max_scroll = max(0, self.canvas_width - self.client_width)
            clamped = max(0, min(new_pos, max_scroll))
            if clamped != self.scroll_x:
                self.scroll_x = clamped
                si = (win32con.SIF_POS, 0, 0, 0, self.scroll_x, 0)
                win32gui.SetScrollInfo(self.hwnd, win32con.SB_HORZ, si, True)
                self.position_canvas()
        else:
            max_scroll = max(0, self.canvas_height - self.client_height)
            clamped = max(0, min(new_pos, max_scroll))
            if clamped != self.scroll_y:
                self.scroll_y = clamped
                si = (win32con.SIF_POS, 0, 0, 0, self.scroll_y, 0)
                win32gui.SetScrollInfo(self.hwnd, win32con.SB_VERT, si, True)
                self.position_canvas()

    def apply_zoom(self, delta, screen_x, screen_y):
        # Convert cursor screen coordinates to viewport client coordinates
        cursor_x, cursor_y = win32gui.ScreenToClient(self.hwnd, (screen_x, screen_y))

        # Canvas point currently under the cursor in unscaled (world) coordinates
        world_x = (self.scroll_x + cursor_x) / self.zoom
        world_y = (self.scroll_y + cursor_y) / self.zoom

        steps = delta / 120.0
        new_zoom = self.zoom + (steps * self.zoom_step)
        new_zoom = max(self.min_zoom, min(new_zoom, self.max_zoom))
        new_zoom = round(new_zoom, 2)

        if new_zoom == self.zoom:
            return

        self.zoom = new_zoom
        self.canvas_width = max(1, int(round(self.base_canvas_width * self.zoom)))
        self.canvas_height = max(1, int(round(self.base_canvas_height * self.zoom)))

        # Adjust scroll offsets so the point under the cursor stays anchored
        self.scroll_x = int(round(world_x * self.zoom - cursor_x))
        self.scroll_y = int(round(world_y * self.zoom - cursor_y))

        self.update_scrollbars()
        self.update_title()

    def handle_scroll(self, bar, wparam):
        scroll_code = win32api.LOWORD(wparam)
        si = win32gui.GetScrollInfo(self.hwnd, bar)
        pos = si[4]
        page = si[3]
        max_pos = si[2]
        track_pos = si[5]

        step = 20

        if scroll_code == win32con.SB_LINEUP:
            pos -= step
        elif scroll_code == win32con.SB_LINEDOWN:
            pos += step
        elif scroll_code == win32con.SB_PAGEUP:
            pos -= page
        elif scroll_code == win32con.SB_PAGEDOWN:
            pos += page
        elif scroll_code in (win32con.SB_THUMBTRACK, win32con.SB_THUMBPOSITION):
            pos = track_pos
        elif scroll_code == win32con.SB_TOP:
            pos = 0
        elif scroll_code == win32con.SB_BOTTOM:
            pos = max_pos

        self.set_scroll_pos(bar, pos)

    def handle_mousewheel(self, wparam, lparam, is_horizontal=False):
        delta = win32api.HIWORD(wparam)
        if delta >= 32768:
            delta -= 65536

        key_state = win32api.LOWORD(wparam)

        # Ctrl + Wheel triggers cursor-anchored zooming
        if not is_horizontal and (key_state & MK_CONTROL):
            screen_x = win32api.LOWORD(lparam)
            if screen_x >= 32768:
                screen_x -= 65536
            screen_y = win32api.HIWORD(lparam)
            if screen_y >= 32768:
                screen_y -= 65536
            self.apply_zoom(delta, screen_x, screen_y)
            return

        scroll_step = 60
        steps = delta / 120.0

        if is_horizontal or (key_state & MK_SHIFT):
            # Positive delta on WM_MOUSEHWHEEL scrolls right; Shift+Wheel up scrolls left
            direction = 1 if is_horizontal else -1
            offset = int(direction * steps * scroll_step)
            self.set_scroll_pos(win32con.SB_HORZ, self.scroll_x + offset)
        else:
            # Positive delta scrolls up (decreases scroll_y)
            offset = int(-steps * scroll_step)
            self.set_scroll_pos(win32con.SB_VERT, self.scroll_y + offset)

    def viewport_wnd_proc(self, hwnd, msg, wparam, lparam):
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
        elif msg == win32con.WM_MOUSEWHEEL:
            self.handle_mousewheel(wparam, lparam, is_horizontal=False)
            return 0
        elif msg == WM_MOUSEHWHEEL:
            self.handle_mousewheel(wparam, lparam, is_horizontal=True)
            return 0
        elif msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return 0

        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def canvas_wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_PAINT:
            hdc, ps = win32gui.BeginPaint(hwnd)

            # Draw a scaled grid on the canvas so zoom and scroll are clearly visible
            grid_size = max(8, int(round(100 * self.zoom)))
            pen = win32gui.CreatePen(win32con.PS_SOLID, 1, win32api.RGB(220, 225, 235))
            old_pen = win32gui.SelectObject(hdc, pen)

            for x in range(0, self.canvas_width + 1, grid_size):
                win32gui.MoveToEx(hdc, x, 0)
                win32gui.LineTo(hdc, x, self.canvas_height)

            for y in range(0, self.canvas_height + 1, grid_size):
                win32gui.MoveToEx(hdc, 0, y)
                win32gui.LineTo(hdc, self.canvas_width, y)

            win32gui.SelectObject(hdc, old_pen)
            win32gui.DeleteObject(pen)

            # Draw a scaled reference rectangle and zoom label
            rect_left = int(round(100 * self.zoom))
            rect_top = int(round(100 * self.zoom))
            rect_right = int(round(400 * self.zoom))
            rect_bottom = int(round(300 * self.zoom))
            win32gui.Rectangle(hdc, rect_left, rect_top, rect_right, rect_bottom)

            zoom_pct = int(round(self.zoom * 100))
            win32gui.DrawText(
                hdc,
                f"Canvas Zoom: {zoom_pct}% ({self.canvas_width}x{self.canvas_height})",
                -1,
                (10, 10, self.canvas_width, 60),
                win32con.DT_LEFT | win32con.DT_TOP | win32con.DT_SINGLELINE,
            )

            win32gui.EndPaint(hwnd, ps)
            return 0

        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def show(self):
        self.update_title()
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        win32gui.UpdateWindow(self.hwnd)
        win32gui.PumpMessages()


if __name__ == "__main__":
    app = ViewportWindow(
        title="Viewport & Canvas App",
        width=800,
        height=600,
        canvas_width=1600,
        canvas_height=1200,
    )
    app.show()
