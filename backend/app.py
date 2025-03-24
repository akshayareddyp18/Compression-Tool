from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import numpy as np
import zipfile
from collections import Counter, namedtuple
from heapq import heappush, heappop
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
COMPRESSED_FOLDER = "compressed"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(COMPRESSED_FOLDER, exist_ok=True)

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

@app.route("/", methods=["GET"])
def home():
    return "✅ Huffman & VAE Compression Backend is running!"

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
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    try:
        with open(file_path, 'rb') as f:
            content_bytes = f.read()

        huffman_compressed_bytes, codebook = huffman_compress_bytes(content_bytes)
        vae_compressed_data = vae_compress(huffman_compressed_bytes)

        output_zip = os.path.join(COMPRESSED_FOLDER, f"{filename}_compressed.zip")
        with zipfile.ZipFile(output_zip, 'w') as zipf:
            zipf.writestr(f"{filename}_compressed.bin", vae_compressed_data)

        original_size = os.path.getsize(file_path)
        compressed_size = os.path.getsize(output_zip)
        compression_ratio = round(original_size / compressed_size, 2) if compressed_size > 0 else 0
        space_saving = round((1 - compressed_size / original_size) * 100, 2) if original_size > 0 else 0

        # Print compression stats in console
        print(f"✅ Compression completed for {filename}")
        print(f"Original file size: {original_size} bytes")
        print(f"Compressed file size: {compressed_size} bytes")
        print(f"Compression Ratio: {compression_ratio}")
        print(f"Space Saved: {space_saving}%")

        download_url = f"http://127.0.0.1:5000/download/{filename}_compressed.zip"

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

if __name__ == "__main__":
    app.run(debug=True)
