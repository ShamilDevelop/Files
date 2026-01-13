#!/usr/bin/env python3
import http.server
import socketserver
import os
import cgi
import json
from urllib.parse import urlparse, parse_qs
import threading
import time

UPLOAD_DIR = '/var/www/uploads'
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory sessions for progress tracking
upload_sessions = {}

class UploadHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/upload':
            # Parse multipart form
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD':'POST'}
            )
            
            if 'file' in form:
                file_item = form['file']
                if file_item.filename:
                    filename = os.path.basename(file_item.filename)
                    filepath = os.path.join(UPLOAD_DIR, filename)
                    
                    # Create unique session ID
                    session_id = f"{filename}_{int(time.time())}"
                    upload_sessions[session_id] = {
                        'total': 0,
                        'received': 0,
                        'filename': filename,
                        'status': 'uploading'
                    }
                    
                    # First pass: get total size
                    total_size = len(file_item.value)
                    upload_sessions[session_id]['total'] = total_size
                    
                    # Save file
                    with open(filepath, 'wb') as f:
                        chunk_size = 1024 * 64  # 64KB chunks
                        for i in range(0, total_size, chunk_size):
                            chunk = file_item.value[i:i+chunk_size]
                            f.write(chunk)
                            upload_sessions[session_id]['received'] += len(chunk)
                            time.sleep(0.01)  # Allow progress updates
                    
                    upload_sessions[session_id]['status'] = 'completed'
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'success': True,
                        'filename': filename,
                        'session_id': session_id
                    }).encode())
                    return
            
            self.send_response(400)
            self.end_headers()
        elif self.path.startswith('/progress/'):
            session_id = self.path.split('/')[-1]
            if session_id in upload_sessions:
                progress = upload_sessions[session_id]
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(progress).encode())
            else:
                self.send_response(404)
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
            <html>
            <head>
                <title>File Upload with Progress</title>
                <style>
                    body { font-family: Arial; max-width: 800px; margin: 50px auto; }
                    .progress-container { margin: 20px 0; }
                    .progress-bar { width: 100%; height: 30px; background: #f0f0f0; border-radius: 15px; overflow: hidden; }
                    .progress-fill { height: 100%; background: #4CAF50; transition: width 0.3s; border-radius: 15px; }
                    .progress-text { margin-top: 10px; font-weight: bold; }
                    input[type=file] { margin: 20px 0; }
                    button { padding: 12px 30px; background: #2196F3; color: white; border: none; border-radius: 5px; cursor: pointer; }
                </style>
            </head>
            <body>
                <h1>📁 File Upload Server with Progress Bar</h1>
                <form id="uploadForm">
                    <input type="file" id="fileInput" name="file"><br>
                    <button type="submit">Upload File</button>
                </form>
                
                <div id="progressContainer" class="progress-container" style="display:none;">
                    <div class="progress-bar">
                        <div id="progressFill" class="progress-fill" style="width:0%"></div>
                    </div>
                    <div id="progressText" class="progress-text">0%</div>
                </div>
                
                <h3>Uploaded files:</h3>
                <ul id="fileList">
            '''
            for f in os.listdir(UPLOAD_DIR):
                html += f'<li><a href="/uploads/{f}" target="_blank">{f}</a></li>'
            html += '''
                </ul>
                <script>
                    document.getElementById('uploadForm').onsubmit = async function(e) {
                        e.preventDefault();
                        const fileInput = document.getElementById('fileInput');
                        const file = fileInput.files[0];
                        if (!file) return;
                        
                        const formData = new FormData();
                        formData.append('file', file);
                        
                        // Show progress bar
                        document.getElementById('progressContainer').style.display = 'block';
                        
                        const xhr = new XMLHttpRequest();
                        let sessionId;
                        
                        // Progress monitoring
                        xhr.upload.onprogress = function(e) {
                            if (e.lengthComputable) {
                                const percent = (e.loaded / e.total) * 100;
                                document.getElementById('progressFill').style.width = percent + '%';
                                document.getElementById('progressText').textContent = Math.round(percent) + '%';
                            }
                        };
                        
                        xhr.onload = function() {
                            if (xhr.status === 200) {
                                alert('✅ Upload completed!');
                                location.reload();
                            } else {
                                alert('❌ Upload failed!');
                            }
                            document.getElementById('progressContainer').style.display = 'none';
                        };
                        
                        xhr.open('POST', '/upload');
                        xhr.send(formData);
                    };
                </script>
            </body>
            </html>
            '''
            self.wfile.write(html.encode())
        elif self.path.startswith('/uploads/'):
            return super().do_GET()
        else:
            super().do_GET()

PORT = 80
print(f"🚀 Starting upload server with progress bar on port {PORT}")
print(f"📁 Uploads saved to: {UPLOAD_DIR}")
with socketserver.TCPServer(("", PORT), UploadHandler) as httpd:
    httpd.serve_forever()
