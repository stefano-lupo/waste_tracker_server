import os, sys
from bson import json_util, objectid
from flask import Flask, request, json, abort, make_response
from werkzeug import secure_filename
from flask_pymongo import PyMongo
from gridfs import GridFS
from flask_cors import CORS
import datetime

DIR_PATH = os.path.dirname(os.path.realpath(__file__))
IMAGE_DIR = DIR_PATH + "/tmp_images"
GRID_FS_IMAGE_NAMESPACE = "images"

LOCAL_IP = "localhost"
PORT = 5000

app = Flask(__name__)
CORS(app)
app.debug = True
app.config["MONGO_URI"] = "mongodb://localhost:27017/waste_tracker"
mongo = PyMongo(app)
db = mongo.db
gridfs = GridFS(db, GRID_FS_IMAGE_NAMESPACE)

def toJson(data):
   return json_util.dumps(data)

@app.route('/')
def root():
   return "hello world!"

# Specify an RFID -> Dish link
@app.route('/rfidtodish', methods = ['POST'])
def register_meal_to_rfid():
   data = request.get_json()

   # Delete any existing registered links without corresponding files
   rfid = data["rfid"]
   result = db.captures.delete_many({"rfid": rfid, "file_id": None})
   print("Deleted " + str(result.deleted_count) + " existing captures for " + rfid)

   # Create the new link
   data["registered_timestamp"] = datetime.datetime.now().isoformat()
   result = db.captures.insert_one(data)

   return str(result.inserted_id)


# Upload collection data for current rfid
@app.route('/collection', methods = ['POST'])
def upload_collection_data():   
   # Fetch the link entry created when RFID was registered to a meal
   data = json.loads(request.form.getlist('json')[0])
   rfid = data["rfid"]
   link_entry = db.captures.find_one({"rfid": rfid, "file_id": None})

   if (link_entry is None):
      print("No link entry for: " + rfid)
      abort(404, "Unable to find link entry for " + rfid)
      return

   print("Found link entry: ", link_entry)

   # Save file in GFS
   file = request.files['image']
   filename = secure_filename(file.filename)
   file_id = gridfs.put(file, content_type=file.content_type, filename=filename)

   # Update that link entry with the collection data
   link_entry["weight"] = data["weight"]
   link_entry["collected_timestamp"] = data["collected_timestamp"]
   link_entry["file_id"] = file_id

   # Update DB
   db.captures.update_one({"_id": link_entry["_id"]}, {'$set': link_entry})
   return "File uploaded succesfully"

@app.route('/dish')
def get_dishes_for_rfid():
   dish_name = request.args.get('dish_name')
   captures = db.captures.find({'dish_name': dish_name})

   if captures is None:
      abort(404, "No dish found with name " + dish_name)

   return toJson(captures)

@app.route('/dish/<name>', methods = ['GET'])
def get_captures_for_dishname(name):
   return toJson(db.captures.find({'dish_name': name}))

@app.route('/image/<id>', methods = ['GET'])
def get_image_by_id(id):
   print(id)
   f = gridfs.get(objectid.ObjectId(id))
   response = make_response(f.read())
   response.mimetype = 'image/jpeg'
   return response

@app.route('/captures-by-dish')
def get_all_captures_by_dish():
   dictionary = {}
   captures = db.captures.find({})
   for capture in captures:
      dish_name = capture['dish_name']
      if ('file_id' not in capture):
         print("Skipping " + capture['dish_name'] + " as no file_id")
         continue
      
      capture['image_url'] = "http://" + LOCAL_IP  + ":" + str(PORT) + "/image/" + str(capture['file_id'])
      if dish_name in dictionary:
         dictionary[dish_name].append(capture)
      else:
         dictionary[dish_name] = [capture]

    
   return toJson(dictionary)

if __name__ == '__main__':
   if (len(sys.argv) > 1):
      LOCAL_IP = sys.argv[1]
   

   if (len(sys.argv) > 2):
      PORT = sys.argv[2]
   
   app.run(host=LOCAL_IP, port=PORT)


# curl \
#   -F "userid=1" \
#   -F "filecomment=This is an image file" \
#   -F "image=@/home/pi/waste_tracker/tmp_images/icon.png" \
#   192.168.1.10:5000/image