import ctypes
import subprocess
import sys


def ensure_dependencies():
    try:
        import win32api  # noqa: F401
        import win32con  # noqa: F401
        import win32gui  # noqa: F401
        import win32print  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pywin32"])


ensure_dependencies()

import win32api
import win32con
import win32gui
import win32print


WM_MOUSEHWHEEL = 0x020E
WHEEL_DELTA = 120
LOGPIXELSY = 90

VK_CONTROL = 0x11
VK_OEM_PLUS = 0xBB
VK_OEM_MINUS = 0xBD
VK_ADD = 0x6B
VK_SUBTRACT = 0x6D
VK_NUMPAD0 = 0x60


class CanvasControl:

    def __init__(
        self,
        hwnd,
        control_id,
        class_name,
        text,
        x,
        y,
        width,
        height,
        base_font_size=10,
        on_click=None,
    ):
        self.hwnd = hwnd
        self.control_id = control_id
        self.class_name = class_name
        self.text = text
        self.base_x = x
        self.base_y = y
        self.base_width = width
        self.base_height = height
        self.base_font_size = base_font_size
        self.on_click = on_click
        self.font_handle = None


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
        self.base_canvas_width = canvas_width
        self.base_canvas_height = canvas_height

        self.zoom = 1.0
        self.min_zoom = 0.25
        self.max_zoom = 4.0
        self.zoom_step = 1.15

        self.canvas_width = canvas_width
        self.canvas_height = canvas_height

        self.hwnd = None
        self.canvas_hwnd = None
        self.scroll_x = 0
        self.scroll_y = 0
        self.line_step = 30
        self.wheel_step = 90

        self.controls = {}
        self.next_control_id = 1001

        self.hinstance = win32api.GetModuleHandle(None)

        # Register the outer viewport window class
        self.wc = win32gui.WNDCLASS()
        self.wc.lpfnWndProc = self.wnd_proc
        self.wc.hInstance = self.hinstance
        self.wc.lpszClassName = "ViewportWindowClass"
        self.wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        self.wc.hbrBackground = win32con.COLOR_APPWORKSPACE + 1
        self.wc.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
        win32gui.RegisterClass(self.wc)

        # Register the inner canvas window class
        self.canvas_wc = win32gui.WNDCLASS()
        self.canvas_wc.lpfnWndProc = self.canvas_wnd_proc
        self.canvas_wc.hInstance = self.hinstance
        self.canvas_wc.lpszClassName = "InnerCanvasWindowClass"
        self.canvas_wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        self.canvas_wc.hbrBackground = win32con.COLOR_WINDOW + 1
        self.canvas_wc.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
        win32gui.RegisterClass(self.canvas_wc)

        self.create_windows()

    def create_windows(self):
        viewport_style = (
            win32con.WS_OVERLAPPEDWINDOW
            | win32con.WS_HSCROLL
            | win32con.WS_VSCROLL
            | win32con.WS_CLIPCHILDREN
        )
        self.hwnd = win32gui.CreateWindow(
            self.wc.lpszClassName,
            self._format_title(),
            viewport_style,
            win32con.CW_USEDEFAULT,
            win32con.CW_USEDEFAULT,
            self.width,
            self.height,
            0,
            0,
            self.hinstance,
            None,
        )

        canvas_style = (
            win32con.WS_CHILD
            | win32con.WS_VISIBLE
            | win32con.WS_BORDER
            | win32con.WS_CLIPCHILDREN
        )
        self.canvas_hwnd = win32gui.CreateWindow(
            self.canvas_wc.lpszClassName,
            "",
            canvas_style,
            0,
            0,
            self.canvas_width,
            self.canvas_height,
            self.hwnd,
            0,
            self.hinstance,
            None,
        )

    def _format_title(self):
        return f"{self.base_title} ({int(round(self.zoom * 100))}%)"

    def _update_title(self):
        if self.hwnd:
            win32gui.SetWindowText(self.hwnd, self._format_title())

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
        base_font_size=10,
        on_click=None,
    ):
        control_id = self.next_control_id
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
            control_id,
            self.hinstance,
            None,
        )

        ctrl = CanvasControl(
            hwnd=ctrl_hwnd,
            control_id=control_id,
            class_name=class_name,
            text=text,
            x=x,
            y=y,
            width=width,
            height=height,
            base_font_size=base_font_size,
            on_click=on_click,
        )
        self.controls[control_id] = ctrl
        self.apply_control_font(ctrl)
        return ctrl

    def apply_control_font(self, ctrl):
        hdc = win32gui.GetDC(ctrl.hwnd)
        logpixelsy = win32print.GetDeviceCaps(hdc, LOGPIXELSY)
        win32gui.ReleaseDC(ctrl.hwnd, hdc)

        scaled_pt = max(6, int(round(ctrl.base_font_size * self.zoom)))
        lf = win32gui.LOGFONT()
        lf.lfHeight = -int(round(scaled_pt * logpixelsy / 72.0))
        lf.lfFaceName = "Segoe UI"

        new_font = win32gui.CreateFontIndirect(lf)
        win32gui.SendMessage(ctrl.hwnd, win32con.WM_SETFONT, new_font, True)

        if ctrl.font_handle:
            win32gui.DeleteObject(ctrl.font_handle)
        ctrl.font_handle = new_font

    def layout_controls(self):
        for ctrl in self.controls.values():
            scaled_x = int(round(ctrl.base_x * self.zoom))
            scaled_y = int(round(ctrl.base_y * self.zoom))
            scaled_w = max(1, int(round(ctrl.base_width * self.zoom)))
            scaled_h = max(1, int(round(ctrl.base_height * self.zoom)))

            win32gui.SetWindowPos(
                ctrl.hwnd,
                0,
                scaled_x,
                scaled_y,
                scaled_w,
                scaled_h,
                win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE,
            )
            self.apply_control_font(ctrl)

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

    def update_scrollbars(self, client_width, client_height):
        max_x = max(0, self.canvas_width - client_width)
        self.scroll_x = max(0, min(self.scroll_x, max_x))

        si_h = (
            win32con.SIF_RANGE | win32con.SIF_PAGE | win32con.SIF_POS,
            0,
            max(0, self.canvas_width - 1),
            client_width,
            self.scroll_x,
            0,
        )
        win32gui.SetScrollInfo(self.hwnd, win32con.SB_HORZ, si_h, True)

        max_y = max(0, self.canvas_height - client_height)
        self.scroll_y = max(0, min(self.scroll_y, max_y))

        si_v = (
            win32con.SIF_RANGE | win32con.SIF_PAGE | win32con.SIF_POS,
            0,
            max(0, self.canvas_height - 1),
            client_height,
            self.scroll_y,
            0,
        )
        win32gui.SetScrollInfo(self.hwnd, win32con.SB_VERT, si_v, True)

        self.position_canvas()

    def set_zoom(self, new_zoom, anchor_x=None, anchor_y=None):
        new_zoom = max(self.min_zoom, min(self.max_zoom, new_zoom))
        if abs(new_zoom - self.zoom) < 1e-6:
            return

        left, top, right, bottom = win32gui.GetClientRect(self.hwnd)
        client_w = right - left
        client_h = bottom - top

        if anchor_x is None:
            anchor_x = client_w / 2.0
        if anchor_y is None:
            anchor_y = client_h / 2.0

        canvas_x = (self.scroll_x + anchor_x) / self.zoom
        canvas_y = (self.scroll_y + anchor_y) / self.zoom

        self.zoom = new_zoom
        self.canvas_width = max(1, int(round(self.base_canvas_width * self.zoom)))
        self.canvas_height = max(1, int(round(self.base_canvas_height * self.zoom)))

        self.scroll_x = int(round(canvas_x * self.zoom - anchor_x))
        self.scroll_y = int(round(canvas_y * self.zoom - anchor_y))

        self.update_scrollbars(client_w, client_h)
        self.layout_controls()
        self._update_title()
        win32gui.InvalidateRect(self.canvas_hwnd, None, True)

    def handle_zoom_shortcut(self, vk):
        if vk in (VK_OEM_PLUS, VK_ADD):
            self.set_zoom(self.zoom * self.zoom_step)
            return True
        if vk in (VK_OEM_MINUS, VK_SUBTRACT):
            self.set_zoom(self.zoom / self.zoom_step)
            return True
        if vk in (ord("0"), VK_NUMPAD0):
            self.set_zoom(1.0)
            return True
        return False

    def scroll_horizontal_by(self, delta_x):
        left, top, right, bottom = win32gui.GetClientRect(self.hwnd)
        client_w = right - left
        max_x = max(0, self.canvas_width - client_w)

        new_pos = max(0, min(self.scroll_x + delta_x, max_x))
        if new_pos != self.scroll_x:
            self.scroll_x = new_pos
            si = (win32con.SIF_POS, 0, 0, 0, self.scroll_x, 0)
            win32gui.SetScrollInfo(self.hwnd, win32con.SB_HORZ, si, True)
            self.position_canvas()

    def scroll_vertical_by(self, delta_y):
        left, top, right, bottom = win32gui.GetClientRect(self.hwnd)
        client_h = bottom - top
        max_y = max(0, self.canvas_height - client_h)

        new_pos = max(0, min(self.scroll_y + delta_y, max_y))
        if new_pos != self.scroll_y:
            self.scroll_y = new_pos
            si = (win32con.SIF_POS, 0, 0, 0, self.scroll_y, 0)
            win32gui.SetScrollInfo(self.hwnd, win32con.SB_VERT, si, True)
            self.position_canvas()

    def handle_scroll(self, bar, scroll_code):
        si = win32gui.GetScrollInfo(self.hwnd, bar)
        nMin, nMax, nPage, nPos, nTrackPos = si[1], si[2], si[3], si[4], si[5]
        max_pos = max(0, nMax - nPage + 1)

        if scroll_code == win32con.SB_LINEUP:
            new_pos = nPos - self.line_step
        elif scroll_code == win32con.SB_LINEDOWN:
            new_pos = nPos + self.line_step
        elif scroll_code == win32con.SB_PAGEUP:
            new_pos = nPos - nPage
        elif scroll_code == win32con.SB_PAGEDOWN:
            new_pos = nPos + nPage
        elif scroll_code in (win32con.SB_THUMBTRACK, win32con.SB_THUMBPOSITION):
            new_pos = nTrackPos
        elif scroll_code == win32con.SB_TOP:
            new_pos = nMin
        elif scroll_code == win32con.SB_BOTTOM:
            new_pos = max_pos
        else:
            return

        new_pos = max(nMin, min(new_pos, max_pos))

        if bar == win32con.SB_HORZ and new_pos != self.scroll_x:
            self.scroll_x = new_pos
            win32gui.SetScrollInfo(
                self.hwnd, bar, (win32con.SIF_POS, 0, 0, 0, self.scroll_x, 0), True
            )
            self.position_canvas()
        elif bar == win32con.SB_VERT and new_pos != self.scroll_y:
            self.scroll_y = new_pos
            win32gui.SetScrollInfo(
                self.hwnd, bar, (win32con.SIF_POS, 0, 0, 0, self.scroll_y, 0), True
            )
            self.position_canvas()

    def _on_mousewheel(self, wparam, lparam):
        delta = ctypes.c_short(wparam >> 16).value
        keys = wparam & 0xFFFF

        if keys & win32con.MK_CONTROL:
            screen_x = ctypes.c_short(lparam & 0xFFFF).value
            screen_y = ctypes.c_short((lparam >> 16) & 0xFFFF).value
            client_x, client_y = win32gui.ScreenToClient(self.hwnd, (screen_x, screen_y))

            steps = delta / WHEEL_DELTA
            factor = self.zoom_step ** steps
            self.set_zoom(self.zoom * factor, anchor_x=client_x, anchor_y=client_y)
        else:
            scroll_amount = -int((delta / WHEEL_DELTA) * self.wheel_step)
            if keys & win32con.MK_SHIFT:
                self.scroll_horizontal_by(scroll_amount)
            else:
                self.scroll_vertical_by(scroll_amount)

    def _on_mousehwheel(self, wparam):
        delta = ctypes.c_short(wparam >> 16).value
        scroll_amount = int((delta / WHEEL_DELTA) * self.wheel_step)
        self.scroll_horizontal_by(scroll_amount)

    def canvas_wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_COMMAND:
            ctrl_id = wparam & 0xFFFF
            notify_code = (wparam >> 16) & 0xFFFF
            if notify_code == win32con.BN_CLICKED and ctrl_id in self.controls:
                ctrl = self.controls[ctrl_id]
                if ctrl.on_click:
                    ctrl.on_click(ctrl)
                return 0

        if msg == win32con.WM_MOUSEWHEEL:
            self._on_mousewheel(wparam, lparam)
            return 0

        if msg == WM_MOUSEHWHEEL:
            self._on_mousehwheel(wparam)
            return 0

        if msg == win32con.WM_PAINT:
            hdc, ps = win32gui.BeginPaint(hwnd)
            pen = win32gui.CreatePen(win32con.PS_SOLID, 1, win32api.RGB(230, 230, 230))
            old_pen = win32gui.SelectObject(hdc, pen)

            step = max(10, int(round(100 * self.zoom)))
            for x in range(0, self.canvas_width, step):
                win32gui.MoveToEx(hdc, x, 0)
                win32gui.LineTo(hdc, x, self.canvas_height)
            for y in range(0, self.canvas_height, step):
                win32gui.MoveToEx(hdc, 0, y)
                win32gui.LineTo(hdc, self.canvas_width, y)

            win32gui.SelectObject(hdc, old_pen)
            win32gui.DeleteObject(pen)
            win32gui.EndPaint(hwnd, ps)
            return 0

        if msg == win32con.WM_DESTROY:
            for ctrl in self.controls.values():
                if ctrl.font_handle:
                    win32gui.DeleteObject(ctrl.font_handle)
                    ctrl.font_handle = None
            return 0

        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_SIZE:
            self.width = lparam & 0xFFFF
            self.height = (lparam >> 16) & 0xFFFF
            self.update_scrollbars(self.width, self.height)
            return 0

        if msg == win32con.WM_KEYDOWN:
            ctrl_pressed = (win32api.GetKeyState(VK_CONTROL) & 0x8000) != 0
            if ctrl_pressed and self.handle_zoom_shortcut(wparam):
                return 0

        if msg == win32con.WM_HSCROLL:
            scroll_code = wparam & 0xFFFF
            self.handle_scroll(win32con.SB_HORZ, scroll_code)
            return 0

        if msg == win32con.WM_VSCROLL:
            scroll_code = wparam & 0xFFFF
            self.handle_scroll(win32con.SB_VERT, scroll_code)
            return 0

        if msg == win32con.WM_MOUSEWHEEL:
            self._on_mousewheel(wparam, lparam)
            return 0

        if msg == WM_MOUSEHWHEEL:
            self._on_mousehwheel(wparam)
            return 0

        if msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return 0

        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def show(self):
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        win32gui.UpdateWindow(self.hwnd)

        while True:
            ret, msg = win32gui.GetMessage(None, 0, 0)
            if ret <= 0:
                break

            hwnd, message, wparam, lparam, time, pt = msg
            if message == win32con.WM_KEYDOWN:
                ctrl_pressed = (win32api.GetKeyState(VK_CONTROL) & 0x8000) != 0
                if ctrl_pressed and self.handle_zoom_shortcut(wparam):
                    continue

            win32gui.TranslateMessage(msg)
            win32gui.DispatchMessage(msg)


