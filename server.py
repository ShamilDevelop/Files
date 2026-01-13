#!/usr/bin/env python3
import http.server
import socketserver
import os
import cgi
from urllib.parse import urlparse, parse_qs

UPLOAD_DIR = '/var/www/uploads'
os.makedirs(UPLOAD_DIR, exist_ok=True)

class UploadHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/upload':
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD': 'POST'}
            )
            
            if 'file' in form:
                file_item = form['file']
                if file_item.filename:
                    filename = os.path.basename(file_item.filename)
                    filepath = os.path.join(UPLOAD_DIR, filename)
                    
                    with open(filepath, 'wb') as f:
                        f.write(file_item.file.read())
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(f'<h1>File {filename} uploaded successfully!</h1><a href="/">Back</a>'.encode())
                    return
            self.send_response(400)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html = '''
            <!DOCTYPE html>
            <html><body>
            <h1>File Upload Server</h1>
            <form action="/upload" method="post" enctype="multipart/form-data">
                <input type="file" name="file"><br><br>
                <input type="submit" value="Upload">
            </form>
            <h3>Uploaded files:</h3>
            <ul>'''
            for f in os.listdir(UPLOAD_DIR):
                html += f'<li><a href="/uploads/{f}">{f}</a></li>'
            html += '</ul></body></html>'
            self.wfile.write(html.encode())
        elif self.path.startswith('/uploads/'):
            return super().do_GET()
        else:
            super().do_GET()

PORT = 80
with socketserver.TCPServer(("", PORT), UploadHandler) as httpd:
    print(f"Serving at port {PORT} - Uploads go to {UPLOAD_DIR}")
    httpd.serve_forever()
