import atexit
import os
from flask import Flask, render_template, request, redirect, url_for
from threading import Lock, Thread
from queue import Queue
import tempfile
from  werkzeug.exceptions import HTTPException
import convert, upload, control
import time

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1000 * 1000
mutex = Lock()
upload_thread = None
upload_queue: Queue[bytes] = Queue()
exiting = False

# Set the upload folder and allowed extensions
UPLOAD_FOLDER = 'uploaded'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Helper function to check file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def _send_file(data: bytes):
    try:
        with tempfile.NamedTemporaryFile() as f:
            f.write(data)
            f.flush()
            out = convert.convert_image(f.name)
            if all(v == 0 for v in out):
                raise HTTPException('Error converting image (no transparency pls)\n')
            print(f'Converted image size: {len(out)}\n'.encode())
            upload_queue.put(out)
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
    if file.content_length > 5 * 1000 * 1000:
        return 'Invalid size', 400

    if file and allowed_file(file.filename):
        _send_file(file.stream.read())
        return redirect(url_for('index'))

    return 'Invalid file format. Only PNG, JPG, JPEG, GIF allowed.', 400

def interrupt():
    print('Shutting down...')
    global exiting
    exiting = True
    if upload_thread and upload_thread.is_alive():
        upload_thread.join()

def pump_images():
    client = control.FemtoCircleControl()
    client.wait_for_state()
    print('Connected to FemtoCircle', client.state)
    while not exiting:
        out = upload_queue.get()
        with mutex:
            client.setSingleLoop()
            try:
                wait_bin_index = client.state.filelist.index('WAIT')
            except (ValueError, AttributeError):
                print('No wait.bin found, uploading directly')
                wait_bin_index = 3

            client.playFileFromList(wait_bin_index) #play wait.bin
            for _ in range(3):
                print('Uploading image...')
                try:
                    upload.FemtoCircleUpload().send_file("output.bin", [out])
                    break
                except EOFError as e:
                    print(f'Error uploading image: {e}')
                    time.sleep(2)
            print('Upload complete, playing image...')
            try:
                new_file_index = client.state.filelist.index('OUTPUT')
            except (ValueError, AttributeError):
                print('No output.bin found, cannot play uploaded image')
                new_file_index = 2
            client.playFileFromList(new_file_index)
    client.io.close()

if __name__ == '__main__':
    upload_thread = Thread(target=pump_images, daemon=True)
    upload_thread.start()
    atexit.register(interrupt)
    app.run(debug=False, host='0.0.0.0', port=4242)
