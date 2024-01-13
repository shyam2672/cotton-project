from flask import Flask, request, jsonify, send_file
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from pymongo import MongoClient
from bson import ObjectId
import bcrypt
import os
import cv2
import numpy as np
from io import BytesIO


app = Flask(__name__)
# Replace with a secure secret key
app.config['JWT_SECRET_KEY'] = 'cotton123456'
jwt = JWTManager(app)

client = MongoClient(
    'mongodb+srv://cotton123456:cotton654321@cluster0.q7hrmaj.mongodb.net/cotton?retryWrites=true&w=majority')
db = client['cotton']
users_collection = db['users']
uploads_collection = db['uploads']

# print("connected to mongodb")
UPLOAD_FOLDER = "C:\\Users\\SHYAM\\OneDrive\\Desktop\\cotton project\\server\\UPLOAD_FOLDER"

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/')
def test():
    users_collection.insert_one({"name": "John"})
    return "Connected to the data base!"

# Register user endpoint
@app.route('/register', methods=['POST'])
def register():
    try:
        username = request.json.get('username')
        password = request.json.get('password')
        if not username or not password:
            return jsonify({"msg": "Missing username or password"}), 400

        existing_user = users_collection.find_one({'username': username})
        if existing_user:
            return jsonify({"msg": "Username already exists"}), 400

        # Implement your password hashing function
        hashed_password = generate_hashed_password(password)

        new_user = {
            'username': username,
            'password': hashed_password
        }

        users_collection.insert_one(new_user)
        return jsonify({"msg": "User registered successfully"}), 201
    except Exception as e:
        # Handle other exceptions
        return jsonify({"error": str(e)}), 500


# Function to hash a password
def generate_hashed_password(password):
    # Hash the password using bcrypt
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    # Return the hashed password as a string
    return hashed_password.decode('utf-8')


# Function to verify a password
def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# Login endpoint
@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')

    if not username or not password:
        return jsonify({"msg": "Missing username or password"}), 401

    user = users_collection.find_one({'username': username})
    # Implement your password verification function
    if user and verify_password(password, user['password']):
        access_token = create_access_token(identity=username)
        return jsonify(access_token=access_token), 200
    else:
        return jsonify({"msg": "Invalid credentials"}), 401


# Protected endpoint for uploading images
@app.route('/upload', methods=['POST'])
@jwt_required()
def upload_file():
    current_user = get_jwt_identity()
    if 'file' not in request.files:
        return 'No file part'

    file = request.files['file']
    print(file)
    if file.filename == '':
        return 'No selected file'
    print(file.filename)
    # Save the uploaded file to the specified upload folder
    if file:
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))

        # Store the file details along with user info in MongoDB
        user = users_collection.find_one({'username': current_user})
        inserted_id = uploads_collection.insert_one(
            {'filename': file.filename, 'uploaded_by': user['_id']}).inserted_id
        return f"File uploaded successfully with ID: {inserted_id}"
    
    



def change_resolution(image, scale_percent):
    width = int(image.shape[1] * scale_percent / 100)
    height = int(image.shape[0] * scale_percent / 100)
    dim = (width, height)
    resized_image = cv2.resize(image, dim, interpolation=cv2.INTER_AREA)
    return resized_image


# @app.route('/change_resolution', methods=['POST'])
# def upload_file():
#     try:
#         file = request.files['image']
#         scale_percent = float(request.form.get('scale_percent', 50))

#         # Read the image
#         nparr = np.frombuffer(file.read(), np.uint8)
#         image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

#         # Change resolution
#         resized_image = change_resolution(image, scale_percent)

#         # Convert the resized image to bytes
#         retval, buffer = cv2.imencode('.jpg', resized_image)
#         img_bytes = buffer.tobytes()

#         # Create a BytesIO object and send the resized image
#         return send_file(BytesIO(img_bytes), mimetype='image/jpeg')

#     except Exception as e:
#         return str(e)



if __name__ == '__main__':
    app.run(debug=True)
