import ctypes
from ctypes import wintypes
import win32api
import win32con
import win32gui

CANVASZOOMTYPE_FREE = 1
CANVASZOOMTYPE_MIN = 2


class SCROLLINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("fMask", wintypes.UINT),
        ("nMin", ctypes.c_int),
        ("nMax", ctypes.c_int),
        ("nPage", wintypes.UINT),
        ("nPos", ctypes.c_int),
        ("nTrackPos", ctypes.c_int),
    ]


class LOGFONTW(ctypes.Structure):
    _fields_ = [
        ("lfHeight", wintypes.LONG),
        ("lfWidth", wintypes.LONG),
        ("lfEscapement", wintypes.LONG),
        ("lfOrientation", wintypes.LONG),
        ("lfWeight", wintypes.LONG),
        ("lfItalic", wintypes.BYTE),
        ("lfUnderline", wintypes.BYTE),
        ("lfStrikeOut", wintypes.BYTE),
        ("lfCharSet", wintypes.BYTE),
        ("lfOutPrecision", wintypes.BYTE),
        ("lfClipPrecision", wintypes.BYTE),
        ("lfQuality", wintypes.BYTE),
        ("lfPitchAndFamily", wintypes.BYTE),
        ("lfFaceName", wintypes.WCHAR * 32),
    ]


