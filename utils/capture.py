"""Capture.py: Capture HTTP requests for replay

This script provides a function that listens for an HTTP request on the given
address and port, captures that request, and generates a urllib Request object
by which the request can be replayed against a different server. This server
always responds with 200 and an empty body. Returning other responses is left
as an exercise for the reader.

This is designed to use just the python built-ins and to be useable from a
REPL.

Usage:

>>> import capture
>>> req = capture.capture_request("127.0.0.1", 8000)
------Elsewhere...-------
$ curl -H "MyHeader: MyValue" http://localhost:8000/path/path2\?query\=param -d '{"some":"payload"}
------Back here...-------
>>> req
<capture.CapturedRequest object at 0x7f82fd127750>
>>> req.headers
{'Host': 'localhost:8000',
 'User-agent': 'curl/7.64.1',
 'Accept': '*/*', 
 'Myheader': 'MyValue',
 'Content-length': '18',
 'Content-type': 'application/x-www-form-urlencoded'
}
>>> req.full_url
'http://localhost:8000/path/path2?query=param'
>>> req.data
b'{"some":"payload"}'
>>> req.set_url("https://actual.site/target/path")
>>> req.full_url
'https://actual.site/target/path?query=param'
>>> import urllib
>>> import urllib.request
>>> urllib.request.urlopen(req)
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request
from urllib.parse import urlsplit, urlunsplit


def capture_request(host, port):
    return CaptureServer((host, port)).capture_request()


class CapturedRequest(Request):
    def set_url(self, new_url):
        """Set target url for request replay."""
        scheme, host, path, query, fragment = urlsplit(self.full_url)
        scheme, host, path, _, _ = urlsplit(new_url)
        self.full_url = urlunsplit((scheme, host, path, query, fragment))
        self.headers["Host"] = host


class CaptureServer(HTTPServer):
    def __init__(self, server_address):
        self.last_request = None
        self.allow_reuse_address = True
        super().__init__(server_address, CaptureRequestHandler, False)

    def capture_request(self):
        self.last_request = None
        try:
            self.server_bind()
            self.server_activate()
            self.handle_request()
            if self.last_request:
                return self.last_request
        except:
            self.server_close()
            raise


class CaptureRequestHandler(BaseHTTPRequestHandler):
    def do_request(self):
        # This seems like a bug in BaseHTTPRequestHandler.
        self._headers_buffer = []
        try:
            cl = int(self.headers.get("Content-Length", 0))
        except:
            print("Couldn't read content-length, proceding without capturing body")
            cl = 0
        body = self.rfile.read(cl)
        # This doesn't support HTTPS, so assume HTTP
        req = CapturedRequest("http://" + self.headers.get("Host") + self.path, data=body,
                              headers=dict(self.headers.items()), method=self.command)
        self.server.last_request = req
        self.send_response_only(200)
        self.end_headers()
        return True

    def __getattr__(self, name):
        if name.startswith("do_"):
            return self.do_request
