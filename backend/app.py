from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import os
import numpy as np
from collections import Counter, namedtuple
from heapq import heappush, heappop
from werkzeug.utils import secure_filename
import json
import logging

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

# Huffman Tree node
Node = namedtuple("Node", ["freq", "symbol", "left", "right"])

def build_huffman_tree(frequencies):
    heap = []
    # Add a counter to break ties and avoid comparing Node objects directly
    counter = 0
    for byte_val, freq in frequencies.items():
        heappush(heap, (freq, counter, Node(freq, byte_val, None, None)))
        counter += 1

    while len(heap) > 1:
        freq1, count1, left = heappop(heap)
        freq2, count2, right = heappop(heap)
        merged = Node(freq1 + freq2, None, left, right)
        heappush(heap, (merged.freq, counter, merged))
        counter += 1

    return heappop(heap)[2] if heap else None

def create_codes(node, prefix="", codebook={}):
    if node.symbol is not None:
        codebook[node.symbol] = prefix
    else:
        create_codes(node.left, prefix + "0", codebook)
        create_codes(node.right, prefix + "1", codebook)
    return codebook

def huffman_compress_bytes(content_bytes):
    if not content_bytes:
        logging.warning("Input data is empty")
        return b"", {}, 0

    frequencies = Counter(content_bytes)
    if len(frequencies) == 1:
        byte_val = next(iter(frequencies))
        logging.debug(f"Single byte input detected: {byte_val}")
        return bytes([byte_val]), {byte_val: "0"}, 0

    tree = build_huffman_tree(frequencies)
    if not tree:
        raise ValueError("Failed to build Huffman tree")

    codebook = create_codes(tree)
    compressed_bits = ''.join(codebook[b] for b in content_bytes)

    padding = 8 - (len(compressed_bits) % 8) if len(compressed_bits) % 8 != 0 else 0
    compressed_bits += '0' * padding

    compressed_bytes = int(compressed_bits, 2).to_bytes((len(compressed_bits) + 7) // 8, byteorder='big')
    return compressed_bytes, codebook, padding

def vae_compress(content_bytes):
    if not content_bytes:
        raise ValueError("Input data is empty")
    arr = np.frombuffer(content_bytes, dtype=np.uint8)
    downsampled = arr[::2]
    logging.debug(f"VAE compressed {len(content_bytes)} bytes to {len(downsampled)} bytes")
    return downsampled.tobytes()

def vae_decompress(content_bytes):
    if not content_bytes:
        raise ValueError("Compressed data is empty")
    decompressed = bytearray()
    for b in content_bytes:
        decompressed.extend([b, 0])
    logging.debug(f"VAE decompressed {len(content_bytes)} bytes to {len(decompressed)} bytes")
    return decompressed

def huffman_decompress(compressed_bytes, codebook, padding):
    if not compressed_bytes:
        logging.warning("Compressed data is empty")
        return b""

    inverse_codebook = {v: int(k) for k, v in codebook.items()}

    bitstream = bin(int.from_bytes(compressed_bytes, byteorder='big'))[2:]
    bitstream = bitstream.zfill(len(compressed_bytes) * 8)[:-padding] if padding else bitstream
    logging.debug(f"Bitstream length: {len(bitstream)} bits")

    decoded_bytes = bytearray()
    current_code = ""
    for bit in bitstream:
        current_code += bit
        if current_code in inverse_codebook:
            decoded_bytes.append(inverse_codebook[current_code])
            current_code = ""
    if current_code:
        logging.warning(f"Unprocessed bits remaining: {current_code}")
    if not decoded_bytes:
        logging.warning("No valid codes found in bitstream")
    logging.debug(f"Decoded {len(decoded_bytes)} bytes")
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
        return jsonify({"message": f"Unsupported file type: {file_ext}. Use .txt, .pdf, .png, or .zip."}), 400

    filename = secure_filename(file.filename)
    logging.info(f"Processing file: {filename}, original extension: {file_ext}, size: {file.content_length or 'unknown'} bytes")
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)
    logging.debug(f"File saved to: {file_path}")

    try:
        with open(file_path, 'rb') as f:
            content_bytes = f.read()
        logging.info(f"Read {len(content_bytes)} bytes from {filename}")

        huffman_compressed_bytes, codebook, padding = huffman_compress_bytes(content_bytes)
        logging.debug(f"Huffman compression result: {len(huffman_compressed_bytes)} bytes, codebook size: {len(codebook)}, padding: {padding}")

        if not huffman_compressed_bytes:
            raise ValueError("Huffman compression produced no output")

        vae_compressed_data = vae_compress(huffman_compressed_bytes)
        logging.debug(f"VAE compression result: {len(vae_compressed_data)} bytes")

        output_filename = f"{os.path.splitext(filename)[0]}_compressed{file_ext}"
        output_path = os.path.join(COMPRESSED_FOLDER, output_filename)
        logging.debug(f"Saving compressed file to: {output_path}")
        with open(output_path, 'wb') as compressed_file:
            compressed_file.write(vae_compressed_data)

        codebook_filename = f"{os.path.splitext(filename)[0]}_codebook.json"
        codebook_path = os.path.join(COMPRESSED_FOLDER, codebook_filename)
        logging.debug(f"Saving codebook to: {codebook_path}")
        with open(codebook_path, 'w') as codebook_file:
            json.dump({"codebook": {str(k): v for k, v in codebook.items()}, "padding": padding}, codebook_file)
            logging.debug("Codebook saved successfully")

        original_size = os.path.getsize(file_path)
        compressed_size = os.path.getsize(output_path)
        compression_ratio = round(original_size / compressed_size, 2) if compressed_size > 0 else 0
        space_saving = round((1 - compressed_size / original_size) * 100, 2) if original_size > 0 else 0

        download_url = f"http://127.0.0.1:5000/download/{output_filename}"
        logging.info(f"Compression successful: {filename}, ratio: {compression_ratio}, space saved: {space_saving}%")

        return jsonify({
            "message": "✅ File successfully compressed!",
            "download_url": download_url,
            "codebook_filename": codebook_filename,
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

    codebook_filename = request.form.get("codebook_filename")
    if not codebook_filename:
        logging.error("No codebook filename provided")
        return jsonify({"message": "❌ Codebook filename not provided."}), 400

    filename = secure_filename(file.filename)
    logging.debug(f"Received file for decompression: {filename}")
    compressed_path = os.path.join(COMPRESSED_FOLDER, filename)
    file.save(compressed_path)

    codebook_path = os.path.join(COMPRESSED_FOLDER, secure_filename(codebook_filename))
    logging.debug(f"Looking for codebook: {codebook_path}")

    if not os.path.exists(codebook_path):
        logging.error(f"Codebook not found: {codebook_path}")
        return jsonify({"message": f"❌ Codebook file not found: {codebook_filename}"}), 400

    try:
        with open(compressed_path, 'rb') as f:
            compressed_data = f.read()

        logging.debug(f"Loading codebook: {codebook_path}")
        with open(codebook_path, 'r') as f:
            codebook_data = json.load(f)
            codebook = {int(k): v for k, v in codebook_data["codebook"].items()}
            padding = codebook_data.get("padding", 0)

        logging.debug("Starting VAE decompression")
        huffman_bytes = vae_decompress(compressed_data)
        logging.debug("Starting Huffman decompression")
        original_data = huffman_decompress(huffman_bytes, codebook, padding)

        output_filename = filename.replace("_compressed", "_decompressed")
        output_path = os.path.join(DECOMPRESSED_FOLDER, output_filename)

        logging.debug(f"Saving decompressed file to: {output_path}")
        with open(output_path, 'wb') as out_file:
            out_file.write(original_data)

        logging.debug(f"Sending decompressed file: {output_filename}")
        return send_file(
            output_path,
            download_name=output_filename,
            as_attachment=True
        )

    except Exception as e:
        logging.error(f"Decompression error: {str(e)}", exc_info=True)
        return jsonify({"message": f"❌ Error during decompression: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)