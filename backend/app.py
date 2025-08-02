from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import logging
import zipfile
from io import BytesIO

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Define folders using absolute paths
UPLOAD_FOLDER = os.path.abspath("uploads")
COMPRESSED_FOLDER = os.path.abspath("compressed")
DECOMPRESSED_FOLDER = os.path.abspath("decompressed")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(COMPRESSED_FOLDER, exist_ok=True)
os.makedirs(DECOMPRESSED_FOLDER, exist_ok=True)

@app.route("/", methods=["GET"])
def home():
    return "Successfully running!"

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

    allowed_extensions = {'.txt', '.pdf', '.png', '.zip', '.jpg', '.docx'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        logging.error(f"Unsupported file type: {file.filename}, extension: {file_ext}")
        return jsonify({"message": f"Unsupported file type: {file_ext}. Use .txt, .pdf, .png, .zip, .jpg, or .docx."}), 400

    filename = secure_filename(file.filename)
    logging.info(f"Processing file: {filename}, extension: {file_ext}, size: {file.content_length or 'unknown'} bytes")
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)
    logging.debug(f"File saved to: {file_path}")

    try:
        # Create a ZIP file containing the original file
        zip_filename = f"{os.path.splitext(filename)[0]}_compressed.zip"
        zip_path = os.path.join(COMPRESSED_FOLDER, zip_filename)
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(file_path, filename)  # Store file with original name
        logging.debug(f"Created ZIP file: {zip_path}")

        original_size = os.path.getsize(file_path)
        compressed_size = os.path.getsize(zip_path)
        compression_ratio = round(original_size / compressed_size, 2) if compressed_size > 0 else 0
        space_saving = round((1 - compressed_size / original_size) * 100, 2) if original_size > 0 else 0

        download_url = f"http://127.0.0.1:5000/download/{zip_filename}"
        logging.info(f"Compression successful: {filename}, ratio: {compression_ratio}, space saved: {space_saving}%")

        return jsonify({
            "message": "✅ File successfully compressed! Download the ZIP file and extract it to access the original file.",
            "download_url": download_url,
            "original_size_bytes": original_size,
            "compressed_size_bytes": compressed_size,
            "compression_ratio": compression_ratio,
            "space_saved_percent": space_saving
        })

    except Exception as e:
        logging.error(f"Compression error for {filename}: {str(e)}", exc_info=True)
        return jsonify({"message": f"❌ Error during compression: {str(e)}"}), 500

@app.route("/download/<path:filename>")
def download_file(filename):
    try:
        logging.debug(f"Downloading file: {filename}")
        return send_from_directory(COMPRESSED_FOLDER, filename, as_attachment=True)
    except Exception as e:
        logging.error(f"Download error for {filename}: {str(e)}", exc_info=True)
        return jsonify({"message": f"❌ Error downloading file: {str(e)}"}), 404

@app.route("/decompress", methods=["POST"])
def decompress_file():
    if "file" not in request.files:
        logging.error("No file part in request")
        return jsonify({"message": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        logging.error("No selected file")
        return jsonify({"message": "No selected file"}), 400

    filename = secure_filename(file.filename)
    if not filename.endswith('.zip'):
        logging.error(f"Invalid file type: {filename}, expected .zip")
        return jsonify({"message": "❌ Please upload a .zip file."}), 400

    zip_path = os.path.join(COMPRESSED_FOLDER, filename)
    file.save(zip_path)
    logging.debug(f"ZIP file saved to: {zip_path}")

    try:
        # Extract the ZIP file
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            extracted_files = zipf.namelist()
            if not extracted_files:
                raise ValueError("ZIP file is empty")
            if len(extracted_files) > 1:
                raise ValueError("ZIP file contains multiple files; only one file is supported.")
            extracted_file = extracted_files[0]  # Take first file
            # Validate extracted file extension
            allowed_extensions = {'.txt', '.pdf', '.png', '.jpg', '.docx'}
            file_ext = os.path.splitext(extracted_file)[1].lower()
            if file_ext not in allowed_extensions:
                raise ValueError(f"Extracted file has unsupported extension: {file_ext}")
            extracted_path = os.path.join(DECOMPRESSED_FOLDER, extracted_file)
            zipf.extract(extracted_file, DECOMPRESSED_FOLDER)
        
        logging.debug(f"Extracted file to: {extracted_path}")
        
        # Send the file with proper Content-Disposition header
        response = send_file(
            extracted_path,
            download_name=extracted_file,  # Ensure the original filename is used
            as_attachment=True
        )
        # Add the filename in the response headers for the frontend
        response.headers["X-Extracted-Filename"] = extracted_file
        return response

    except Exception as e:
        logging.error(f"Decompression error: {str(e)}", exc_info=True)
        return jsonify({"message": f"❌ Error during decompression: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)