class Win32ViewportCanvas:
    """
    Manages a Win32 Viewport child/popup window containing a scrollable, zoomable Canvas window.
    Extracted and translated from AutoIt winmgmt.au3.
    """

    _classes_registered = False
    _VIEWPORT_CLASS = "Win32ViewportClass"
    _CANVAS_CLASS = "Win32CanvasClass"
    _instance_map = {}

    def __init__(
        self,
        parent_hwnd: int,
        x: int,
        y: int,
        viewport_w: int,
        viewport_h: int,
        canvas_w: int = None,
        canvas_h: int = None,
        zoom_type: int = CANVASZOOMTYPE_FREE,
        is_popup: bool = False,
        title: str = "Viewport",
    ):
        self.parent_hwnd = parent_hwnd
        self.viewport_x = x
        self.viewport_y = y
        self.viewport_w = viewport_w
        self.viewport_h = viewport_h

        self.canvas_w = canvas_w if canvas_w is not None else viewport_w
        self.canvas_h = canvas_h if canvas_h is not None else viewport_h
        self.base_canvas_w = self.canvas_w
        self.base_canvas_h = self.canvas_h
        self.min_w = self.canvas_w
        self.min_h = self.canvas_h

        self.zoom_type = zoom_type
        self.is_popup = is_popup
        self.title = title

        # Tracking state
        self.scroll_x = 0
        self.scroll_y = 0
        self.zoom_scale = 1.0
        self.cataloged_controls = []  # List of dicts: {hwnd, x, y, w, h, font_size}
        self._font_handles = []  # Keep references so GDI HFONTs are not freed prematurely

        self._register_window_classes()
        self._create_windows()
        self.on_resize(self.viewport_w, self.viewport_h)

    @classmethod
    def _register_window_classes(cls):
        if cls._classes_registered:
            return

        hinstance = win32api.GetModuleHandle(None)

        # Viewport Window Class
        wc_vp = win32gui.WNDCLASS()
        wc_vp.lpfnWndProc = cls._static_viewport_wndproc
        wc_vp.hInstance = hinstance
        wc_vp.lpszClassName = cls._VIEWPORT_CLASS
        wc_vp.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        wc_vp.hbrBackground = win32con.COLOR_WINDOW + 1
        wc_vp.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
        win32gui.RegisterClass(wc_vp)

        # Canvas Window Class
        wc_can = win32gui.WNDCLASS()
        wc_can.lpfnWndProc = cls._static_canvas_wndproc
        wc_can.hInstance = hinstance
        wc_can.lpszClassName = cls._CANVAS_CLASS
        wc_can.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        wc_can.hbrBackground = win32con.COLOR_BTNFACE + 1
        wc_can.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
        win32gui.RegisterClass(wc_can)

        cls._classes_registered = True

    @classmethod
    def _static_viewport_wndproc(cls, hwnd, msg, wparam, lparam):
        instance = cls._instance_map.get(hwnd)
        if instance:
            return instance._viewport_wndproc(hwnd, msg, wparam, lparam)
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    @classmethod
    def _static_canvas_wndproc(cls, hwnd, msg, wparam, lparam):
        instance = cls._instance_map.get(hwnd)
        if instance:
            return instance._canvas_wndproc(hwnd, msg, wparam, lparam)
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _create_windows(self):
        hinstance = win32api.GetModuleHandle(None)

        if self.is_popup:
            vp_style = (
                win32con.WS_MINIMIZEBOX
                | win32con.WS_MAXIMIZEBOX
                | win32con.WS_CAPTION
                | win32con.WS_POPUP
                | win32con.WS_SYSMENU
                | win32con.WS_THICKFRAME
                | win32con.WS_HSCROLL
                | win32con.WS_VSCROLL
            )
        else:
            vp_style = (
                win32con.WS_CHILD
                | win32con.WS_VISIBLE
                | win32con.WS_CLIPCHILDREN
                | win32con.WS_HSCROLL
                | win32con.WS_VSCROLL
            )

        self.hwnd_viewport = win32gui.CreateWindowEx(
            0,
            self._VIEWPORT_CLASS,
            self.title,
            vp_style,
            self.viewport_x,
            self.viewport_y,
            self.viewport_w,
            self.viewport_h,
            self.parent_hwnd,
            0,
            hinstance,
            None,
        )
        self._instance_map[self.hwnd_viewport] = self

        can_style = win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_CLIPCHILDREN
        self.hwnd_canvas = win32gui.CreateWindowEx(
            0,
            self._CANVAS_CLASS,
            "Canvas",
            can_style,
            0,
            0,
            self.canvas_w,
            self.canvas_h,
            self.hwnd_viewport,
            0,
            hinstance,
            None,
        )
        self._instance_map[self.hwnd_canvas] = self

    def _viewport_wndproc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_SIZE:
            w = win32api.LOWORD(lparam)
            h = win32api.HIWORD(lparam)
            self.on_resize(w, h)
            return 0
        elif msg == win32con.WM_VSCROLL:
            scroll_code = win32api.LOWORD(wparam)
            pos = win32api.HIWORD(wparam)
            self._handle_scroll(win32con.SB_VERT, scroll_code, pos)
            return 0
        elif msg == win32con.WM_HSCROLL:
            scroll_code = win32api.LOWORD(wparam)
            pos = win32api.HIWORD(wparam)
            self._handle_scroll(win32con.SB_HORZ, scroll_code, pos)
            return 0
        elif msg == win32con.WM_MOUSEWHEEL:
            return self.handle_mousewheel(wparam)
        elif msg == win32con.WM_CLOSE and self.is_popup:
            self.set_visible(False)
            return 0
        elif msg == win32con.WM_DESTROY:
            self._cleanup_fonts()
            self._instance_map.pop(self.hwnd_viewport, None)
            self._instance_map.pop(self.hwnd_canvas, None)

        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _canvas_wndproc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_MOUSEWHEEL:
            return self.handle_mousewheel(wparam)
        elif msg == win32con.WM_COMMAND:
            if self.parent_hwnd:
                return win32gui.SendMessage(self.parent_hwnd, msg, wparam, lparam)
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _cleanup_fonts(self):
        for hfont in self._font_handles:
            try:
                win32gui.DeleteObject(hfont)
            except Exception:
                pass
        self._font_handles.clear()

    # -------------------------------------------------------------------------
    # Visibility & Layout Management
    # -------------------------------------------------------------------------

    def set_visible(self, visible: bool):
        cmd = win32con.SW_SHOW if visible else win32con.SW_HIDE
        flags = (
            win32con.SWP_NOMOVE
            | win32con.SWP_NOSIZE
            | win32con.SWP_NOACTIVATE
            | (win32con.SWP_SHOWWINDOW if visible else (win32con.SWP_HIDEWINDOW | win32con.SWP_NOZORDER))
        )
        win32gui.ShowWindow(self.hwnd_viewport, cmd)
        win32gui.SetWindowPos(self.hwnd_viewport, win32con.HWND_TOP, 0, 0, 0, 0, flags)

        win32gui.ShowWindow(self.hwnd_canvas, cmd)
        win32gui.SetWindowPos(self.hwnd_canvas, win32con.HWND_TOP, 0, 0, 0, 0, flags)

    def set_viewport_bounds(self, x: int, y: int, w: int, h: int):
        self.viewport_x = x
        self.viewport_y = y
        self.viewport_w = w
        self.viewport_h = h
        win32gui.SetWindowPos(
            self.hwnd_viewport,
            0,
            x,
            y,
            w,
            h,
            win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE,
        )

    def set_canvas_size(self, w: int, h: int):
        self.canvas_w = w
        self.canvas_h = h
        self.base_canvas_w = w
        self.base_canvas_h = h
        if self.zoom_type == CANVASZOOMTYPE_MIN:
            self.min_w = w
            self.min_h = h
        win32gui.SetWindowPos(
            self.hwnd_canvas,
            0,
            -self.scroll_x,
            -self.scroll_y,
            w,
            h,
            win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE,
        )
        self.on_resize(self.viewport_w, self.viewport_h)

    # -------------------------------------------------------------------------
    # Resizing & Scrollbar Math (__GenCanvas_WM_SIZE & __Canvas_CheckScrollPos)
    # -------------------------------------------------------------------------

    def on_resize(self, new_vp_w: int = None, new_vp_h: int = None):
        if new_vp_w is not None and new_vp_h is not None:
            self.viewport_w = new_vp_w
            self.viewport_h = new_vp_h
        else:
            left, top, right, bottom = win32gui.GetClientRect(self.hwnd_viewport)
            self.viewport_w = right - left
            self.viewport_h = bottom - top

        sb_w = win32api.GetSystemMetrics(win32con.SM_CXVSCROLL)
        sb_h = win32api.GetSystemMetrics(win32con.SM_CYHSCROLL)

        if self.zoom_type == CANVASZOOMTYPE_MIN:
            if self.canvas_h <= self.viewport_h:
                sb_w = 0
            if self.canvas_w <= self.viewport_w:
                sb_h = 0

        old_w, old_h = self.canvas_w, self.canvas_h

        self.scroll_y, page_h, min_h, max_h, self.canvas_h = self._check_scroll_pos(
            self.scroll_y, self.canvas_h, self.viewport_h, self.min_h, self.zoom_type, sb_h
        )
        self.scroll_x, page_w, min_w, max_w, self.canvas_w = self._check_scroll_pos(
            self.scroll_x,
            self.canvas_w,
            self.viewport_w,
            self.min_w,
            self.zoom_type,
            0 if max_h == 0 else sb_w,
        )
        if max_w == 0:
            self.scroll_y, page_h, min_h, max_h, self.canvas_h = self._check_scroll_pos(
                self.scroll_y, self.canvas_h, self.viewport_h, self.min_h, self.zoom_type, 0
            )

        if self.canvas_w != old_w or self.canvas_h != old_h:
            win32gui.SetWindowPos(
                self.hwnd_canvas,
                0,
                -self.scroll_x,
                -self.scroll_y,
                self.canvas_w,
                self.canvas_h,
                win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE,
            )
        else:
            win32gui.SetWindowPos(
                self.hwnd_canvas,
                0,
                -self.scroll_x,
                -self.scroll_y,
                0,
                0,
                win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE,
            )

        self._update_scrollbar_metrics(
            self.hwnd_viewport, win32con.SB_HORZ, min_w, max_w, page_w, abs(self.scroll_x)
        )
        self._update_scrollbar_metrics(
            self.hwnd_viewport, win32con.SB_VERT, min_h, max_h, page_h, abs(self.scroll_y)
        )

    @staticmethod
    def _check_scroll_pos(pos, canvas_len, view_len, canvas_min, zoom_type, sb_len=0):
        view_len_sb = int(view_len) - int(sb_len)
        pos_min = 0
        pos_max = 0
        page = 1
        s_min = 0
        s_max = 0

        if canvas_len < view_len_sb:
            if zoom_type == CANVASZOOMTYPE_MIN:
                if canvas_min <= view_len_sb:
                    canvas_len = view_len
                    pos_min = 0
                    pos_max = 0
                    page = 1
                    s_min = 0
                    s_max = 0
                    pos = 0
                else:
                    canvas_len = canvas_min
            else:
                pos_min = -view_len_sb
                pos_max = 0
                page = canvas_len
                s_min = 0
                s_max = view_len_sb

        if canvas_len >= view_len_sb:
            if zoom_type == CANVASZOOMTYPE_MIN:
                canvas_len = canvas_min if view_len_sb < canvas_min else view_len_sb
            pos_min = 0
            pos_max = canvas_len
            page = view_len_sb
            s_min = 0
            s_max = canvas_len
            if (canvas_len - view_len) <= sb_len:
                s_max = 0
                pos_max = 0

        if pos < pos_min:
            pos = pos_min
        if pos > pos_max:
            pos = pos_max

        return pos, page, s_min, s_max, canvas_len

    @staticmethod
    def _update_scrollbar_metrics(hwnd, bar, s_min, s_max, page, pos):
        si = SCROLLINFO()
        si.cbSize = ctypes.sizeof(SCROLLINFO)
        si.fMask = win32con.SIF_RANGE | win32con.SIF_PAGE | win32con.SIF_POS
        si.nMin = int(s_min)
        si.nMax = int(s_max)
        si.nPage = int(page)
        si.nPos = int(pos)
        ctypes.windll.user32.SetScrollInfo(hwnd, bar, ctypes.byref(si), True)

    def _handle_scroll(self, bar, scroll_code, track_pos):
        si = SCROLLINFO()
        si.cbSize = ctypes.sizeof(SCROLLINFO)
        si.fMask = win32con.SIF_ALL
        ctypes.windll.user32.GetScrollInfo(self.hwnd_viewport, bar, ctypes.byref(si))

        s_min = si.nMin
        s_max = si.nMax
        page = si.nPage
        cur_pos = si.nPos
        live_track = si.nTrackPos

        new_pos = cur_pos
        if scroll_code == win32con.SB_LINEUP:
            new_pos -= 20
        elif scroll_code == win32con.SB_LINEDOWN:
            new_pos += 20
        elif scroll_code == win32con.SB_PAGEUP:
            new_pos -= page
        elif scroll_code == win32con.SB_PAGEDOWN:
            new_pos += page
        elif scroll_code in (win32con.SB_THUMBPOSITION, win32con.SB_THUMBTRACK):
            new_pos = live_track

        max_scrollable = max(s_min, s_max - page)
        new_pos = max(s_min, min(new_pos, max_scrollable))

        if cur_pos == new_pos:
            return

        if bar == win32con.SB_HORZ:
            if self.viewport_w > self.canvas_w:
                new_pos = -new_pos
            new_pos, _, _, _, _ = self._check_scroll_pos(
                new_pos, self.canvas_w, self.viewport_w, self.min_w, CANVASZOOMTYPE_FREE, 0
            )
            self.scroll_x = new_pos
        elif bar == win32con.SB_VERT:
            if self.viewport_h > self.canvas_h:
                new_pos = -new_pos
            new_pos, _, _, _, _ = self._check_scroll_pos(
                new_pos, self.canvas_h, self.viewport_h, self.min_h, CANVASZOOMTYPE_FREE, 0
            )
            self.scroll_y = new_pos

        si_pos = SCROLLINFO()
        si_pos.cbSize = ctypes.sizeof(SCROLLINFO)
        si_pos.fMask = win32con.SIF_POS
        si_pos.nPos = abs(int(new_pos))
        ctypes.windll.user32.SetScrollInfo(self.hwnd_viewport, bar, ctypes.byref(si_pos), True)

        win32gui.SetWindowPos(
            self.hwnd_canvas,
            0,
            -self.scroll_x,
            -self.scroll_y,
            0,
            0,
            win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE,
        )

    def handle_mousewheel(self, wparam):
        delta = ctypes.c_short(win32api.HIWORD(wparam)).value
        modifiers = win32api.LOWORD(wparam)

        if (modifiers & win32con.MK_CONTROL) == win32con.MK_CONTROL:
            zoom_adj = 0.05 if delta >= 0 else -0.05
            self.adjust_zoom(zoom_adj)
            self.on_resize()
        else:
            scroll_code = win32con.SB_LINEUP if delta > 0 else win32con.SB_LINEDOWN
            for _ in range(3):
                self._handle_scroll(win32con.SB_VERT, scroll_code, 0)
        return 0

    # -------------------------------------------------------------------------
    # Popout / Pop-in Detachment (__Canvas_Popout & __Canvas_PopIn)
    # -------------------------------------------------------------------------

    def popout(self, title: str = "Detached View"):
        old_style = win32gui.GetWindowLong(self.hwnd_viewport, win32con.GWL_STYLE)
        new_style = (
            old_style
            | win32con.WS_CAPTION
            | win32con.WS_THICKFRAME
            | win32con.WS_SYSMENU
            | win32con.WS_MAXIMIZEBOX
        ) & ~win32con.WS_CHILD

        win32gui.SetWindowLong(self.hwnd_viewport, win32con.GWL_STYLE, new_style)
        win32gui.SetParent(self.hwnd_viewport, 0)
        win32gui.SetWindowText(self.hwnd_viewport, title)

        left, top, right, bottom = win32gui.GetWindowRect(self.hwnd_viewport)
        w = (right - left) + 100
        h = (bottom - top) + 100

        win32gui.SetWindowPos(
            self.hwnd_viewport,
            0,
            left + 50,
            top + 50,
            w,
            h,
            win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE | win32con.SWP_FRAMECHANGED,
        )
        self.is_popup = True

    def popin(self, parent_hwnd: int, x: int, y: int, w: int, h: int):
        old_style = win32gui.GetWindowLong(self.hwnd_viewport, win32con.GWL_STYLE)
        strip_flags = (
            win32con.WS_CAPTION
            | win32con.WS_THICKFRAME
            | win32con.WS_SYSMENU
            | win32con.WS_MAXIMIZEBOX
        )
        new_style = (old_style | win32con.WS_CHILD) & ~strip_flags

        win32gui.SetWindowLong(self.hwnd_viewport, win32con.GWL_STYLE, new_style)
        win32gui.SetParent(self.hwnd_viewport, parent_hwnd)
        self.parent_hwnd = parent_hwnd
        self.is_popup = False

        win32gui.SetWindowPos(
            self.hwnd_viewport,
            0,
            x,
            y,
            w,
            h,
            win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE | win32con.SWP_FRAMECHANGED,
        )
        win32gui.RedrawWindow(
            parent_hwnd,
            None,
            None,
            win32con.RDW_INVALIDATE | win32con.RDW_UPDATENOW | win32con.RDW_ALLCHILDREN,
        )

    # -------------------------------------------------------------------------
    # Zoom Cataloging & Scaling (__Canvas_ZoomCatalog & __Canvas_SetZoom)
    # -------------------------------------------------------------------------

    def catalog_controls(self):
        """Enumerates all child controls inside hwnd_canvas and records their base geometry and font size."""
        self.base_canvas_w = self.canvas_w
        self.base_canvas_h = self.canvas_h
        self.cataloged_controls.clear()

        def enum_cb(hwnd, _):
            if win32gui.GetParent(hwnd) == self.hwnd_canvas:
                rect = win32gui.GetWindowRect(hwnd)
                pt_tl = win32gui.ScreenToClient(self.hwnd_canvas, (rect[0], rect[1]))
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                font_pt = self._get_control_font_size(hwnd)
                self.cataloged_controls.append(
                    {
                        "hwnd": hwnd,
                        "x": pt_tl[0],
                        "y": pt_tl[1],
                        "w": w,
                        "h": h,
                        "font_size": font_pt,
                    }
                )
            return True

        win32gui.EnumChildWindows(self.hwnd_canvas, enum_cb, None)

    def adjust_zoom(self, delta: float):
        new_scale = self.zoom_scale + delta
        if 0.97 < new_scale < 1.03:
            new_scale = 1.0
        return self.set_zoom(new_scale)

    def set_zoom(self, new_scale: float):
        if not self.cataloged_controls:
            self.catalog_controls()

        new_scale = max(0.1, min(10.0, float(new_scale)))
        self.zoom_scale = new_scale

        new_w = int(self.base_canvas_w * new_scale)
        new_h = int(self.base_canvas_h * new_scale)
        self.canvas_w = new_w
        self.canvas_h = new_h

        win32gui.SetWindowPos(
            self.hwnd_canvas,
            0,
            -self.scroll_x,
            -self.scroll_y,
            new_w,
            new_h,
            win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE,
        )

        old_fonts = list(self._font_handles)
        self._font_handles.clear()

        for ctrl in self.cataloged_controls:
            hwnd = ctrl["hwnd"]
            cx = int(ctrl["x"] * new_scale)
            cy = int(ctrl["y"] * new_scale)
            cw = int(ctrl["w"] * new_scale)
            ch = int(ctrl["h"] * new_scale)

            win32gui.SetWindowPos(
                hwnd,
                0,
                cx,
                cy,
                cw,
                ch,
                win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE | win32con.SWP_NOREDRAW,
            )

            if ctrl["font_size"] and ctrl["font_size"] > 0:
                scaled_pt = max(1, int(ctrl["font_size"] * new_scale))
                self._set_control_font_size(hwnd, scaled_pt)

        for hfont in old_fonts:
            try:
                win32gui.DeleteObject(hfont)
            except Exception:
                pass

        win32gui.RedrawWindow(
            self.hwnd_canvas,
            None,
            None,
            win32con.RDW_INVALIDATE | win32con.RDW_ALLCHILDREN,
        )
        return self.zoom_scale

    @staticmethod
    def _get_control_font_size(hwnd) -> int:
        hfont = win32gui.SendMessage(hwnd, win32con.WM_GETFONT, 0, 0)
        if not hfont:
            hfont = win32gui.GetStockObject(win32con.DEFAULT_GUI_FONT)
        lf = LOGFONTW()
        if ctypes.windll.gdi32.GetObjectW(hfont, ctypes.sizeof(LOGFONTW), ctypes.byref(lf)):
            hdc = win32gui.GetDC(hwnd)
            dpi_y = ctypes.windll.gdi32.GetDeviceCaps(hdc, win32con.LOGPIXELSY)
            win32gui.ReleaseDC(hwnd, hdc)
            return round((abs(lf.lfHeight) * 72) / dpi_y)
        return 9

    def _set_control_font_size(self, hwnd, point_size: int):
        hfont = win32gui.SendMessage(hwnd, win32con.WM_GETFONT, 0, 0)
        if not hfont:
            hfont = win32gui.GetStockObject(win32con.DEFAULT_GUI_FONT)
        lf = LOGFONTW()
        if not ctypes.windll.gdi32.GetObjectW(hfont, ctypes.sizeof(LOGFONTW), ctypes.byref(lf)):
            return
        hdc = win32gui.GetDC(hwnd)
        dpi_y = ctypes.windll.gdi32.GetDeviceCaps(hdc, win32con.LOGPIXELSY)
        win32gui.ReleaseDC(hwnd, hdc)

        lf.lfHeight = -round((point_size * dpi_y) / 72)
        new_hfont = ctypes.windll.gdi32.CreateFontIndirectW(ctypes.byref(lf))
        if new_hfont:
            self._font_handles.append(new_hfont)
            win32gui.SendMessage(hwnd, win32con.WM_SETFONT, new_hfont, False)


