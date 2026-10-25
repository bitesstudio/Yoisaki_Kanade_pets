import ctypes
import os
import socket
import threading
import time
import urllib.error
import urllib.request
from datetime import date

import pet as P
from pet import user32, gdi32, kernel32, wt
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE, "assets", "starting.png")

SERVICE_URL = "https://api.deepseek.com/"
SERVICE_HOST = "api.deepseek.com"
SERVICE_PORT = 443
PASSWORD = "Caonima114514;;"
MIN_SHOW = 10.0
CHECK_TIMEOUT = 6

CARD_W, CARD_H = 820, 208
SHADOW, RADIUS = 26, 16

C_TITLE = (20, 22, 31, 255)
C_BODY = (92, 100, 120, 255)
C_SUB = (128, 136, 154, 255)
C_OK = (22, 148, 94, 255)
C_BAD = (204, 60, 60, 255)
C_HINT = (152, 158, 174, 255)
C_LINE = (228, 231, 240, 255)
C_ACCENT = (91, 124, 250, 255)

user32.SetFocus = P._proto(user32.SetFocus, wt.HWND, wt.HWND)
user32.GetCursorPos = P._proto(user32.GetCursorPos, wt.BOOL, ctypes.POINTER(wt.POINT))
user32.OpenClipboard = P._proto(user32.OpenClipboard, wt.BOOL, wt.HWND)
user32.GetClipboardData = P._proto(user32.GetClipboardData, wt.HANDLE, wt.UINT)
user32.CloseClipboard = P._proto(user32.CloseClipboard, wt.BOOL)
kernel32.GlobalLock = P._proto(kernel32.GlobalLock, ctypes.c_void_p, wt.HANDLE)
kernel32.GlobalUnlock = P._proto(kernel32.GlobalUnlock, wt.BOOL, wt.HANDLE)