if __name__ == "__main__":
    app = ViewportWindow(
        title="Viewport & Canvas",
        width=800,
        height=600,
        canvas_width=2000,
        canvas_height=1500,
    )

    app.add_control("STATIC", "Canvas Form Controls (Zoom with Ctrl + Wheel or Ctrl + +/-/0):", 40, 30, 520, 24, base_font_size=11)
    app.add_control("STATIC", "Name:", 40, 75, 80, 24)
    name_input = app.add_control(
        "EDIT",
        "Sample Input",
        130,
        72,
        240,
        28,
        style=win32con.ES_AUTOHSCROLL,
        ex_style=win32con.WS_EX_CLIENTEDGE,
    )
    status_label = app.add_control("STATIC", "Status: Ready", 40, 165, 400, 24)

    def on_submit(_ctrl):
        current_text = win32gui.GetWindowText(name_input.hwnd)
        win32gui.SetWindowText(status_label.hwnd, f"Status: Submitted '{current_text}'")

    app.add_control(
        "BUTTON",
        "Submit",
        130,
        115,
        110,
        32,
        style=win32con.BS_PUSHBUTTON,
        on_click=on_submit,
    )

    app.add_control(
        "BUTTON",
        "Reset Zoom (100%)",
        255,
        115,
        150,
        32,
        style=win32con.BS_PUSHBUTTON,
        on_click=lambda _c: app.set_zoom(1.0),
    )

    app.add_control(
        "BUTTON",
        "Bottom-Right Control",
        1650,
        1350,
        200,
        40,
        style=win32con.BS_PUSHBUTTON,
        on_click=lambda _c: win32gui.SetWindowText(status_label.hwnd, "Status: Clicked bottom-right button!"),
    )

    app.show()