# =============================================================================
# Example Usage
# =============================================================================
if __name__ == "__main__":
    def main_wndproc(hwnd, msg, wparam, lparam):
        if msg == win32con.WM_SIZE and hasattr(main_wndproc, "vp"):
            w = win32api.LOWORD(lparam)
            h = win32api.HIWORD(lparam)
            main_wndproc.vp.set_viewport_bounds(10, 10, max(50, w - 20), max(50, h - 20))
            return 0
        elif msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    hinst = win32api.GetModuleHandle(None)
    wc = win32gui.WNDCLASS()
    wc.lpfnWndProc = main_wndproc
    wc.hInstance = hinst
    wc.lpszClassName = "DemoMainHost"
    wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
    wc.hbrBackground = win32con.COLOR_APPWORKSPACE + 1
    win32gui.RegisterClass(wc)

    hwnd_main = win32gui.CreateWindowEx(
        0,
        "DemoMainHost",
        "Win32 Viewport & Canvas Demo (Ctrl+Wheel to Zoom, Wheel to Scroll)",
        win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE,
        100,
        100,
        640,
        480,
        0,
        0,
        hinst,
        None,
    )

    # Create viewport (600x420) hosting a larger scrollable canvas (1200x900)
    vp = Win32ViewportCanvas(
        parent_hwnd=hwnd_main,
        x=10,
        y=10,
        viewport_w=600,
        viewport_h=420,
        canvas_w=1200,
        canvas_h=900,
        zoom_type=CANVASZOOMTYPE_FREE,
    )
    main_wndproc.vp = vp

    # Populate sample Win32 child controls onto vp.hwnd_canvas
    for row in range(10):
        for col in range(6):
            btn_x = 20 + col * 190
            btn_y = 20 + row * 80
            win32gui.CreateWindowEx(
                0,
                "BUTTON",
                f"Button ({row}, {col})",
                win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.BS_PUSHBUTTON,
                btn_x,
                btn_y,
                160,
                40,
                vp.hwnd_canvas,
                1000 + row * 10 + col,
                hinst,
                None,
            )

    # Catalog controls so Ctrl+MouseWheel scales them cleanly
    vp.catalog_controls()

    win32gui.PumpMessages()
