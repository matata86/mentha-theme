#!/usr/bin/env python3
"""Minimální CDP klient (jen stdlib) pro snímání GTK aplikací přes Broadway v headless Chrome.

Použití: cdp.py URL WxH script.json
script.json = seznam kroků:
  {"wait": ms} | {"move": [x, y]} | {"click": [x, y]} | {"rclick": [x, y]} | {"dbl": [x, y]}
  {"key": "Escape"|"Return"|"Tab"|"Down"|...} | {"type": "text"} | {"shot": "out.png"}
  {"shot": "out.png", "clip": [x, y, w, h]}
  {"key": "ctrl+l"} / "ctrl+shift+Tab" / "alt+F" / "F2" / "F3" (modifikátory ctrl, alt, shift, meta; písmena, F1-F12)
  {"scroll": [x, y, dy]}  kolečko myši v bodě (dy > 0 = dolů, v px)
  {"maxwin": true}  dvojklik do titulku největšího Broadway okna (maximalizace na velikost prohlížeče)
  {"rect": "name"}  vypíše pozice všech Broadway oken (canvasů) do stdout jako JSON: rect name {...}
"""
import base64, json, os, socket, struct, subprocess, sys, tempfile, time, urllib.request

KEYS = {"Escape": 27, "Return": 13, "Tab": 9, "Down": 40, "Up": 38, "Left": 37, "Right": 39,
        "BackSpace": 8, "space": 32, "Delete": 46, "Home": 36, "End": 35, "Menu": 93,
        **{f"F{i}": 111 + i for i in range(1, 13)}, ",": 188, ".": 190, "/": 191, "-": 189, ";": 186}
MODS = {"alt": 1, "ctrl": 2, "meta": 4, "shift": 8}


