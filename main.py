import os

from flask import Flask, request
from werkzeug import secure_filename

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
IMAGE_DIR = DIR_PATH + "/tmp_images"

LOCAL_IP = "192.168.1.10"
PORT = 5000

app = Flask(__name__)
app.debug = True

@app.route('/')
def hello_world():
   return "Hello World"

@app.route('/image', methods = ['POST'])
def upload_image():
    print("Image upload endpoint")
    json = request.form.getlist('json')[0]
    file = request.files['image']
    file.save(IMAGE_DIR + "/" + secure_filename(file.filename))
    return "File uploaded succesfully"

if __name__ == '__main__':
   app.run(host=LOCAL_IP, port=PORT)


# curl \
#   -F "userid=1" \
#   -F "filecomment=This is an image file" \
#   -F "image=@/home/pi/waste_tracker/tmp_images/icon.png" \
#   192.168.1.10:5000/image