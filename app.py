from flask import Flask, request, jsonify, send_file
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
)
from pymongo import MongoClient
import bcrypt
import os
import cv2
from werkzeug.utils import secure_filename
from gridfs import GridFS
from lines import fiberLen

import certifi

ca = certifi.where()

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "cotton123456"
jwt = JWTManager(app)

client = MongoClient(
    "mongodb+srv://cotton123456:cotton654321@cluster0.q7hrmaj.mongodb.net/cotton?retryWrites=true&w=majority",
    tlsCAFile=ca,
)
db = client["cotton"]
users_collection = db["users"]
uploads_collection = db["uploads"]

app.config["UPLOAD_FOLDER"] = "uploads"
grid_fs = GridFS(db, collection="files")


def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def generate_hashed_password(password):
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed_password.decode("utf-8")


@app.route("/")
@jwt_required()
def test():
    return jsonify({"msg": "success"}), 200


@app.route("/register", methods=["POST"])
def register():
    try:
        username = request.json.get("username")
        password = request.json.get("password")
        if not username or not password:
            return (
                jsonify({"msg": "Missing username or password", "result": "failure"}),
                400,
            )

        existing_user = users_collection.find_one({"username": username})
        if existing_user:
            return jsonify({"msg": "Username already exists", "result": "failure"}), 400

        hashed_password = generate_hashed_password(password)

        new_user = {"username": username, "password": hashed_password}

        users_collection.insert_one(new_user)
        return (
            jsonify({"msg": "User registered successfully", "result": "success"}),
            201,
        )

    except Exception as e:
        return jsonify({"msg": str(e), "result": "failure"}), 500


@app.route("/login", methods=["POST"])
def login():
    username = request.json.get("username")
    password = request.json.get("password")

    if not username or not password:
        return (
            jsonify({"msg": "Missing username or password", "result": "failure"}),
            401,
        )

    user = users_collection.find_one({"username": username})

    if user and verify_password(password, user["password"]):
        access_token = create_access_token(identity=username)
        return jsonify({"access_token": access_token, "result": "success"}), 200

    else:
        return jsonify({"msg": "Invalid credentials", "result": "failure"}), 401


def change_resolution(image, scale_percent):
    width = int(image.shape[1] * scale_percent / 100)
    height = int(image.shape[0] * scale_percent / 100)
    dim = (width, height)
    resized_image = cv2.resize(image, dim, interpolation=cv2.INTER_AREA)
    return resized_image


def processImage(filename, operation, scale):
    print(f"the operation is {operation} and filename is {filename}")
    img = cv2.imread(f"uploads/{filename}")
    match operation:
        case "cgray":
            imgProcessed = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            newFilename = f"static/{filename}"
            cv2.imwrite(newFilename, imgProcessed)
            return newFilename
        case "resize":
            scale_percent = 50
            width = int(img.shape[1] * scale_percent / 100)
            height = int(img.shape[0] * scale_percent / 100)
            dim = (width, height)
            imgProcessed = cv2.resize(img, dim, interpolation=cv2.INTER_AREA)
            newFilename = f"static/{filename}"
            cv2.imwrite(newFilename, imgProcessed)
            return newFilename
        case "getD":
            return img.shape
        case "lines":
            res = fiberLen(f"uploads/{filename}", scale)
            print(res)
            return res

    pass


@app.route("/upload", methods=["POST"])
@jwt_required()
def upload_file():
    current_user = get_jwt_identity()
    if "file" not in request.files:
        return jsonify({"msg": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"msg": "No selected file"}), 400

    if file:
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], file.filename))
        file_id = grid_fs.put(
            file.stream, filename=file.filename, content_type=file.content_type
        )

        # scale = request.json.get("scale")

        user = users_collection.find_one({"username": current_user})
        uploads_collection.insert_one({"filid": file_id, "uploaded_by": user["_id"]})

        res = processImage(file.filename, "lines", 1)
        return jsonify({"length": res}), 200


@app.route("/edit", methods=["POST"])
@jwt_required()
def edit():
    try:
        file = request.files["image"]
        if file.filename == "":
            return "error no selected file"
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            new = processImage(filename, "cgray")
            return send_file(new, as_attachment=True)

    except Exception as e:
        return str(e)


if __name__ == "__main__":
    app.run(debug=True)
