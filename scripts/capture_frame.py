import urllib.request
import time

def capture():
    # It's an MJPEG stream. We can just read the first JPEG image by looking for boundary.
    import requests
    r = requests.get('http://127.0.0.1:8081/cam/0', stream=True)
    if r.status_code == 200:
        bytes = b''
        for chunk in r.iter_content(chunk_size=1024):
            bytes += chunk
            a = bytes.find(b'\xff\xd8')
            b = bytes.find(b'\xff\xd9')
            if a != -1 and b != -1:
                jpg = bytes[a:b+2]
                with open('/tmp/webcam.jpg', 'wb') as f:
                    f.write(jpg)
                print("Captured to /tmp/webcam.jpg")
                return
capture()
