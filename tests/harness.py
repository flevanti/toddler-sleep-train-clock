"""Shared helpers for the browser tests: static server, check(), settings opener."""
import functools
import http.server
import threading

H = 'window.__toddlerSleepTrainClock'
VIEWPORTS = [(1024, 768), (768, 1024)]


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve(root):
    """Serve the repo root on a free local port. Returns (server, url of index.html)."""
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(_Quiet, directory=root))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, 'http://127.0.0.1:%d/index.html' % srv.server_address[1]


class Checks:
    def __init__(self):
        self.fails = []

    def __call__(self, name, cond, info=''):
        print(('PASS ' if cond else 'FAIL ') + name, info)
        if not cond:
            self.fails.append(name)

    def finish(self):
        print('FAILURES:', self.fails or 'none')
        return 1 if self.fails else 0


def open_settings(p, vp):
    """Long-press the top-right corner (page must use page.clock)."""
    p.mouse.move(vp[0] - 30, 30)
    p.mouse.down()
    p.clock.run_for(2700)
    p.mouse.up()
    p.clock.run_for(200)
