import ctypes
import json
import math
import os
import random
import sys
import time
from ctypes import wintypes as wt

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "site"))

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:
    ctypes.windll.user32.MessageBoxW(None, "缺少 Pillow，请执行：pip install pillow", "宵崎奏", 0)
    sys.exit(1)

SPRITE_PATH = os.path.join(BASE, "assets", "kanade.png")
STATE_PATH = os.path.join(BASE, "pet_state.json")
PET_HEIGHT = 210
FRAME_MS = 33
IDLE_SLEEP = 140
DEBUG = bool(os.environ.get("PET_DEBUG"))

def dbg(*a):
    if DEBUG:
        print("[pet]", *a, flush=True)
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhl.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
]

LINES = [
    "……曲子，还差一点点。",
    "要听一下吗？刚写的。",
    "拉面……想吃。",
    "别熬夜了。……我也没资格说这话。",
    "谢谢你陪我。",
    "再写五分钟就睡，真的。",
    "有点吵……不过，还好。",
    "今天的和弦，好像不太对。",
    "你把窗户关了吗？有点冷。",
    "唔……在听。",
]
CLICK_LINES = ["……嗯？", "别戳啦。", "我在想旋律。", "……有点痒。", "再戳就写不出曲子了。"]
WAKE_LINES = ["……唔，我醒了。", "几点了……？", "啊，睡着了。"]
SLEEP_LINES = ["Zzz……", "……zzZ"]
GREET_LINES = ["……啊，你来了。", "今天也在这里写曲子。", "嗯，我在。"]
NOTE_COLORS = [(255, 255, 255, 245), (255, 168, 205, 245), (150, 195, 255, 245)]

WS_POPUP, WS_VISIBLE = 0x80000000, 0x10000000
WS_EX_LAYERED, WS_EX_TOOLWINDOW, WS_EX_TOPMOST = 0x00080000, 0x00000080, 0x00000008
ULW_ALPHA, AC_SRC_OVER, AC_SRC_ALPHA = 2, 0, 1
DIB_RGB_COLORS, BI_RGB = 0, 0
WM_DESTROY, WM_TIMER, WM_NULL, WM_CLOSE = 0x0002, 0x0113, 0x0000, 0x0010
WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP, WM_RBUTTONUP = 0x0200, 0x0201, 0x0202, 0x0205
WM_CAPTURECHANGED = 0x0215
SWP_NOSIZE, SWP_NOMOVE, SWP_NOZORDER, SWP_NOACTIVATE = 0x0001, 0x0002, 0x0004, 0x0010
HWND_TOPMOST, HWND_NOTOPMOST = -1, -2
MF_STRING, MF_SEPARATOR, MF_CHECKED = 0x0000, 0x0800, 0x0008
TPM_RETURNCMD, TPM_RIGHTBUTTON = 0x0100, 0x0002
SPI_GETWORKAREA = 0x0030
IDC_ARROW = 32512

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)

class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [("cbSize", wt.UINT), ("style", wt.UINT), ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                ("hInstance", wt.HINSTANCE), ("hIcon", wt.HICON), ("hCursor", wt.HANDLE),
                ("hbrBackground", wt.HBRUSH), ("lpszMenuName", wt.LPCWSTR),
                ("lpszClassName", wt.LPCWSTR), ("hIconSm", wt.HICON)]

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", ctypes.c_long), ("biHeight", ctypes.c_long),
                ("biPlanes", wt.WORD), ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wt.DWORD),
                ("biClrImportant", wt.DWORD)]

class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wt.DWORD * 3)]

class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [("BlendOp", ctypes.c_ubyte), ("BlendFlags", ctypes.c_ubyte),
                ("SourceConstantAlpha", ctypes.c_ubyte), ("AlphaFormat", ctypes.c_ubyte)]

def _proto(fn, restype, *argtypes):
    fn.restype = restype
    fn.argtypes = list(argtypes)
    return fn

