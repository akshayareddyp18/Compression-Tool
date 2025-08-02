from flask import Flask, request, jsonify, send_from_directory, send_file, url_for
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import logging
import zipfile
from io import BytesIO

app = Flask(__name__)
CORS(app, origins=[
    'http://localhost:3000',  
    'https://Compression-Tool-1.onrender.com'  
])


# --------------------------------------------------
# Logging
# --------------------------------------------------
logging.basicConfig(
    level=logging.INFO,               # change to DEBUG for very verbose logs
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# --------------------------------------------------
# Directory setup
# --------------------------------------------------
ROOT_DIR            = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER       = os.path.join(ROOT_DIR, "uploads")
COMPRESSED_FOLDER   = os.path.join(ROOT_DIR, "compressed")
DECOMPRESSED_FOLDER = os.path.join(ROOT_DIR, "decompressed")

for folder in (UPLOAD_FOLDER, COMPRESSED_FOLDER, DECOMPRESSED_FOLDER):
    os.makedirs(folder, exist_ok=True)

# --------------------------------------------------
# Routes
# --------------------------------------------------
@app.route("/", methods=["GET"])
def home():
    return "✅ Backend is running!"

@app.route("/status", methods=["GET"])
def status():
    return jsonify({"status": "Backend is running!"})

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        logging.error("No file part in request")
        return jsonify({"message": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        logging.error("No selected file")
        return jsonify({"message": "No selected file"}), 400

    allowed_extensions = {".txt", ".pdf", ".png", ".zip", ".jpg", ".docx"}
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        logging.error(f"Unsupported file type: {file_ext}")
        return jsonify({"message": f"Unsupported file type: {file_ext}"}), 400

    filename   = secure_filename(file.filename)
    file_path  = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)
    logging.info(f"Saved upload: {file_path}")

    try:
        # Build ZIP
        zip_filename = f"{os.path.splitext(filename)[0]}_compressed.zip"
        zip_path     = os.path.join(COMPRESSED_FOLDER, zip_filename)

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(file_path, filename)

        original_size    = os.path.getsize(file_path)
        compressed_size  = os.path.getsize(zip_path)
        compression_ratio = round(original_size / compressed_size, 2) if compressed_size else 0
        space_saved       = round((1 - compressed_size / original_size) * 100, 2) if original_size else 0

        # Build an absolute download URL that works on Render
        download_url = url_for("download_file", filename=zip_filename, _external=True)

        return jsonify({
            "message": "✅ File compressed!",
            "download_url": download_url,
            "original_size_bytes": original_size,
            "compressed_size_bytes": compressed_size,
            "compression_ratio": compression_ratio,
            "space_saved_percent": space_saved
        })
    except Exception as e:
        logging.exception("Compression error")
        return jsonify({"message": f"❌ Compression error: {e}"}), 500

@app.route("/download/<path:filename>", methods=["GET"])
def download_file(filename):
    try:
        return send_from_directory(COMPRESSED_FOLDER, filename, as_attachment=True)
    except Exception as e:
        logging.exception("Download error")
        return jsonify({"message": f"❌ Download error: {e}"}), 404

@app.route("/decompress", methods=["POST"])
def decompress_file():
    if "file" not in request.files or request.files["file"].filename == "":
        return jsonify({"message": "No .zip file provided"}), 400

    file      = request.files["file"]
    filename  = secure_filename(file.filename)

    if not filename.endswith(".zip"):
        return jsonify({"message": "❌ Please upload a .zip file"}), 400

    zip_path = os.path.join(COMPRESSED_FOLDER, filename)
    file.save(zip_path)

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            members = zf.namelist()
            if len(members) != 1:
                return jsonify({"message": "ZIP must contain exactly one file"}), 400

            extracted_name = members[0]
            allowed_ext    = {".txt", ".pdf", ".png", ".jpg", ".docx"}
            if os.path.splitext(extracted_name)[1].lower() not in allowed_ext:
                return jsonify({"message": "Unsupported extracted file type"}), 400

            extracted_path = os.path.join(DECOMPRESSED_FOLDER, extracted_name)
            zf.extract(extracted_name, DECOMPRESSED_FOLDER)

        response = send_file(extracted_path, download_name=extracted_name, as_attachment=True)
        response.headers["X-Extracted-Filename"] = extracted_name
        return response
    except Exception as e:
        logging.exception("Decompression error")
        return jsonify({"message": f"❌ Decompression error: {e}"}), 500

# --------------------------------------------------
# Entry point
# --------------------------------------------------
if __name__ == "__main__":
    # Use Render's assigned port if present, else default to 5000 for local dev
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
