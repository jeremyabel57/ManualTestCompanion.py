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

import ctypes
from ctypes import wintypes
import win32api
import win32con
import win32gui

# Win32 Constants not always exposed in win32con
WM_MOUSEHWHEEL = 0x020E
WHEEL_DELTA = 120
VK_OEM_PLUS = 0xBB
VK_OEM_MINUS = 0xBD
DEFAULT_GUI_FONT = 17


class CanvasControl:
    """Represents a child Win32 UI control placed on the virtual canvas."""

    def __init__(self, hwnd, class_name, text, x, y, width, height, font_size=9, ctrl_id=0):
        self.hwnd = hwnd
        self.class_name = class_name
        self.text = text
        self.base_x = x
        self.base_y = y
        self.base_width = width
        self.base_height = height
        self.base_font_size = font_size
        self.ctrl_id = ctrl_id
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
        self.base_canvas_width = canvas_width
        self.base_canvas_height = canvas_height
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height

        self.zoom = 1.0
        self.min_zoom = 0.25
        self.max_zoom = 4.0
        self.zoom_step = 0.1

        self.scroll_x = 0
        self.scroll_y = 0
        self.wheel_step = 40

        self.hwnd = None
        self.canvas_hwnd = None
        self.controls = []
        self.next_ctrl_id = 1001

        # Register Viewport window class
        self.wc = win32gui.WNDCLASS()
        self.wc.lpfnWndProc = self.wnd_proc
        self.wc.lpszClassName = "ViewportWin32Class"
        self.wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        self.wc.hbrBackground = win32con.COLOR_APPWORKSPACE + 1
        self.wc.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
        win32gui.RegisterClass(self.wc)

        # Register Canvas child window class
        self.canvas_wc = win32gui.WNDCLASS()
        self.canvas_wc.lpfnWndProc = self.canvas_wnd_proc
        self.canvas_wc.lpszClassName = "CanvasChildWin32Class"
        self.canvas_wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        self.canvas_wc.hbrBackground = win32con.COLOR_WINDOW + 1
        self.canvas_wc.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
        win32gui.RegisterClass(self.canvas_wc)

        self.create_window()
        self.create_canvas()
        self.create_sample_controls()

    def create_window(self):
        style = (
            win32con.WS_OVERLAPPEDWINDOW
            | win32con.WS_HSCROLL
            | win32con.WS_VSCROLL
            | win32con.WS_CLIPCHILDREN
        )
        self.hwnd = win32gui.CreateWindow(
            self.wc.lpszClassName,
            self.format_title(),
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

    def create_canvas(self):
        style = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_BORDER | win32con.WS_CLIPCHILDREN
        self.canvas_hwnd = win32gui.CreateWindow(
            self.canvas_wc.lpszClassName,
            "",
            style,
            0,
            0,
            self.canvas_width,
            self.canvas_height,
            self.hwnd,
            0,
            self.canvas_wc.hInstance,
            None,
        )

    def add_control(self, class_name, text, x, y, width, height, style=0, ex_style=0, font_size=9):
        """Creates a native Win32 child control inside the canvas that scales with zoom."""
        ctrl_id = self.next_ctrl_id
        self.next_ctrl_id += 1

        base_style = win32con.WS_CHILD | win32con.WS_VISIBLE | style
        hwnd = win32gui.CreateWindowEx(
            ex_style,
            class_name,
            text,
            base_style,
            int(round(x * self.zoom)),
            int(round(y * self.zoom)),
            int(round(width * self.zoom)),
            int(round(height * self.zoom)),
            self.canvas_hwnd,
            ctrl_id,
            self.canvas_wc.hInstance,
            None,
        )

        ctrl = CanvasControl(hwnd, class_name, text, x, y, width, height, font_size, ctrl_id)
        self.apply_control_font(ctrl)
        self.controls.append(ctrl)
        return ctrl

    def create_sample_controls(self):
        """Adds sample child UI controls to demonstrate zooming and scrolling."""
        self.add_control(
            "STATIC",
            "Viewport Canvas Form (Zoom with Ctrl+Wheel or Ctrl + / - / 0)",
            40,
            30,
            420,
            24,
            font_size=10,
        )
        self.add_control("STATIC", "Item Name:", 40, 75, 100, 22)
        self.edit_ctrl = self.add_control(
            "EDIT",
            "Sample Node 01",
            150,
            72,
            220,
            26,
            style=win32con.ES_AUTOHSCROLL | win32con.WS_TABSTOP,
            ex_style=win32con.WS_EX_CLIENTEDGE,
        )
        self.add_control(
            "BUTTON",
            "Trigger Action",
            385,
            71,
            120,
            28,
            style=win32con.BS_PUSHBUTTON | win32con.WS_TABSTOP,
        )
        self.check_ctrl = self.add_control(
            "BUTTON",
            "Enable Grid Snap",
            40,
            115,
            160,
            24,
            style=win32con.BS_AUTOCHECKBOX | win32con.WS_TABSTOP,
        )
        self.list_ctrl = self.add_control(
            "LISTBOX",
            "",
            40,
            155,
            330,
            130,
            style=win32con.LBS_NOTIFY | win32con.WS_VSCROLL | win32con.WS_TABSTOP,
            ex_style=win32con.WS_EX_CLIENTEDGE,
        )
        for item in ("Layer 1: Background Grid", "Layer 2: Vector Shapes", "Layer 3: UI Controls", "Layer 4: Annotations"):
            win32gui.SendMessage(self.list_ctrl.hwnd, win32con.LB_ADDSTRING, 0, item)

        # Distant control to test scrolling + zooming across the larger canvas
        self.add_control(
            "BUTTON",
            "Far Canvas Button (1200, 900)",
            1200,
            900,
            220,
            40,
            style=win32con.BS_PUSHBUTTON,
            font_size=10,
        )

    def apply_control_font(self, ctrl):
        """Creates and assigns a scaled font matching the current zoom level."""
        if ctrl.hfont:
            win32gui.DeleteObject(ctrl.hfont)
            ctrl.hfont = None

        hdc = win32gui.GetDC(self.hwnd)
        logpixelsy = win32gui.GetDeviceCaps(hdc, win32con.LOGPIXELSY)
        win32gui.ReleaseDC(self.hwnd, hdc)

        scaled_pt = max(4, ctrl.base_font_size * self.zoom)
        lf = win32gui.LOGFONT()
        lf.lfHeight = -int(round(scaled_pt * logpixelsy / 72.0))
        lf.lfWeight = win32con.FW_NORMAL
        lf.lfFaceName = "Segoe UI"

        ctrl.hfont = win32gui.CreateFontIndirect(lf)
        win32gui.SendMessage(ctrl.hwnd, win32con.WM_SETFONT, ctrl.hfont, True)

    def layout_controls(self):
        """Rescales and repositions all child controls on the canvas."""
        for ctrl in self.controls:
            x = int(round(ctrl.base_x * self.zoom))
            y = int(round(ctrl.base_y * self.zoom))
            w = max(1, int(round(ctrl.base_width * self.zoom)))
            h = max(1, int(round(ctrl.base_height * self.zoom)))

            win32gui.SetWindowPos(
                ctrl.hwnd,
                0,
                x,
                y,
                w,
                h,
                win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE,
            )
            self.apply_control_font(ctrl)

    def format_title(self):
        return f"{self.base_title} ({int(round(self.zoom * 100))}%)"

    def update_title(self):
        if self.hwnd:
            win32gui.SetWindowText(self.hwnd, self.format_title())

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
        if not self.hwnd:
            return

        _, _, client_w, client_h = win32gui.GetClientRect(self.hwnd)

        max_x = max(0, self.canvas_width - client_w)
        self.scroll_x = max(0, min(self.scroll_x, max_x))
        si_h = (
            win32con.SIF_RANGE | win32con.SIF_PAGE | win32con.SIF_POS,
            0,
            max(0, self.canvas_width - 1),
            client_w,
            self.scroll_x,
            0,
        )
        win32gui.SetScrollInfo(self.hwnd, win32con.SB_HORZ, si_h, True)

        max_y = max(0, self.canvas_height - client_h)
        self.scroll_y = max(0, min(self.scroll_y, max_y))
        si_v = (
            win32con.SIF_RANGE | win32con.SIF_PAGE | win32con.SIF_POS,
            0,
            max(0, self.canvas_height - 1),
            client_h,
            self.scroll_y,
            0,
        )
        win32gui.SetScrollInfo(self.hwnd, win32con.SB_VERT, si_v, True)

        self.position_canvas()

    def set_zoom(self, new_zoom, anchor_x=None, anchor_y=None):
        new_zoom = round(max(self.min_zoom, min(self.max_zoom, new_zoom)), 2)
        if new_zoom == self.zoom:
            return

        _, _, client_w, client_h = win32gui.GetClientRect(self.hwnd)
        if anchor_x is None:
            anchor_x = client_w / 2.0
        if anchor_y is None:
            anchor_y = client_h / 2.0

        canvas_pt_x = (self.scroll_x + anchor_x) / self.zoom
        canvas_pt_y = (self.scroll_y + anchor_y) / self.zoom

        self.zoom = new_zoom
        self.canvas_width = max(1, int(round(self.base_canvas_width * self.zoom)))
        self.canvas_height = max(1, int(round(self.base_canvas_height * self.zoom)))

        self.scroll_x = int(round(canvas_pt_x * self.zoom - anchor_x))
        self.scroll_y = int(round(canvas_pt_y * self.zoom - anchor_y))

        self.update_scrollbars()
        self.layout_controls()
        self.update_title()
        if self.canvas_hwnd:
            win32gui.InvalidateRect(self.canvas_hwnd, None, True)

    def handle_scroll(self, bar, wparam):
        action = win32api.LOWORD(wparam)
        si = win32gui.GetScrollInfo(self.hwnd, bar)
        n_min, n_max, n_page, n_pos, n_track = si[1], si[2], si[3], si[4], si[5]

        pos = n_pos
        line_step = 20

        if action == win32con.SB_LINEUP:
            pos -= line_step
        elif action == win32con.SB_LINEDOWN:
            pos += line_step
        elif action == win32con.SB_PAGEUP:
            pos -= n_page
        elif action == win32con.SB_PAGEDOWN:
            pos += n_page
        elif action in (win32con.SB_THUMBTRACK, win32con.SB_THUMBPOSITION):
            pos = n_track
        elif action == win32con.SB_TOP:
            pos = n_min
        elif action == win32con.SB_BOTTOM:
            pos = n_max

        max_scroll = max(0, n_max - n_page + 1)
        pos = max(0, min(pos, max_scroll))

        if pos != n_pos:
            if bar == win32con.SB_HORZ:
                self.scroll_x = pos
            else:
                self.scroll_y = pos

            win32gui.SetScrollInfo(self.hwnd, bar, (win32con.SIF_POS, 0, 0, 0, pos, 0), True)
            self.position_canvas()

    def scroll_by(self, bar, delta):
        si = win32gui.GetScrollInfo(self.hwnd, bar)
        n_max, n_page, n_pos = si[2], si[3], si[4]
        max_scroll = max(0, n_max - n_page + 1)
        new_pos = max(0, min(n_pos + delta, max_scroll))

        if new_pos != n_pos:
            if bar == win32con.SB_HORZ:
                self.scroll_x = new_pos
            else:
                self.scroll_y = new_pos

            win32gui.SetScrollInfo(self.hwnd, bar, (win32con.SIF_POS, 0, 0, 0, new_pos, 0), True)
            self.position_canvas()

    def handle_mouse_wheel(self, wparam, lparam, horizontal=False):
        delta = ctypes.c_short(win32api.HIWORD(wparam)).value
        key_state = win32api.LOWORD(wparam)

        if not horizontal and (key_state & win32con.MK_CONTROL):
            screen_x = ctypes.c_short(win32api.LOWORD(lparam)).value
            screen_y = ctypes.c_short(win32api.HIWORD(lparam)).value
            client_x, client_y = win32gui.ScreenToClient(self.hwnd, (screen_x, screen_y))

            steps = delta / WHEEL_DELTA
            self.set_zoom(self.zoom + steps * self.zoom_step, client_x, client_y)
            return

        if horizontal:
            scroll_delta = int((delta / WHEEL_DELTA) * self.wheel_step)
            self.scroll_by(win32con.SB_HORZ, scroll_delta)
        elif key_state & win32con.MK_SHIFT:
            scroll_delta = -int((delta / WHEEL_DELTA) * self.wheel_step)
            self.scroll_by(win32con.SB_HORZ, scroll_delta)
        else:
            scroll_delta = -int((delta / WHEEL_DELTA) * self.wheel_step)
            self.scroll_by(win32con.SB_VERT, scroll_delta)

    def handle_keydown(self, wparam):
        ctrl_pressed = (win32api.GetKeyState(win32con.VK_CONTROL) & 0x8000) != 0
        if not ctrl_pressed:
            return False

        if wparam in (VK_OEM_PLUS, win32con.VK_ADD):
            self.set_zoom(self.zoom + self.zoom_step)
            return True
        if wparam in (VK_OEM_MINUS, win32con.VK_SUBTRACT):
            self.set_zoom(self.zoom - self.zoom_step)
            return True
        if wparam in (ord("0"), win32con.VK_NUMPAD0):
            self.set_zoom(1.0)
            return True
        return False

    def handle_command(self, wparam, lparam):
        ctrl_id = win32api.LOWORD(wparam)
        notify_code = win32api.HIWORD(wparam)

        if notify_code == win32con.BN_CLICKED:
            for ctrl in self.controls:
                if ctrl.ctrl_id == ctrl_id:
                    if ctrl == self.check_ctrl:
                        checked = win32gui.SendMessage(ctrl.hwnd, win32con.BM_GETCHECK, 0, 0) == win32con.BST_CHECKED
                        win32gui.SetWindowText(self.edit_ctrl.hwnd, f"Grid Snap: {'ON' if checked else 'OFF'}")
                    else:
                        current_text = win32gui.GetWindowText(self.edit_ctrl.hwnd)
                        win32gui.MessageBox(
                            self.hwnd,
                            f"Clicked '{ctrl.text}'\nCurrent input text: {current_text}",
                            "Canvas Control Event",
                            win32con.MB_OK | win32con.MB_ICONINFORMATION,
                        )
                    break

    def cleanup_fonts(self):
        for ctrl in self.controls:
            if ctrl.hfont:
                win32gui.DeleteObject(ctrl.hfont)
                ctrl.hfont = None

    def wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_SIZE:
            self.width = win32api.LOWORD(lparam)
            self.height = win32api.HIWORD(lparam)
            self.update_scrollbars()
            return 0
        elif msg == win32con.WM_HSCROLL:
            self.handle_scroll(win32con.SB_HORZ, wparam)
            return 0
        elif msg == win32con.WM_VSCROLL:
            self.handle_scroll(win32con.SB_VERT, wparam)
            return 0
        elif msg == win32con.WM_MOUSEWHEEL:
            self.handle_mouse_wheel(wparam, lparam, horizontal=False)
            return 0
        elif msg == WM_MOUSEHWHEEL:
            self.handle_mouse_wheel(wparam, lparam, horizontal=True)
            return 0
        elif msg == win32con.WM_KEYDOWN:
            if self.handle_keydown(wparam):
                return 0
        elif msg == win32con.WM_DESTROY:
            self.cleanup_fonts()
            win32gui.PostQuitMessage(0)
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def canvas_wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_COMMAND:
            self.handle_command(wparam, lparam)
            return 0
        elif msg == win32con.WM_MOUSEWHEEL:
            self.handle_mouse_wheel(wparam, lparam, horizontal=False)
            return 0
        elif msg == WM_MOUSEHWHEEL:
            self.handle_mouse_wheel(wparam, lparam, horizontal=True)
            return 0
        elif msg == win32con.WM_KEYDOWN:
            if self.handle_keydown(wparam):
                return 0
        elif msg == win32con.WM_CTLCOLORSTATIC:
            hdc = wparam
            win32gui.SetBkMode(hdc, win32con.TRANSPARENT)
            return win32gui.GetStockObject(win32con.WHITE_BRUSH)
        elif msg == win32con.WM_PAINT:
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
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def show(self):
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        win32gui.UpdateWindow(self.hwnd)
        self.update_scrollbars()

        # Custom message loop so Ctrl + + / - / 0 work even when a child control has focus
        msg = wintypes.MSG()
        user32 = ctypes.windll.user32
        while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) > 0:
            if msg.message == win32con.WM_KEYDOWN and self.handle_keydown(msg.wParam):
                continue
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))


if __name__ == "__main__":
    app = ViewportWindow(title="Viewport & Canvas App", width=800, height=600)
    app.show()
