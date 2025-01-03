import os
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
from threading import Lock
import tempfile
from  werkzeug.exceptions import HTTPException
import convert, upload, control
import time

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 3 * 1000 * 1000
mutex = Lock()

# Set the upload folder and allowed extensions
UPLOAD_FOLDER = 'uploaded'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Helper function to check file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def _send_file(data):
    try:
        with tempfile.NamedTemporaryFile() as f:
            f.write(data)
            f.flush()
            out = convert.convert_image(f.name)
            if all(v == 0 for v in out):
                raise HTTPException('Error converting image (no transparency pls)\n')
            print(f'Converted image size: {len(out)}\n'.encode())
            with mutex:
                client = control.FemtoCircleControl()
                client.setSingleLoop()
                client.playFileFromList(1) #play wait.bin
                upload.FemtoCircleUpload().send_file("output.bin", [out])
                client.playFileFromList(0)
    except Exception as e:
        print(e)
        raise HTTPException('Error converting image')
    with open(f'{UPLOAD_FOLDER}/{time.time()}.image', 'wb') as f:
        f.write(data)

# Route to display uploaded images
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle image upload
@app.route('/upload', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return redirect(request.url)

    file = request.files['file']
    if file.content_length > 3 * 1000 * 1000:
        return 'Invalid size', 400

    if file and allowed_file(file.filename):
        _send_file(file.stream.read())
        return redirect(url_for('index'))

    return 'Invalid file format. Only PNG, JPG, JPEG, GIF allowed.', 400

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=4242)