kernel32.GetModuleHandleW = _proto(kernel32.GetModuleHandleW, wt.HMODULE, wt.LPCWSTR)
user32.DefWindowProcW = _proto(user32.DefWindowProcW, ctypes.c_ssize_t,
                               wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
user32.CreateWindowExW = _proto(user32.CreateWindowExW, wt.HWND, wt.DWORD, wt.LPCWSTR, wt.LPCWSTR,
                                wt.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                wt.HWND, wt.HMENU, wt.HINSTANCE, wt.LPVOID)
user32.UpdateLayeredWindow = _proto(user32.UpdateLayeredWindow, wt.BOOL, wt.HWND, wt.HDC,
                                    ctypes.POINTER(wt.POINT), ctypes.POINTER(wt.SIZE), wt.HDC,
                                    ctypes.POINTER(wt.POINT), wt.DWORD,
                                    ctypes.POINTER(BLENDFUNCTION), wt.DWORD)
user32.GetDC = _proto(user32.GetDC, wt.HDC, wt.HWND)
user32.ReleaseDC = _proto(user32.ReleaseDC, ctypes.c_int, wt.HWND, wt.HDC)
user32.LoadCursorW = _proto(user32.LoadCursorW, wt.HANDLE, wt.HINSTANCE, wt.LPCWSTR)
user32.SetTimer = _proto(user32.SetTimer, ctypes.c_size_t, wt.HWND, ctypes.c_size_t,
                         wt.UINT, wt.LPVOID)
user32.SetWindowPos = _proto(user32.SetWindowPos, wt.BOOL, wt.HWND, wt.HWND,
                             ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT)
user32.DestroyWindow = _proto(user32.DestroyWindow, wt.BOOL, wt.HWND)
user32.SetForegroundWindow = _proto(user32.SetForegroundWindow, wt.BOOL, wt.HWND)
user32.PostMessageW = _proto(user32.PostMessageW, wt.BOOL, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
user32.PostQuitMessage = _proto(user32.PostQuitMessage, None, ctypes.c_int)
user32.GetMessageW = _proto(user32.GetMessageW, wt.BOOL, ctypes.POINTER(wt.MSG), wt.HWND,
                            wt.UINT, wt.UINT)
user32.TranslateMessage = _proto(user32.TranslateMessage, wt.BOOL, ctypes.POINTER(wt.MSG))
user32.DispatchMessageW = _proto(user32.DispatchMessageW, ctypes.c_ssize_t, ctypes.POINTER(wt.MSG))
user32.CreatePopupMenu = _proto(user32.CreatePopupMenu, wt.HMENU)
user32.AppendMenuW = _proto(user32.AppendMenuW, wt.BOOL, wt.HMENU, wt.UINT,
                            ctypes.c_size_t, wt.LPCWSTR)
user32.TrackPopupMenu = _proto(user32.TrackPopupMenu, ctypes.c_int, wt.HMENU, wt.UINT,
                               ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.HWND, wt.LPVOID)
user32.DestroyMenu = _proto(user32.DestroyMenu, wt.BOOL, wt.HMENU)
user32.SetCapture = _proto(user32.SetCapture, wt.HWND, wt.HWND)
user32.ReleaseCapture = _proto(user32.ReleaseCapture, wt.BOOL)
gdi32.CreateDIBSection = _proto(gdi32.CreateDIBSection, wt.HBITMAP, wt.HDC,
                                ctypes.POINTER(BITMAPINFO), wt.UINT,
                                ctypes.POINTER(ctypes.c_void_p), wt.HANDLE, wt.DWORD)
gdi32.CreateCompatibleDC = _proto(gdi32.CreateCompatibleDC, wt.HDC, wt.HDC)
gdi32.SelectObject = _proto(gdi32.SelectObject, wt.HGDIOBJ, wt.HDC, wt.HGDIOBJ)
gdi32.GetDeviceCaps = _proto(gdi32.GetDeviceCaps, ctypes.c_int, wt.HDC, ctypes.c_int)

def enable_dpi_awareness():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass

def system_dpi():
    try:
        return user32.GetDpiForSystem()
    except Exception:
        hdc = user32.GetDC(None)
        dpi = gdi32.GetDeviceCaps(hdc, 88)
        user32.ReleaseDC(None, hdc)
        return dpi or 96

def work_area():
    r = wt.RECT()
    user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(r), 0)
    return r.left, r.top, r.right, r.bottom

def load_font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()

def make_shadow(w, h):
    m = max(2, int(h * 0.45))
    im = Image.new("L", (w, h), 0)
    ImageDraw.Draw(im).ellipse([m, m, w - m, h - m], fill=255)
    im = im.filter(ImageFilter.GaussianBlur(m * 0.8))
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.putalpha(im.point(lambda v: int(v * 0.42)))
    return out

def make_note(size, color, outline=(40, 44, 62, 230)):
    ss = 4
    W, H = int(size * 1.1) * ss, int(size * 1.5) * ss
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    hw, hh = W * 0.40, H * 0.21
    hx, hy = W * 0.10, H - hh * 1.35
    d.ellipse([hx, hy, hx + hw, hy + hh], fill=255)
    stem_x = hx + hw * 0.86
    stem_w = max(2, W * 0.065)
    d.rectangle([stem_x, H * 0.12, stem_x + stem_w, hy + hh * 0.55], fill=255)
    d.polygon([(stem_x + stem_w, H * 0.12),
               (stem_x + W * 0.34, H * 0.25),
               (stem_x + W * 0.30, H * 0.36),
               (stem_x + stem_w, H * 0.28)], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(ss * 0.35))

    ow = max(2, int(ss * 1.3))
    edge = mask.filter(ImageFilter.MaxFilter(ow * 2 + 1))

    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    layer = Image.new("RGBA", (W, H), outline)
    im.paste(layer, (0, 0), edge)
    fill = Image.new("RGBA", (W, H), color)
    im.paste(fill, (0, 0), mask)
    return im.resize((W // ss, H // ss), Image.LANCZOS)

class Bubble:

    def __init__(self, scale):
        self.size = int(13 * scale)
        self.font = load_font(self.size)
        self.pad_x, self.pad_y = int(13 * scale), int(9 * scale)
        self.radius, self.tail = int(12 * scale), int(9 * scale)
        self.max_w = int(186 * scale)
        self.line_h = int(self.size * 1.45)

    def _wrap(self, text):
        lines, cur = [], ""
        for ch in text:
            if ch == "\n":
                lines.append(cur)
                cur = ""
                continue
            if self.font.getlength(cur + ch) > self.max_w and cur:
                lines.append(cur)
                cur = ch
            else:
                cur += ch
        if cur or not lines:
            lines.append(cur)
        return lines

    def render(self, text):
        ss = 3
        lines = self._wrap(text)
        font = load_font(self.size * ss)
        tw = max(font.getlength(l) for l in lines) / ss
        bw = int(tw + self.pad_x * 2)
        bh = int(self.line_h * len(lines) + self.pad_y * 2)
        W, H = (bw + 2) * ss, (bh + self.tail + 2) * ss

        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        box = [ss, ss, W - ss - 1, H - self.tail * ss - ss]
        d.rounded_rectangle(box, radius=self.radius * ss, fill=(253, 253, 255, 246),
                            outline=(148, 158, 190, 255), width=ss)
        tx = W // 2
        d.polygon([(tx - 7 * ss, box[3] - ss), (tx + 7 * ss, box[3] - ss),
                   (tx, box[3] + self.tail * ss - 2 * ss)], fill=(253, 253, 255, 246))
        d.line([(tx - 7 * ss, box[3] - ss), (tx, box[3] + self.tail * ss - 2 * ss),
                (tx + 7 * ss, box[3] - ss)], fill=(148, 158, 190, 255), width=ss)
        d.line([(tx - 7 * ss + ss, box[3] - ss), (tx + 7 * ss - ss, box[3] - ss)],
               fill=(253, 253, 255, 246), width=ss * 2)
        ty = box[1] + self.pad_y * ss - ss
        for line in lines:
            d.text((W // 2, ty), line, font=font, fill=(38, 42, 58, 255), anchor="mt")
            ty += self.line_h * ss

        shadow = layer.filter(ImageFilter.GaussianBlur(3 * ss))
        shadow.putalpha(shadow.split()[3].point(lambda v: int(v * 0.20)))
        big = Image.new("RGBA", (W + 12 * ss, H + 12 * ss), (0, 0, 0, 0))
        big.alpha_composite(shadow, (6 * ss, 8 * ss))
        big.alpha_composite(layer, (6 * ss, 6 * ss))
        return big.resize((big.width // ss, big.height // ss), Image.LANCZOS)

class Pet:
    def __init__(self):
        enable_dpi_awareness()
        self.scale = max(0.9, min(2.6, system_dpi() / 96.0))

        raw = Image.open(SPRITE_PATH).convert("RGBA")
        h = int(PET_HEIGHT * self.scale)
        w = max(1, int(raw.width * h / raw.height))
        char = raw.resize((w, h), Image.LANCZOS)

        self.pad = int(34 * self.scale)
        self.spr = Image.new("RGBA", (w + self.pad * 2, h + self.pad * 2), (0, 0, 0, 0))
        self.spr.paste(char, (self.pad, self.pad), char)
        self.char_w, self.char_h = w, h
        self.spr_h = self.spr.height
        self.pivot_ratio = (self.pad + h) / float(self.spr.height)

        self.canvas_w = max(w + self.pad * 2, int(236 * self.scale))
        self.canvas_h = h + int(190 * self.scale)
        self.bottom_margin = int(24 * self.scale)
        self.base_y = self.canvas_h - self.bottom_margin

        self.shadow = make_shadow(int(w * 0.9), int(24 * self.scale))
        self.notes = [make_note(int(14 * self.scale), c) for c in NOTE_COLORS]
        self.bubble = Bubble(self.scale)

        self.t0 = time.time()
        self.last = self.t0
        self.alpha = 0
        self._last_img = None
        self.dragging = False
        self.drag_moved = False
        self.drag_tilt = 0.0
        self.hop_t = None
        self.sleeping = False
        self.last_touch = time.time()
        self.particles = []
        self.bubble_text = ""
        self.bubble_until = 0.0
        self.bubble_cache = (None, None)
        self.next_chatter = time.time() + random.uniform(25, 50)
        self.next_note = time.time() + 2.5
        self.topmost = True

        st = self._load_state()
        wa = work_area()
        self.w, self.h = self.canvas_w, self.canvas_h
        self.x = st.get("x", wa[2] - self.w - int(30 * self.scale))
        self.y = st.get("y", wa[3] - self.h - int(4 * self.scale))
        self._clamp_to_screen()
        self._create_window()
        self.say(random.choice(GREET_LINES), hold=4.0)

    def _load_state(self):
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_state(self):
        try:
            with open(STATE_PATH, "w", encoding="utf-8") as f:
                json.dump({"x": self.x, "y": self.y}, f)
        except Exception:
            pass

    def _clamp_to_screen(self):
        l, t, r, b = work_area()
        self.x = max(l - self.w // 2, min(self.x, r - self.w // 2))
        self.y = max(t - self.h // 2, min(self.y, b - self.h // 2))

    def _create_window(self):
        self._proc = WNDPROC(self._wndproc)
        hinst = kernel32.GetModuleHandleW(None)
        cls = "KanadePetWindow"
        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.lpfnWndProc = self._proc
        wc.hInstance = hinst
        wc.hCursor = user32.LoadCursorW(None, ctypes.cast(IDC_ARROW, wt.LPCWSTR))
        wc.lpszClassName = cls
        user32.RegisterClassExW(ctypes.byref(wc))

        self.hwnd = user32.CreateWindowExW(
            WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_TOPMOST, cls, "宵崎奏",
            WS_POPUP | WS_VISIBLE, self.x, self.y, self.w, self.h, None, None, hinst, None)
        if not self.hwnd:
            raise OSError("创建窗口失败：%d" % ctypes.get_last_error())

        self.screen_dc = user32.GetDC(None)
        self.mem_dc = gdi32.CreateCompatibleDC(self.screen_dc)
        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = self.w
        bmi.bmiHeader.biHeight = -self.h
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB
        self.bits = ctypes.c_void_p()
        self.hbmp = gdi32.CreateDIBSection(self.mem_dc, ctypes.byref(bmi), DIB_RGB_COLORS,
                                           ctypes.byref(self.bits), None, 0)
        gdi32.SelectObject(self.mem_dc, self.hbmp)
        user32.SetTimer(self.hwnd, 1, FRAME_MS, None)

    def _blit(self, img):
        buf = img.convert("RGBa").tobytes("raw", "BGRa")
        ctypes.memmove(self.bits, buf, len(buf))
        blend = BLENDFUNCTION(AC_SRC_OVER, 0, self.alpha, AC_SRC_ALPHA)
        pt_dst = wt.POINT(self.x, self.y)
        pt_src = wt.POINT(0, 0)
        size = wt.SIZE(self.w, self.h)
        user32.UpdateLayeredWindow(self.hwnd, self.screen_dc, ctypes.byref(pt_dst),
                                   ctypes.byref(size), self.mem_dc, ctypes.byref(pt_src),
                                   0, ctypes.byref(blend), ULW_ALPHA)

    def _move_window(self, x, y):
        self.x, self.y = int(x), int(y)
        dbg("move", self.x, self.y)
        if getattr(self, "_last_img", None) is not None:
            self._blit(self._last_img)
        else:
            user32.SetWindowPos(self.hwnd, None, self.x, self.y, 0, 0,
                                SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE)

    def _wndproc(self, hwnd, msg, wparam, lparam):
        try:
            if msg == WM_TIMER:
                self.tick()
            elif msg == WM_LBUTTONDOWN:
                self._on_press()
            elif msg == WM_MOUSEMOVE and self.dragging:
                self._on_drag()
            elif msg == WM_LBUTTONUP:
                self._on_release()
            elif msg == WM_RBUTTONUP:
                self._show_menu()
            elif msg == WM_CAPTURECHANGED and self.dragging:
                self.dragging = False
                self.drag_tilt = 0.0
                self._save_state()
            elif msg == WM_CLOSE:
                self._save_state()
                return user32.DefWindowProcW(hwnd, msg, wparam, lparam)
            elif msg == WM_DESTROY:
                user32.PostQuitMessage(0)
            else:
                return user32.DefWindowProcW(hwnd, msg, wparam, lparam)
        except Exception as e:
            print("wndproc error:", repr(e))
        return 0

    def _cursor(self):
        pt = wt.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    def _on_press(self):
        self.dragging = True
        self.drag_moved = False
        user32.SetCapture(self.hwnd)
        dbg("press at", self._cursor(), "win", self.x, self.y)
        cx, cy = self._cursor()
        self._press_rel = (cx - self.x, cy - self.y)
        self._press_pos = (cx, cy)
        self._last_x = cx
        self._wake()

    def _on_drag(self):
        cx, cy = self._cursor()
        if abs(cx - self._press_pos[0]) + abs(cy - self._press_pos[1]) > 3:
            self.drag_moved = True
        self.drag_tilt = max(-14.0, min(14.0, (cx - self._last_x) * 1.8 + self.drag_tilt * 0.5))
        self._last_x = cx
        self._move_window(cx - self._press_rel[0], cy - self._press_rel[1])

    def _on_release(self):
        if not self.dragging:
            return
        self.dragging = False
        user32.ReleaseCapture()
        dbg("release moved=", self.drag_moved, "win", self.x, self.y)
        if self.drag_moved:
            self.drag_tilt = 0.0
            self._clamp_to_screen()
            self._move_window(self.x, self.y)
            self._save_state()
        else:
            self.hop_t = 0.0
            self.spawn_notes(4)
            self.say(random.choice(CLICK_LINES), hold=2.4)

    def _show_menu(self):
        hmenu = user32.CreatePopupMenu()
        user32.AppendMenuW(hmenu, MF_STRING, 1, "说句话")
        user32.AppendMenuW(hmenu, MF_STRING, 2, "叫醒她" if self.sleeping else "让她休息")
        user32.AppendMenuW(hmenu, MF_STRING | (MF_CHECKED if self.topmost else 0), 3, "总在最前")
        user32.AppendMenuW(hmenu, MF_STRING, 4, "回到右下角")
        user32.AppendMenuW(hmenu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(hmenu, MF_STRING, 5, "退出")

        cx, cy = self._cursor()
        user32.SetForegroundWindow(self.hwnd)
        cmd = user32.TrackPopupMenu(hmenu, TPM_RETURNCMD | TPM_RIGHTBUTTON, cx, cy, 0,
                                    self.hwnd, None)
        user32.PostMessageW(self.hwnd, WM_NULL, 0, 0)
        user32.DestroyMenu(hmenu)

        if cmd == 1:
            self._wake()
            self.say(random.choice(LINES), hold=4.0)
            self.spawn_notes(2)
        elif cmd == 2:
            if self.sleeping:
                self._wake()
                self.say(random.choice(WAKE_LINES), hold=3.0)
            else:
                self.sleeping = True
                self.say(random.choice(SLEEP_LINES), hold=3.0)
        elif cmd == 3:
            self.topmost = not self.topmost
            user32.SetWindowPos(self.hwnd, HWND_TOPMOST if self.topmost else HWND_NOTOPMOST,
                                0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
        elif cmd == 4:
            l, t, r, b = work_area()
            self._move_window(r - self.w - int(30 * self.scale), b - self.h - int(4 * self.scale))
            self._save_state()
        elif cmd == 5:
            self._save_state()
            user32.DestroyWindow(self.hwnd)

    def _wake(self):
        self.last_touch = time.time()
        self.sleeping = False

    def say(self, text, hold=3.5):
        self.bubble_text = text
        self.bubble_until = time.time() + hold + len(text) * 0.06
        self.bubble_cache = (None, None)

    def spawn_notes(self, n=1):
        for _ in range(n):
            side = random.choice((-1, 1))
            self.particles.append({
                "img": random.choice(self.notes),
                "x": self.canvas_w * 0.5 + side * random.uniform(self.canvas_w * 0.16, self.canvas_w * 0.33),
                "y": self.base_y - random.uniform(self.char_h * 0.25, self.char_h * 0.80),
                "vx": side * random.uniform(4, 16),
                "vy": random.uniform(-54, -30),
                "age": 0.0,
                "life": random.uniform(1.7, 2.7),
                "spin": random.uniform(-45, 45),
                "ang": random.uniform(0, 360),
            })

    def tick(self):
        now = time.time()
        dt = min(0.12, now - self.last)
        self.last = now
        t = now - self.t0

        if self.alpha < 255:
            self.alpha = min(255, self.alpha + 26)

        if not self.sleeping and now - self.last_touch > IDLE_SLEEP:
            self.sleeping = True
            self.say(random.choice(SLEEP_LINES), hold=3.0)

        if not self.sleeping and not self.dragging and now > self.next_chatter:
            self.say(random.choice(LINES), hold=4.0)
            self.next_chatter = now + random.uniform(45, 95)

        if now > self.next_note and not self.dragging:
            if self.sleeping:
                self.spawn_notes(1)
                self.next_note = now + random.uniform(5, 9)
            else:
                if random.random() < 0.5:
                    self.spawn_notes(1)
                self.next_note = now + random.uniform(4, 11)

        if self.hop_t is not None:
            self.hop_t += dt
            if self.hop_t > 0.62:
                self.hop_t = None

        self._last_img = self.compose(t, now, dt)
        self._blit(self._last_img)
    def compose(self, t, now, dt):
        canvas = Image.new("RGBA", (self.canvas_w, self.canvas_h), (0, 0, 0, 0))

        breath = math.sin(t * 2.0)
        sx = 1.0 - 0.010 * breath
        sy = 1.0 + 0.014 * breath
        sway = math.sin(t * 0.85) * (0.7 if self.sleeping else 1.4)

        hop_y, squash = 0.0, 1.0
        if self.hop_t is not None:
            p = self.hop_t / 0.62
            hop_y = -math.sin(p * math.pi) * self.char_h * 0.20
            squash = 1.0 - 0.09 * math.sin(p * math.pi * 2)
        if self.dragging:
            sway += self.drag_tilt

        nw = max(1, int(self.spr.width * sx))
        nh = max(1, int(self.spr.height * sy * squash))
        scaled = self.spr.resize((nw, nh), Image.BILINEAR)
        pv = nh * self.pivot_ratio
        rot = scaled.rotate(sway, resample=Image.BICUBIC, center=(nw * 0.5, pv))

        cx = self.canvas_w * 0.5
        base_y = self.base_y + hop_y
        canvas.paste(rot, (int(cx - nw * 0.5), int(base_y - pv)), rot)

        k = 1.0 if self.hop_t is None else max(0.5, 1.0 - abs(hop_y) / (self.char_h * 0.4))
        sw, shh = max(6, int(self.shadow.width * k)), max(3, int(self.shadow.height * k))
        sh = self.shadow.resize((sw, shh), Image.BILINEAR)
        if k < 0.999:
            sh.putalpha(sh.split()[3].point(lambda v: int(v * k)))
        canvas.paste(sh, (int(cx - sw / 2), int(self.base_y - shh * 0.55)), sh)

        alive = []
        for p in self.particles:
            p["age"] += dt
            if p["age"] >= p["life"]:
                continue
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["ang"] += p["spin"] * dt
            fade = 1.0 - p["age"] / p["life"]
            img = p["img"].rotate(p["ang"], resample=Image.BICUBIC, expand=True)
            img.putalpha(img.split()[3].point(lambda v, f=fade: int(v * f)))
            canvas.paste(img, (int(p["x"] - img.width / 2), int(p["y"] - img.height / 2)), img)
            alive.append(p)
        self.particles = alive

        if self.bubble_text and now < self.bubble_until:
            if self.bubble_cache[0] != self.bubble_text:
                self.bubble_cache = (self.bubble_text, self.bubble.render(self.bubble_text))
            img = self.bubble_cache[1]
            if now > self.bubble_until - 0.35:
                kk = max(0.0, (self.bubble_until - now) / 0.35)
                img = img.copy()
                img.putalpha(img.split()[3].point(lambda v, f=kk: int(v * f)))
            canvas.paste(img, (int(cx - img.width / 2),
                               int(base_y - self.char_h - img.height + 14)), img)
        return canvas

def main():
    from splash import run_gate
    if not run_gate():
        return
    pet = Pet()
    msg = wt.MSG()
    while True:
        r = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
        if r <= 0:
            break
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))
    pet._save_state()

if __name__ == "__main__":
    main()