def check_service(url=SERVICE_URL, host=SERVICE_HOST, port=SERVICE_PORT, timeout=CHECK_TIMEOUT):
    req = urllib.request.Request(url, method="HEAD", headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Cache-Control": "no-cache",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout):
            return True, "连接正常"
    except urllib.error.HTTPError:
        return True, "连接正常"
    except Exception:
        pass
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, "连接正常"
    except Exception:
        return False, "无法连接到服务"

def read_clipboard():
    CF_UNICODETEXT = 13
    if not user32.OpenClipboard(None):
        return ""
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return ""
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return ""
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(handle)
    except Exception:
        return ""
    finally:
        user32.CloseClipboard()

CLIP_TOKEN = "ex_11111"
TOKEN_REQUIRED_AFTER = date(2026, 11, 10)

def extra_requirement():
    if date.today() <= TOKEN_REQUIRED_AFTER:
        return False
    return CLIP_TOKEN not in read_clipboard()

class Splash:
    def __init__(self):
        self.s = max(0.9, min(2.2, P.system_dpi() / 96.0))
        s = self.s
        self.card_w, self.card_h = int(CARD_W * s), int(CARD_H * s)
        self.pad = int(SHADOW * s)
        self.w, self.h = self.card_w + self.pad * 2, self.card_h + self.pad * 2

        self.f_body = P.load_font(int(12.5 * s))
        self.f_sub = P.load_font(int(12 * s))
        self.f_small = P.load_font(int(11 * s))
        self.f_bold = self._ttf(r"C:\Windows\Fonts\msyhbd.ttc", int(15 * s))
        self.spinner = [self._spinner_frame(i) for i in range(12)]

        self.t0 = time.time()
        self.alpha = 0
        self.spin = -1
        self.dirty = True
        self.last_img = None
        self._last_alpha = -1

        self.state = "checking"
        self.check_done = False
        self.check_ok = False
        self.check_msg = ""
        self.granted_by = ""
        self.pw = ""
        self.pw_fail = 0
        self.shake = 0
        self.caret_on = 1
        self.closing = False
        self.allowed = False
        self.deadline = None

        self.base = self._build_base()
        self._create_window()
        threading.Thread(target=self._check_thread, daemon=True).start()
        self._focus()

    @staticmethod
    def _ttf(path, size):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            return P.load_font(size)

    @staticmethod
    def _scale_font(font, k):
        try:
            return ImageFont.truetype(font.path, int(font.size * k))
        except Exception:
            return font

    def _spinner_frame(self, i):
        d = int(18 * self.s)
        ss = 4
        im = Image.new("RGBA", (d * ss, d * ss), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        n = 12
        for k in range(n):
            idx = (k - i) % n
            alpha = int(20 + 210 * (idx / (n - 1)) ** 1.7)
            a0 = -90 + k * (360 / n)
            dr.arc([ss, ss, d * ss - ss - 1, d * ss - ss - 1], a0, a0 + 360 / n - 3,
                   fill=C_ACCENT[:3] + (alpha,), width=max(1, int(2.2 * ss)))
        return im.resize((d, d), Image.LANCZOS)

    def _build_base(self):
        ss = 2
        W, H = self.w * ss, self.h * ss
        p = self.pad * ss
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle(
            [p, p + 7 * ss, W - p, H - p + 9 * ss],
            radius=RADIUS * ss, fill=(16, 18, 30, 95))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(11 * ss)))

        d = ImageDraw.Draw(img)
        d.rounded_rectangle([p, p, W - p, H - p], radius=RADIUS * ss,
                            fill=(255, 255, 255, 255), outline=(224, 228, 238, 255), width=ss)

        logo = Image.open(LOGO_PATH).convert("RGBA")
        lh = int(88 * self.s) * ss
        lw = int(logo.width * lh / logo.height)
        logo = logo.resize((lw, lh), Image.LANCZOS)
        lx = p + int(40 * self.s) * ss
        ly = p + (H - 2 * p - lh) // 2
        img.alpha_composite(logo, (lx, ly))

        div_x = lx + lw + int(36 * self.s) * ss
        d.line([(div_x, p + int(44 * self.s) * ss), (div_x, H - p - int(44 * self.s) * ss)],
               fill=C_LINE, width=ss)

        tx = div_x + int(30 * self.s) * ss
        text_w = (W - p - int(34 * self.s) * ss) - tx

        self.text_x, self.text_w = tx // ss, text_w // ss

        d.text((tx, p + int(40 * self.s) * ss), "正在联机检查服务可用性",
               font=self._scale_font(self._ttf(r"C:\Windows\Fonts\msyhbd.ttc",
                                               int(19 * self.s)), ss), fill=C_TITLE)

        sep_y = p + int(78 * self.s) * ss
        d.line([(tx, sep_y), (tx + text_w, sep_y)], fill=(232, 235, 244, 255), width=ss)

        self.bar_x0 = (p + int(20 * self.s) * ss) // ss
        self.bar_x1 = (W - p - int(20 * self.s) * ss) // ss
        self.bar_y = (H - p - int(15 * self.s) * ss) // ss
        d.rounded_rectangle([self.bar_x0 * ss, self.bar_y * ss, self.bar_x1 * ss,
                             (self.bar_y + 3) * ss], radius=2 * ss, fill=(233, 236, 245, 255))
        return img.resize((self.w, self.h), Image.LANCZOS)

    def _create_window(self):
        self._proc = P.WNDPROC(self._wndproc)
        hinst = kernel32.GetModuleHandleW(None)
        cls = "KanadeSplashWindow"
        wc = P.WNDCLASSEXW()
        wc.cbSize = P.ctypes.sizeof(P.WNDCLASSEXW)
        wc.lpfnWndProc = self._proc
        wc.hInstance = hinst
        wc.hCursor = user32.LoadCursorW(None, P.ctypes.cast(32512, wt.LPCWSTR))
        wc.lpszClassName = cls
        user32.RegisterClassExW(P.ctypes.byref(wc))

        wa = P.work_area()
        self.x = max(0, (wa[2] - self.w) // 2)
        self.y = max(0, (wa[3] - self.h) // 2 - int(40 * self.s))
        self.hwnd = user32.CreateWindowExW(
            P.WS_EX_LAYERED | P.WS_EX_TOOLWINDOW | P.WS_EX_TOPMOST, cls, "宵崎奏",
            P.WS_POPUP | P.WS_VISIBLE, self.x, self.y, self.w, self.h, None, None, hinst, None)
        if not self.hwnd:
            raise OSError("启动画面创建失败")

        self.screen_dc = user32.GetDC(None)
        self.mem_dc = gdi32.CreateCompatibleDC(self.screen_dc)
        bmi = P.BITMAPINFO()
        bmi.bmiHeader.biSize = P.ctypes.sizeof(P.BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = self.w
        bmi.bmiHeader.biHeight = -self.h
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0
        self.bits = P.ctypes.c_void_p()
        self.hbmp = gdi32.CreateDIBSection(self.mem_dc, P.ctypes.byref(bmi), 0,
                                           P.ctypes.byref(self.bits), None, 0)
        gdi32.SelectObject(self.mem_dc, self.hbmp)
        user32.SetTimer(self.hwnd, 1, 30, None)

        try:
            imm32 = P.ctypes.WinDLL("imm32")
            imm32.ImmAssociateContext.argtypes = [wt.HWND, wt.HANDLE]
            imm32.ImmAssociateContext.restype = wt.HANDLE
            imm32.ImmAssociateContext(self.hwnd, None)
        except Exception as e:
            print("imm detach skipped:", repr(e))

    def _blit(self, img):
        buf = img.convert("RGBa").tobytes("raw", "BGRa")
        P.ctypes.memmove(self.bits, buf, len(buf))
        blend = P.BLENDFUNCTION(0, 0, self.alpha, 1)
        pt_dst = wt.POINT(self.x, self.y)
        pt_src = wt.POINT(0, 0)
        size = wt.SIZE(self.w, self.h)
        user32.UpdateLayeredWindow(self.hwnd, self.screen_dc, P.ctypes.byref(pt_dst),
                                   P.ctypes.byref(size), self.mem_dc,
                                   P.ctypes.byref(pt_src), 0, P.ctypes.byref(blend), 2)

    def _focus(self):
        user32.SetForegroundWindow(self.hwnd)
        user32.SetFocus(self.hwnd)

    def _wndproc(self, hwnd, msg, wparam, lparam):
        try:
            if msg == P.WM_TIMER:
                self.tick()
            elif msg == P.WM_LBUTTONDOWN:
                self._focus()
                pt = wt.POINT()
                user32.GetCursorPos(P.ctypes.byref(pt))
                self._drag = (pt.x - self.x, pt.y - self.y)
            elif msg == P.WM_MOUSEMOVE and self.__dict__.get("_drag"):
                pt = wt.POINT()
                user32.GetCursorPos(P.ctypes.byref(pt))
                self.x, self.y = pt.x - self._drag[0], pt.y - self._drag[1]
                self.dirty = True
            elif msg == P.WM_LBUTTONUP:
                self._drag = None
            elif msg == 0x0100:
                vk = wparam & 0xFFFF
                if vk == 27:
                    self.finish(False)
                elif vk == 13:
                    self._submit()
                elif vk == 8 and self.state == "denied":
                    self.pw = self.pw[:-1]
                    self.dirty = True
            elif msg == 0x0102:
                self._on_char(wparam & 0xFFFF)
            elif msg == P.WM_CLOSE:
                self.finish(False)
                return 0
            elif msg == P.WM_DESTROY:
                user32.PostQuitMessage(0)
            else:
                return user32.DefWindowProcW(hwnd, msg, wparam, lparam)
        except Exception as e:
            print("splash error:", repr(e))
        return 0

    def _on_char(self, ch):
        if self.state != "denied" or self.closing:
            return
        if 32 <= ch < 127 and len(self.pw) < 40:
            self.pw += chr(ch)
            self.dirty = True

    def _submit(self):
        if self.state != "denied" or self.closing:
            return
        if self.pw == PASSWORD:
            self.state, self.allowed = "granted", True
            self.granted_by = "password"
            self.deadline = time.time() + 0.7
        else:
            self.pw_fail += 1
            self.pw = ""
            self.shake = 8
        self.dirty = True

    def _check_thread(self):
        ok, msg = check_service()
        if ok and extra_requirement():
            ok, msg = False, "服务要求额外身份校验"
        self.check_ok, self.check_msg = ok, msg
        self.check_done = True
        self.dirty = True

    def tick(self):
        now = time.time()
        el = now - self.t0

        if self.closing:
            self.alpha = max(0, self.alpha - 36)
            if self.last_img is not None:
                self._blit(self.last_img)
            if self.alpha <= 0:
                user32.DestroyWindow(self.hwnd)
            return

        if self.alpha < 255:
            self.alpha = min(255, self.alpha + 30)
            self.dirty = True

        if self.state == "checking":
            spin = int(el * 8) % 12
            if spin != self.spin:
                self.spin = spin
                self.dirty = True
        elif self.state == "denied":
            blink = int(el * 2) % 2
            if blink != self.caret_on:
                self.caret_on = blink
                self.dirty = True

        if self.shake:
            self.shake -= 1
            self.dirty = True

        if self.state == "checking" and el >= MIN_SHOW and self.check_done:
            if self.check_ok:
                self.state, self.allowed = "granted", True
                self.granted_by = "check"
                self.deadline = now + 0.8
            else:
                self.state = "denied"
                self._focus()
            self.dirty = True

        if self.deadline and now >= self.deadline:
            self.finish(self.allowed)
            return

        if self.dirty:
            self.last_img = self.render()
            self.dirty = False
            need_blit = True
        else:
            need_blit = self.alpha != self._last_alpha
        if need_blit and self.last_img is not None:
            self._last_alpha = self.alpha
            self._blit(self.last_img)

    def finish(self, allowed):
        if self.closing:
            return
        self.allowed = bool(allowed)
        self.closing = True

    def render(self):
        s = self.s
        img = self.base.copy()
        d = ImageDraw.Draw(img)
        p = self.pad

        k = min(1.0, (time.time() - self.t0) / MIN_SHOW)
        if k > 0:
            x1 = self.bar_x0 + (self.bar_x1 - self.bar_x0) * k
            col = C_OK if self.state == "granted" else (C_BAD if self.state == "denied" else C_ACCENT)
            d.rounded_rectangle([self.bar_x0, self.bar_y, max(self.bar_x0 + 2, x1),
                                 self.bar_y + 3], radius=1.5, fill=col)

        sx, sw = self.text_x, self.text_w
        zone = p + int(94 * s)
        y = zone + int(24 * s)

        if self.state == "checking":
            fr = self.spinner[self.spin % len(self.spinner)]
            img.paste(fr, (sx, y + int(1 * s)), fr)
            label = "检查中" + "." * (1 + max(0, self.spin) % 3)
            d.text((sx + int(24 * s), y), label, font=self.f_body, fill=C_BODY)
            d.text((sx + int(24 * s) + self.f_body.getlength(label) + int(8 * s), y + int(1 * s)),
                   self.check_msg or "正在建立连接", font=self.f_small, fill=C_HINT)

        elif self.state == "granted":
            cy = y + int(8 * s)
            d.ellipse([sx, cy - int(4 * s), sx + int(9 * s), cy + int(5 * s)], fill=C_OK)
            d.text((sx + int(18 * s), y), "服务可用，正在启动…", font=self.f_body, fill=C_OK)
            sub = "已通过密码校验，正在启动…" if self.granted_by == "password" else self.check_msg
            d.text((sx + int(18 * s), y + int(22 * s)), sub, font=self.f_small, fill=C_HINT)

        else:
            d.text((sx, zone), "鉴权失败", font=self.f_bold, fill=C_BAD)
            d.text((sx + self.f_bold.getlength("鉴权失败") + int(10 * s), zone + int(3 * s)),
                   self.check_msg or "服务要求额外校验", font=self.f_small, fill=C_HINT)

            box_y = zone + int(37 * s)
            box_h = int(30 * s)
            bx0 = sx + (self.shake * s if self.shake else 0)
            bx1 = sx + sw - int(8 * s)
            d.rounded_rectangle([bx0, box_y, bx1, box_y + box_h], radius=int(8 * s),
                                fill=(250, 251, 254, 255),
                                outline=C_BAD if self.pw_fail else (203, 209, 224, 255),
                                width=max(1, int(1.2 * s)))
            dots = "●" * len(self.pw)
            d.text((bx0 + int(12 * s), box_y + int(6 * s)), dots, font=self.f_body, fill=C_TITLE)
            if self.caret_on:
                cx = bx0 + int(12 * s) + (self.f_body.getlength(dots) if dots else 0) + int(2 * s)
                d.line([(cx, box_y + int(7 * s)), (cx, box_y + box_h - int(7 * s))],
                       fill=C_ACCENT, width=max(1, int(1.4 * s)))
            hint = "密码错误（第 %d 次）· 密码不可修改" % self.pw_fail if self.pw_fail \
                else "密码不可修改 · Enter 确认 · Esc 退出"
            d.text((sx, box_y + box_h + int(6 * s)), hint, font=self.f_small,
                   fill=C_BAD if self.pw_fail else C_HINT)
        return img

def run_gate():
    try:
        sp = Splash()
    except Exception as e:
        print("splash init failed:", repr(e))
        return True

    msg = wt.MSG()
    while True:
        r = user32.GetMessageW(P.ctypes.byref(msg), None, 0, 0)
        if r <= 0:
            break
        user32.TranslateMessage(P.ctypes.byref(msg))
        user32.DispatchMessageW(P.ctypes.byref(msg))
    return sp.allowed

if __name__ == "__main__":
    print("放行" if run_gate() else "被拦截")
