import subprocess
import sys


def ensure_dependencies():
    try:
        import win32api  # noqa: F401
        import win32con  # noqa: F401
        import win32gui  # noqa: F401
        import win32print  # noqa: F401
    except ImportError:
        print("pywin32 not found. Installing via pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pywin32"])


ensure_dependencies()

import ctypes
import win32api
import win32con
import win32gui
import win32print

WM_MOUSEHWHEEL = 0x020E
LOGPIXELSY = 90


class CanvasControl:

    def __init__(self, hwnd, ctrl_id, class_name, text, x, y, width, height, font_pt=10):
        self.hwnd = hwnd
        self.ctrl_id = ctrl_id
        self.class_name = class_name
        self.text = text
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.font_pt = font_pt
        self.hfont = None


class ViewportWindow:

    def __init__(
        self,
        title="Viewport & Canvas Window",
        width=800,
        height=600,
        canvas_width=2000,
        canvas_height=1500,
    ):
        self.base_title = title
        self.width = width
        self.height = height
        self.client_width = 0
        self.client_height = 0

        # Base (100%) canvas dimensions and zoom state
        self.base_canvas_width = canvas_width
        self.base_canvas_height = canvas_height
        self.zoom = 1.0
        self.min_zoom = 0.25
        self.max_zoom = 4.0
        self.zoom_step = 0.1

        self.canvas_width = canvas_width
        self.canvas_height = canvas_height

        # Current scroll offsets
        self.scroll_x = 0
        self.scroll_y = 0

        self.hwnd = None
        self.canvas_hwnd = None

        # Child controls hosted inside the canvas
        self.controls = {}
        self.next_control_id = 1001

        # Register the Viewport window class
        self.wc = win32gui.WNDCLASS()
        self.wc.lpfnWndProc = self.wnd_proc
        self.wc.lpszClassName = "ViewportWindowClass"
        self.wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        self.wc.hbrBackground = win32con.COLOR_APPWORKSPACE + 1
        self.wc.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
        win32gui.RegisterClass(self.wc)

        # Register the Canvas window class
        self.canvas_wc = win32gui.WNDCLASS()
        self.canvas_wc.lpfnWndProc = self.canvas_wnd_proc
        self.canvas_wc.lpszClassName = "CanvasChildClass"
        self.canvas_wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        self.canvas_wc.hbrBackground = win32con.COLOR_WINDOW + 1
        self.canvas_wc.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
        win32gui.RegisterClass(self.canvas_wc)

        self.create_window()
        self.create_default_controls()
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

        # Create the larger Canvas child window inside the Viewport
        canvas_style = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_BORDER | win32con.WS_CLIPCHILDREN
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

    def add_control(
        self,
        class_name,
        text,
        x,
        y,
        width,
        height,
        style=0,
        ex_style=0,
        font_pt=10,
        on_command=None,
    ):
        ctrl_id = self.next_control_id
        self.next_control_id += 1

        full_style = win32con.WS_CHILD | win32con.WS_VISIBLE | style
        scaled_x = int(round(x * self.zoom))
        scaled_y = int(round(y * self.zoom))
        scaled_w = max(1, int(round(width * self.zoom)))
        scaled_h = max(1, int(round(height * self.zoom)))

        ctrl_hwnd = win32gui.CreateWindowEx(
            ex_style,
            class_name,
            text,
            full_style,
            scaled_x,
            scaled_y,
            scaled_w,
            scaled_h,
            self.canvas_hwnd,
            ctrl_id,
            self.canvas_wc.hInstance,
            None,
        )

        ctrl = CanvasControl(ctrl_hwnd, ctrl_id, class_name, text, x, y, width, height, font_pt)
        ctrl.on_command = on_command
        self.apply_control_font(ctrl)
        self.controls[ctrl_id] = ctrl
        return ctrl

    def apply_control_font(self, ctrl):
        hdc = win32gui.GetDC(ctrl.hwnd)
        dpi_y = win32print.GetDeviceCaps(hdc, LOGPIXELSY)
        win32gui.ReleaseDC(ctrl.hwnd, hdc)

        scaled_pt = max(4, ctrl.font_pt * self.zoom)
        lf = win32gui.LOGFONT()
        lf.lfHeight = -int(round(scaled_pt * dpi_y / 72.0))
        lf.lfFaceName = "Segoe UI"

        new_font = win32gui.CreateFontIndirect(lf)
        win32gui.SendMessage(ctrl.hwnd, win32con.WM_SETFONT, new_font, 1)

        if ctrl.hfont:
            win32gui.DeleteObject(ctrl.hfont)
        ctrl.hfont = new_font

    def layout_controls(self):
        for ctrl in self.controls.values():
            sx = int(round(ctrl.x * self.zoom))
            sy = int(round(ctrl.y * self.zoom))
            sw = max(1, int(round(ctrl.width * self.zoom)))
            sh = max(1, int(round(ctrl.height * self.zoom)))
            win32gui.SetWindowPos(
                ctrl.hwnd,
                0,
                sx,
                sy,
                sw,
                sh,
                win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE,
            )
            self.apply_control_font(ctrl)

    def create_default_controls(self):
        self.add_control(
            "STATIC",
            "Canvas Controls (Zoom with Ctrl+Wheel or Ctrl + / - / 0):",
            40,
            40,
            420,
            24,
            font_pt=10,
        )

        edit_ctrl = self.add_control(
            "EDIT",
            "Type inside canvas...",
            40,
            75,
            260,
            28,
            style=win32con.ES_AUTOHSCROLL | win32con.WS_TABSTOP,
            ex_style=win32con.WS_EX_CLIENTEDGE,
            font_pt=10,
        )

        status_ctrl = self.add_control(
            "STATIC",
            "Ready.",
            40,
            160,
            380,
            24,
            font_pt=10,
        )

        def on_button_click():
            current_text = win32gui.GetWindowText(edit_ctrl.hwnd)
            win32gui.SetWindowText(status_ctrl.hwnd, f"Submitted: {current_text}")

        self.add_control(
            "BUTTON",
            "Submit",
            315,
            75,
            100,
            28,
            style=win32con.BS_PUSHBUTTON | win32con.WS_TABSTOP,
            font_pt=10,
            on_command=on_button_click,
        )

        listbox_ctrl = self.add_control(
            "LISTBOX",
            "",
            40,
            200,
            260,
            130,
            style=win32con.LBS_NOTIFY | win32con.WS_VSCROLL | win32con.WS_TABSTOP,
            ex_style=win32con.WS_EX_CLIENTEDGE,
            font_pt=10,
        )
        for item in ["Node A (x=40, y=200)", "Node B", "Node C", "Node D", "Node E"]:
            win32gui.SendMessage(listbox_ctrl.hwnd, win32con.LB_ADDSTRING, 0, item)

        self.add_control(
            "BUTTON",
            "Reset Zoom (100%)",
            40,
            350,
            160,
            32,
            style=win32con.BS_PUSHBUTTON | win32con.WS_TABSTOP,
            font_pt=10,
            on_command=lambda: self.set_zoom(1.0),
        )

    def update_title(self):
        if self.hwnd:
            pct = int(round(self.zoom * 100))
            win32gui.SetWindowText(self.hwnd, f"{self.base_title} ({pct}%)")

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

    def update_scrollbars(self):
        # Horizontal scrollbar
        max_h = max(0, self.canvas_width - self.client_width)
        self.scroll_x = max(0, min(self.scroll_x, max_h))
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
        max_v = max(0, self.canvas_height - self.client_height)
        self.scroll_y = max(0, min(self.scroll_y, max_v))
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

    def set_zoom(self, new_zoom, anchor_x=None, anchor_y=None):
        new_zoom = max(self.min_zoom, min(self.max_zoom, round(new_zoom, 2)))
        if new_zoom == self.zoom:
            return

        if anchor_x is None:
            anchor_x = self.client_width // 2
        if anchor_y is None:
            anchor_y = self.client_height // 2

        # Canvas coordinates under the anchor point prior to zoom
        canvas_pt_x = (self.scroll_x + anchor_x) / self.zoom
        canvas_pt_y = (self.scroll_y + anchor_y) / self.zoom

        self.zoom = new_zoom
        self.canvas_width = max(1, int(round(self.base_canvas_width * self.zoom)))
        self.canvas_height = max(1, int(round(self.base_canvas_height * self.zoom)))

        # Keep the same canvas point under the anchor point
        self.scroll_x = int(round(canvas_pt_x * self.zoom - anchor_x))
        self.scroll_y = int(round(canvas_pt_y * self.zoom - anchor_y))

        self.layout_controls()
        self.update_scrollbars()
        self.update_title()
        if self.canvas_hwnd:
            win32gui.InvalidateRect(self.canvas_hwnd, None, True)

    def handle_scroll(self, bar, wparam):
        sb_code = win32api.LOWORD(wparam)
        si = win32gui.GetScrollInfo(self.hwnd, bar)
        pos = si[4]
        page = si[3]
        max_pos = max(0, si[2] - max(0, page - 1))
        step = 20

        if sb_code == win32con.SB_LINEUP:
            pos -= step
        elif sb_code == win32con.SB_LINEDOWN:
            pos += step
        elif sb_code == win32con.SB_PAGEUP:
            pos -= page
        elif sb_code == win32con.SB_PAGEDOWN:
            pos += page
        elif sb_code == win32con.SB_THUMBTRACK:
            pos = si[5]
        elif sb_code == win32con.SB_TOP:
            pos = 0
        elif sb_code == win32con.SB_BOTTOM:
            pos = max_pos

        pos = max(0, min(pos, max_pos))

        if bar == win32con.SB_HORZ:
            if pos != self.scroll_x:
                self.scroll_x = pos
                win32gui.SetScrollInfo(self.hwnd, bar, (win32con.SIF_POS, 0, 0, 0, pos, 0), True)
                self.position_canvas()
        else:
            if pos != self.scroll_y:
                self.scroll_y = pos
                win32gui.SetScrollInfo(self.hwnd, bar, (win32con.SIF_POS, 0, 0, 0, pos, 0), True)
                self.position_canvas()

    def scroll_by(self, dx=0, dy=0):
        if dx != 0:
            si_h = win32gui.GetScrollInfo(self.hwnd, win32con.SB_HORZ)
            max_h = max(0, si_h[2] - max(0, si_h[3] - 1))
            new_x = max(0, min(self.scroll_x + dx, max_h))
            if new_x != self.scroll_x:
                self.scroll_x = new_x
                win32gui.SetScrollInfo(
                    self.hwnd, win32con.SB_HORZ, (win32con.SIF_POS, 0, 0, 0, new_x, 0), True
                )
                self.position_canvas()

        if dy != 0:
            si_v = win32gui.GetScrollInfo(self.hwnd, win32con.SB_VERT)
            max_v = max(0, si_v[2] - max(0, si_v[3] - 1))
            new_y = max(0, min(self.scroll_y + dy, max_v))
            if new_y != self.scroll_y:
                self.scroll_y = new_y
                win32gui.SetScrollInfo(
                    self.hwnd, win32con.SB_VERT, (win32con.SIF_POS, 0, 0, 0, new_y, 0), True
                )
                self.position_canvas()

    def handle_zoom_shortcut(self, vk):
        if vk in (win32con.VK_OEM_PLUS, win32con.VK_ADD):
            self.set_zoom(self.zoom + self.zoom_step)
            return True
        if vk in (win32con.VK_OEM_MINUS, win32con.VK_SUBTRACT):
            self.set_zoom(self.zoom - self.zoom_step)
            return True
        if vk in (ord("0"), win32con.VK_NUMPAD0):
            self.set_zoom(1.0)
            return True
        return False

    def canvas_wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_COMMAND:
            ctrl_id = win32api.LOWORD(wparam)
            notify_code = win32api.HIWORD(wparam)
            ctrl = self.controls.get(ctrl_id)
            if ctrl and ctrl.on_command and notify_code == win32con.BN_CLICKED:
                ctrl.on_command()
                return 0
        elif msg == win32con.WM_PAINT:
            hdc, ps = win32gui.BeginPaint(hwnd)
            pen = win32gui.CreatePen(win32con.PS_SOLID, 1, win32api.RGB(220, 225, 232))
            old_pen = win32gui.SelectObject(hdc, pen)

            grid_step = max(10, int(round(100 * self.zoom)))
            for x in range(0, self.canvas_width, grid_step):
                win32gui.MoveToEx(hdc, x, 0)
                win32gui.LineTo(hdc, x, self.canvas_height)
            for y in range(0, self.canvas_height, grid_step):
                win32gui.MoveToEx(hdc, 0, y)
                win32gui.LineTo(hdc, self.canvas_width, y)

            win32gui.SelectObject(hdc, old_pen)
            win32gui.DeleteObject(pen)
            win32gui.EndPaint(hwnd, ps)
            return 0
        elif msg == win32con.WM_MOUSEWHEEL:
            return self.wnd_proc(self.hwnd, msg, wparam, lparam)
        elif msg == WM_MOUSEHWHEEL:
            return self.wnd_proc(self.hwnd, msg, wparam, lparam)
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_SIZE:
            self.client_width = win32api.LOWORD(lparam)
            self.client_height = win32api.HIWORD(lparam)
            self.update_scrollbars()
            return 0
        elif msg == win32con.WM_KEYDOWN:
            ctrl_pressed = (win32api.GetKeyState(win32con.VK_CONTROL) & 0x8000) != 0
            if ctrl_pressed and self.handle_zoom_shortcut(wparam):
                return 0
        elif msg == win32con.WM_HSCROLL:
            self.handle_scroll(win32con.SB_HORZ, wparam)
            return 0
        elif msg == win32con.WM_VSCROLL:
            self.handle_scroll(win32con.SB_VERT, wparam)
            return 0
        elif msg == win32con.WM_MOUSEWHEEL:
            delta = ctypes.c_short(win32api.HIWORD(wparam)).value
            key_state = win32api.LOWORD(wparam)
            notches = delta / 120.0

            if key_state & win32con.MK_CONTROL:
                screen_x = ctypes.c_short(win32api.LOWORD(lparam)).value
                screen_y = ctypes.c_short(win32api.HIWORD(lparam)).value
                client_x, client_y = win32gui.ScreenToClient(self.hwnd, (screen_x, screen_y))
                self.set_zoom(self.zoom + notches * self.zoom_step, client_x, client_y)
                return 0

            scroll_amount = int(-notches * 60)
            if key_state & win32con.MK_SHIFT:
                self.scroll_by(dx=scroll_amount)
            else:
                self.scroll_by(dy=scroll_amount)
            return 0
        elif msg == WM_MOUSEHWHEEL:
            delta = ctypes.c_short(win32api.HIWORD(wparam)).value
            scroll_amount = int((delta / 120.0) * 60)
            self.scroll_by(dx=scroll_amount)
            return 0
        elif msg == win32con.WM_DESTROY:
            for ctrl in self.controls.values():
                if ctrl.hfont:
                    win32gui.DeleteObject(ctrl.hfont)
            win32gui.PostQuitMessage(0)
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def show(self):
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        win32gui.UpdateWindow(self.hwnd)

        msg = ctypes.wintypes.MSG()
        while win32gui.GetMessage(ctypes.byref(msg), 0, 0) > 0:
            if msg.message == win32con.WM_KEYDOWN:
                ctrl_pressed = (win32api.GetKeyState(win32con.VK_CONTROL) & 0x8000) != 0
                if ctrl_pressed and self.handle_zoom_shortcut(msg.wParam):
                    continue
            win32gui.TranslateMessage(ctypes.byref(msg))
            win32gui.DispatchMessage(ctypes.byref(msg))


if __name__ == "__main__":
    app = ViewportWindow(
        title="Viewport & Canvas App",
        width=800,
        height=600,
        canvas_width=2000,
        canvas_height=1500,
    )
    app.show()