class WS:
    def __init__(self, url):
        host, path = url[len("ws://"):].split("/", 1)
        h, p = host.split(":")
        self.s = socket.create_connection((h, int(p)))
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.send((f"GET /{path} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                     f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.s.recv(1)
        self.n = 0

    def _recv_exact(self, n):
        b = b""
        while len(b) < n:
            c = self.s.recv(n - len(b))
            if not c:
                raise EOFError
            b += c
        return b

    def send(self, obj):
        data = json.dumps(obj).encode()
        hdr = bytearray([0x81])
        n = len(data)
        if n < 126:
            hdr.append(0x80 | n)
        elif n < 65536:
            hdr += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            hdr += bytes([0x80 | 127]) + struct.pack(">Q", n)
        mask = os.urandom(4)
        self.s.send(bytes(hdr) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def recv(self):
        msg = b""
        while True:
            b0, b1 = self._recv_exact(2)
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._recv_exact(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._recv_exact(8))[0]
            msg += self._recv_exact(n)
            if b0 & 0x80:
                return json.loads(msg)

    def call(self, method, **params):
        self.n += 1
        self.send({"id": self.n, "method": method, "params": params})
        while True:
            r = self.recv()
            if r.get("id") == self.n:
                if "error" in r:
                    raise RuntimeError(f"{method}: {r['error']}")
                return r.get("result", {})


def rects(ws):
    r = ws.call("Runtime.evaluate", returnByValue=True, expression=
                "JSON.stringify([...document.querySelectorAll('canvas'),...document.body.children].map(e=>{const r=e.getBoundingClientRect();"
                "return [r.x,r.y,r.width,r.height]}).filter(r=>r[2]>100&&r[3]>50))")
    return json.loads(r["result"]["value"])


def maxwin(ws, w, h, mouse):
    """Broadway otevře okno podle velikosti obrazovky z doby před připojením prohlížeče (~1024x768);
    dvojklik do titulku ho roztáhne na celý viewport (canvas pak začíná v 0,0 a má velikost viewportu)."""
    def best():
        rs = rects(ws)
        return max(rs, key=lambda r: r[2] * r[3]) if rs else None

    def done(r):
        return r and abs(r[0]) < 2 and abs(r[1]) < 2 and abs(r[2] - w) < 3 and abs(r[3] - h) < 3
    r = best()
    if done(r):
        return
    for top in (50, 40, 60, 30, 20, 70):          # stín nad oknem se liší, zkoušíme odsazení titulku
        r = best()
        if r is None:
            return
        x, y, cw, ch = r
        px = min(max(x + cw / 2, x + 150), w - 260)
        py = y + top + 12
        mouse("mouseMoved", px, py)
        for c in (1, 2):
            mouse("mousePressed", px, py, "left", c)
            mouse("mouseReleased", px, py, "left", c)
        time.sleep(1.2)
        if done(best()):
            time.sleep(0.8)
            return
    print("maxwin: nepovedlo se", file=sys.stderr)


def main():
    url, size, script = sys.argv[1], sys.argv[2], json.load(open(sys.argv[3]))
    w, h = map(int, size.split("x"))
    port = 9300 + os.getpid() % 500
    prof = tempfile.mkdtemp(prefix="cdp-")
    chrome = subprocess.Popen(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                               f"--remote-debugging-port={port}", f"--user-data-dir={prof}",
                               f"--window-size={w},{h}", "about:blank"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    page = None
    try:
        for _ in range(100):
            try:
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json"))
                page = next(t for t in tabs if t["type"] == "page")
                break
            except Exception:
                time.sleep(0.1)
        if page is None:
            sys.exit("chrome CDP nenaběhl")
        ws = WS(page["webSocketDebuggerUrl"])
        ws.call("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=1, mobile=False)
        ws.call("Page.navigate", url=url)
        time.sleep(2.5)

        def mouse(kind, x, y, button="none", clicks=0):
            ws.call("Input.dispatchMouseEvent", type=kind, x=x, y=y, button=button, clickCount=clicks)

        for step in script:
            if "wait" in step:
                time.sleep(step["wait"] / 1000)
            elif "move" in step:
                mouse("mouseMoved", *step["move"])
                time.sleep(0.3)
            elif "click" in step or "rclick" in step or "dbl" in step:
                k = "click" if "click" in step else "rclick" if "rclick" in step else "dbl"
                x, y = step[k]
                btn = "right" if k == "rclick" else "left"
                mouse("mouseMoved", x, y)
                for c in ([1, 2] if k == "dbl" else [1]):
                    mouse("mousePressed", x, y, btn, c)
                    mouse("mouseReleased", x, y, btn, c)
                time.sleep(0.6)
            elif "scroll" in step:
                x, y, dy = step["scroll"]
                mouse("mouseMoved", x, y)
                ws.call("Input.dispatchMouseEvent", type="mouseWheel", x=x, y=y, deltaX=0, deltaY=dy)
                time.sleep(0.6)
            elif "key" in step:
                parts = step["key"].split("+")
                mods = sum(MODS[m] for m in parts[:-1])
                k = parts[-1]
                code = KEYS.get(k) or (ord(k.upper()) if len(k) == 1 else 0)
                for t in ("rawKeyDown", "keyUp"):
                    ws.call("Input.dispatchKeyEvent", type=t, key=k, windowsVirtualKeyCode=code, modifiers=mods)
                time.sleep(0.4)
            elif "rect" in step:
                print("rect", step["rect"], rects(ws))
            elif "maxwin" in step:
                maxwin(ws, w, h, mouse)
            elif "eval" in step:
                print("eval", ws.call("Runtime.evaluate", returnByValue=True, expression=step["eval"]).get("result", {}).get("value"))
            elif "waitwin" in step:           # okno aplikace se musí objevit do N ms, jinak exit 3
                t0 = time.time()
                while not rects(ws):
                    if time.time() - t0 > step["waitwin"] / 1000:
                        print("waitwin: okno se neobjevilo", file=sys.stderr)
                        sys.exit(3)
                    time.sleep(0.4)
            elif "type" in step:
                for ch in step["type"]:      # Broadway čte klávesové události, ne insertText
                    code = ord(ch.upper()) if ch.isalnum() else {"/": 191, " ": 32, ".": 190, "-": 189, "_": 189}.get(ch, 0)
                    mods = 8 if ch.isupper() or ch == "_" else 0
                    ws.call("Input.dispatchKeyEvent", type="keyDown", key=ch, text=ch, windowsVirtualKeyCode=code, modifiers=mods)
                    ws.call("Input.dispatchKeyEvent", type="keyUp", key=ch, windowsVirtualKeyCode=code, modifiers=mods)
                time.sleep(0.4)
            elif "shot" in step:
                p: dict = {"format": "png"}
                if "clip" in step:
                    x, y, cw, ch = step["clip"]
                    p["clip"] = {"x": x, "y": y, "width": cw, "height": ch, "scale": 1}
                data = ws.call("Page.captureScreenshot", **p)["data"]
                os.makedirs(os.path.dirname(os.path.abspath(step["shot"])), exist_ok=True)
                open(step["shot"], "wb").write(base64.b64decode(data))
                print("shot", step["shot"])
    finally:
        chrome.terminate()


if __name__ == "__main__":
    main()
