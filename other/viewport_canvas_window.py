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

        self.hwnd = None
        self.canvas_hwnd = None

        self.scroll_x = 0
        self.scroll_y = 0
        self.line_step = 20

        # Register Viewport window class
        self.wc_viewport = win32gui.WNDCLASS()
        self.wc_viewport.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
        self.wc_viewport.lpfnWndProc = self.viewport_wnd_proc
        self.wc_viewport.lpszClassName = "ViewportWindowClass"
        self.wc_viewport.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        self.wc_viewport.hbrBackground = win32con.COLOR_APPWORKSPACE + 1
        win32gui.RegisterClass(self.wc_viewport)

        # Register Canvas child window class
        self.wc_canvas = win32gui.WNDCLASS()
        self.wc_canvas.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
        self.wc_canvas.lpfnWndProc = self.canvas_wnd_proc
        self.wc_canvas.lpszClassName = "CanvasChildWindowClass"
        self.wc_canvas.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        self.wc_canvas.hbrBackground = win32con.COLOR_WINDOW + 1
        win32gui.RegisterClass(self.wc_canvas)

        self.create_windows()

    def create_windows(self):
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
            self.wc_viewport.hInstance,
            None,
        )

        canvas_style = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_BORDER
        self.canvas_hwnd = win32gui.CreateWindow(
            self.wc_canvas.lpszClassName,
            "Canvas",
            canvas_style,
            0,
            0,
            self.canvas_width,
            self.canvas_height,
            self.hwnd,
            0,
            self.wc_canvas.hInstance,
            None,
        )

        self.update_scrollbars()

    def update_scrollbars(self):
        if not self.hwnd:
            return

        _, _, client_w, client_h = win32gui.GetClientRect(self.hwnd)

        max_x = max(0, self.canvas_width - client_w)
        max_y = max(0, self.canvas_height - client_h)

        self.scroll_x = max(0, min(self.scroll_x, max_x))
        self.scroll_y = max(0, min(self.scroll_y, max_y))

        # Horizontal scrollbar info: (fMask, nMin, nMax, nPage, nPos, nTrackPos)
        h_mask = win32con.SIF_RANGE | win32con.SIF_PAGE | win32con.SIF_POS
        h_si = (h_mask, 0, max(0, self.canvas_width - 1), client_w, self.scroll_x, 0)
        win32gui.SetScrollInfo(self.hwnd, win32con.SB_HORZ, h_si, True)

        # Vertical scrollbar info: (fMask, nMin, nMax, nPage, nPos, nTrackPos)
        v_mask = win32con.SIF_RANGE | win32con.SIF_PAGE | win32con.SIF_POS
        v_si = (v_mask, 0, max(0, self.canvas_height - 1), client_h, self.scroll_y, 0)
        win32gui.SetScrollInfo(self.hwnd, win32con.SB_VERT, v_si, True)

        self.position_canvas()

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

    def handle_scroll(self, bar, wparam):
        action = win32api.LOWORD(wparam)
        si = win32gui.GetScrollInfo(self.hwnd, bar)
        # si tuple: (fMask, nMin, nMax, nPage, nPos, nTrackPos)
        n_min, n_max, n_page, n_pos, n_track = si[1], si[2], si[3], si[4], si[5]
        max_pos = max(0, n_max - n_page + 1)

        if action == win32con.SB_LINEUP:
            new_pos = n_pos - self.line_step
        elif action == win32con.SB_LINEDOWN:
            new_pos = n_pos + self.line_step
        elif action == win32con.SB_PAGEUP:
            new_pos = n_pos - n_page
        elif action == win32con.SB_PAGEDOWN:
            new_pos = n_pos + n_page
        elif action in (win32con.SB_THUMBTRACK, win32con.SB_THUMBPOSITION):
            new_pos = n_track
        elif action == win32con.SB_TOP:
            new_pos = n_min
        elif action == win32con.SB_BOTTOM:
            new_pos = max_pos
        else:
            return

        new_pos = max(0, min(new_pos, max_pos))
        if new_pos == n_pos:
            return

        if bar == win32con.SB_HORZ:
            self.scroll_x = new_pos
        else:
            self.scroll_y = new_pos

        win32gui.SetScrollInfo(
            self.hwnd,
            bar,
            (win32con.SIF_POS, 0, 0, 0, new_pos, 0),
            True,
        )
        self.position_canvas()

    def handle_mousewheel(self, wparam):
        # High word of wParam holds signed wheel delta (120 per notch)
        raw_delta = win32api.HIWORD(wparam)
        if raw_delta >= 0x8000:
            raw_delta -= 0x10000

        notches = raw_delta / 120.0
        delta_y = int(-notches * self.line_step * 3)

        si = win32gui.GetScrollInfo(self.hwnd, win32con.SB_VERT)
        n_max, n_page, n_pos = si[2], si[3], si[4]
        max_pos = max(0, n_max - n_page + 1)

        new_pos = max(0, min(n_pos + delta_y, max_pos))
        if new_pos != n_pos:
            self.scroll_y = new_pos
            win32gui.SetScrollInfo(
                self.hwnd,
                win32con.SB_VERT,
                (win32con.SIF_POS, 0, 0, 0, new_pos, 0),
                True,
            )
            self.position_canvas()

    def viewport_wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_SIZE:
            self.update_scrollbars()
            return 0
        elif msg == win32con.WM_HSCROLL:
            self.handle_scroll(win32con.SB_HORZ, wparam)
            return 0
        elif msg == win32con.WM_VSCROLL:
            self.handle_scroll(win32con.SB_VERT, wparam)
            return 0
        elif msg == win32con.WM_MOUSEWHEEL:
            self.handle_mousewheel(wparam)
            return 0
        elif msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def canvas_wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_PAINT:
            hdc, ps = win32gui.BeginPaint(hwnd)
            # Draw coordinate markers on the canvas to visualize scrolling
            for y in range(0, self.canvas_height, 100):
                for x in range(0, self.canvas_width, 200):
                    win32gui.TextOut(hdc, x + 10, y + 10, f"({x}, {y})")
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
