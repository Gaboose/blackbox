from os import curdir, system
from os.path import join as pjoin
import sys
import subprocess

from http.server import BaseHTTPRequestHandler, HTTPServer

class StoreHandler(BaseHTTPRequestHandler):
    #store_path = pjoin(curdir, 'store.json')
    store_path = "/home/pi/Desktop/distance-measure/mode.txt"

    def do_GET(self):
        if self.path == '/':
            with open(self.store_path) as fh:
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                state = int(fh.readline().split()[0])
                if state == 0:
                  t = "Deactivated (0)"
                elif state == 1:
                  t = "Playing music (1) (default)"
                elif state == 2:
                  t = "Variant frequency (2)"
                else:
                  t = "Unknown mode number!"
                self.wfile.write("<html><head><title>BlackBox - manage</title></head>\n".encode())
                self.wfile.write("<body><p>Current state: <strong>".encode() + t.encode() + "</strong></p>\n".encode())
                if state != 0:
                    self.wfile.write('<p><a href="/mode/0">Deactivate (set state to 0)</a></p>'.encode())
                if state != 1:
                    self.wfile.write('<p><a href="/mode/1">Play music (set state to 1)</a></p>'.encode())
                if state != 2:
                    self.wfile.write('<p><a href="/mode/2">Produce variant frequency tone (set state to 2)</a></p>'.encode())
                self.wfile.write('<form method="POST" action="/restart"><p>Restart BlackBox (reboot Raspberry Pi): <input type="submit" value="Restart!"></p></form>'.encode())
                self.wfile.write('<p><a href="/speak">Go to speech synthesis page</a></p>'.encode())
                self.wfile.write('<p><a href="http://192.168.10.1:8000">Go to music upload page</a></p></body></html>'.encode())
        elif self.path.startswith('/mode'):
            m = self.path[-1]
            if m == '/':
                m = self.path[-2]
            try:
                m = int(m)
                if m in (0, 1, 2):
                    print("OK:", m)

                    with open(self.store_path, 'w') as fh:
                        fh.write(str(m) + "\n")

                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write("<html><head><title>BlackBox - manage</title></head>\n".encode())
                    self.wfile.write("<body><p>Updated state to: <strong>".encode() + str(m).encode() + "</strong></p>\n".encode())
                    if m != 0:
                        self.wfile.write('<p><a href="/mode/0">Deactivate (set state to 0)</a></p>'.encode())
                    if m != 1:
                        self.wfile.write('<p><a href="/mode/1">Play music (set state to 1)</a></p>'.encode())
                    if m != 2:
                        self.wfile.write('<p><a href="/mode/2">Produce variant frequency tone (set state to 2)</a></p>'.encode())
                    self.wfile.write('<form method="POST" action="/restart"><p>Restart BlackBox (reboot Raspberry Pi): <input type="submit" value="Restart!"></p></form>'.encode())
                    self.wfile.write('<p><a href="/speak">Go to speech synthesis page</a></p>'.encode())
                    self.wfile.write('<p><a href="http://192.168.10.1:8000">Go to music upload page</a></p></body></html>'.encode())
                else:
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write("<html><head><title>BlackBox - manage</title></head>\n".encode())
                    self.wfile.write("<body><p>Unknown value submitted - go back and try again!</p></body></html>".encode())
            except:
                print("Exception:", sys.exc_info()[0])
                self.send_response(404)
        elif self.path.startswith('/speak'):
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write("<html><head><title>BlackBox - speech</title></head>\n".encode())
            self.wfile.write('<body><form method="POST"><p>What to say:</p><p><input type="text" name="words" id="words"></p><p><input type="submit" value="Speak!"></form>'.encode())
            self.wfile.write('<p><a href="/">Go back to status management page</a></p>'.encode())
            self.wfile.write('<p><a href="http://192.168.10.1:8000">Go to music upload page</a></p></body></html>'.encode())
            
    def do_POST(self):
        if self.path.startswith('/restart'):
          self.send_response(301)
          self.send_header('Location', 'http://192.168.10.1:8001/')
          self.end_headers()
          command = "/usr/bin/sudo /sbin/shutdown -r now"
          process = subprocess.call(command.split())
        else:
          length = self.headers['content-length']
          data = self.rfile.read(int(length))
          self.send_response(200)
          self.send_header("Content-type", "text/html")
          self.end_headers()
          self.wfile.write("<html><head><title>BlackBox - speech</title></head>\n".encode())
          self.wfile.write('<body><form method="POST"><p>What to say:</p><p><input type="text" name="words" id="words"></p><p><input type="submit" value="Speak!"></form>'.encode())
          self.wfile.write('<p><a href="/">Go back to status management page</a></p>'.encode())
          self.wfile.write('<p><a href="http://192.168.10.1:8000">Go to music upload page</a></p></body></html>'.encode())
          s = data.decode().replace('+', ' ')
          if s.startswith("words="):
            system('espeak -s 155 "' + s[6:] + '" ')

server = HTTPServer(('0.0.0.0', 8001), StoreHandler)
server.serve_forever()
