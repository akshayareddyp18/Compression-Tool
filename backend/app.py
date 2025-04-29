from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import os
import numpy as np
import zipfile
from collections import Counter, namedtuple
from heapq import heappush, heappop
from werkzeug.utils import secure_filename
import json
import io

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
COMPRESSED_FOLDER = "compressed"
DECOMPRESSED_FOLDER = "decompressed"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(COMPRESSED_FOLDER, exist_ok=True)
os.makedirs(DECOMPRESSED_FOLDER, exist_ok=True)

# Huffman Tree node
Node = namedtuple("Node", ["freq", "symbol", "left", "right"])

def build_huffman_tree(frequencies):
    heap = []
    for byte_val, freq in frequencies.items():
        heappush(heap, (freq, Node(freq, byte_val, None, None)))

    while len(heap) > 1:
        freq1, left = heappop(heap)
        freq2, right = heappop(heap)
        merged = Node(freq1 + freq2, None, left, right)
        heappush(heap, (merged.freq, merged))

    return heappop(heap)[1]

def create_codes(node, prefix="", codebook={}):
    if node.symbol is not None:
        codebook[node.symbol] = prefix
    else:
        create_codes(node.left, prefix + "0", codebook)
        create_codes(node.right, prefix + "1", codebook)
    return codebook

def huffman_compress_bytes(content_bytes):
    frequencies = Counter(content_bytes)
    tree = build_huffman_tree(frequencies)
    codebook = create_codes(tree)
    compressed_bits = ''.join([codebook[b] for b in content_bytes])

    padding = 8 - (len(compressed_bits) % 8)
    compressed_bits += '0' * padding

    compressed_bytes = int(compressed_bits, 2).to_bytes((len(compressed_bits)) // 8, byteorder='big')
    return compressed_bytes, codebook

def vae_compress(content_bytes):
    arr = np.frombuffer(content_bytes, dtype=np.uint8)
    downsampled = arr[::2]
    return downsampled.tobytes()

def vae_decompress(content_bytes):
    decompressed = bytearray()
    for b in content_bytes:
        decompressed.extend([b, 0])
    return decompressed

def huffman_decompress(compressed_bytes, codebook):
    inverse_codebook = {v: int(k) for k, v in codebook.items()}

    bitstream = bin(int.from_bytes(compressed_bytes, byteorder='big'))[2:]
    bitstream = bitstream.zfill(len(compressed_bytes) * 8)

    decoded_bytes = bytearray()
    current_code = ""
    for bit in bitstream:
        current_code += bit
        if current_code in inverse_codebook:
            decoded_bytes.append(inverse_codebook[current_code])
            current_code = ""
    return bytes(decoded_bytes)

@app.route("/", methods=["GET"])
def home():
    return "Successfully running!"

@app.route("/status", methods=["GET"])
def status():
    return jsonify({"status": "Backend is running!"})

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"message": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"message": "No selected file"}), 400

    filename = secure_filename(file.filename)
    file_extension = os.path.splitext(filename)[1]
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    try:
        with open(file_path, 'rb') as f:
            content_bytes = f.read()

        huffman_compressed_bytes, codebook = huffman_compress_bytes(content_bytes)
        vae_compressed_data = vae_compress(huffman_compressed_bytes)

        output_zip = os.path.join(COMPRESSED_FOLDER, f"{os.path.splitext(filename)[0]}_compressed.zip")
        with zipfile.ZipFile(output_zip, 'w') as zipf:
            zipf.writestr(f"{os.path.splitext(filename)[0]}_compressed.bin", vae_compressed_data)
            zipf.writestr(f"{os.path.splitext(filename)[0]}_codebook.json", json.dumps({str(k): v for k, v in codebook.items()}))

        original_size = os.path.getsize(file_path)
        compressed_size = os.path.getsize(output_zip)
        compression_ratio = round(original_size / compressed_size, 2) if compressed_size > 0 else 0
        space_saving = round((1 - compressed_size / original_size) * 100, 2) if original_size > 0 else 0

        download_url = f"http://127.0.0.1:5000/download/{os.path.basename(output_zip)}"

        return jsonify({
            "message": "✅ File successfully compressed!",
            "download_url": download_url,
            "original_size_bytes": original_size,
            "compressed_size_bytes": compressed_size,
            "compression_ratio": compression_ratio,
            "space_saved_percent": space_saving
        })

    except Exception as e:
        return jsonify({"message": f"❌ Error occurred: {str(e)}"}), 500

@app.route("/download/<path:filename>")
def download_file(filename):
    return send_from_directory(os.path.abspath(COMPRESSED_FOLDER), filename, as_attachment=True)

@app.route("/decompress", methods=["POST"])
def decompress_file():
    if "file" not in request.files:
        return jsonify({"message": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"message": "No selected file"}), 400

    filename = secure_filename(file.filename)
    zip_path = os.path.join(COMPRESSED_FOLDER, filename)
    file.save(zip_path)

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(DECOMPRESSED_FOLDER)
            extracted_files = zip_ref.namelist()

        bin_file = next(f for f in extracted_files if f.endswith('.bin'))
        codebook_file = next(f for f in extracted_files if f.endswith('.json'))

        with open(os.path.join(DECOMPRESSED_FOLDER, bin_file), 'rb') as f:
            vae_compressed_data = f.read()

        with open(os.path.join(DECOMPRESSED_FOLDER, codebook_file), 'r') as f:
            codebook = json.load(f)

        huffman_bytes = vae_decompress(vae_compressed_data)
        original_data = huffman_decompress(huffman_bytes, codebook)

        # Preserving original file extension during decompression
        file_extension = os.path.splitext(filename)[1]
        return send_file(
            io.BytesIO(original_data),
            download_name=f"{os.path.splitext(filename)[0]}_decompressed{file_extension}",
            as_attachment=True
        )

    except Exception as e:
        return jsonify({"message": f"❌ Error during decompression: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
