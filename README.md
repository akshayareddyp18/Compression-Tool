# SmartCompress – Hybrid File Compression using VQ-VAE and Huffman Coding

**SmartCompress** is an intelligent file compression system that integrates **Vector Quantized Variational Autoencoders (VQ-VAE)** and **Huffman Coding** for efficient and lossless compression of various file types. This hybrid approach combines deep learning-based feature reduction with classical entropy encoding, achieving high compression ratios while maintaining data integrity.

## System Architecture
The SmartCompress system consists of the following components:
- Data Preprocessing
- Autoencoder-Based Compression (VQ-VAE)
- Latent Vector Quantization
- Huffman Coding for Lossless Compression
- Decompression with Reconstruction
  
## Implementation Details
### Data Preprocessing
- Supports `.txt`, `.pdf`, `.png`, and other file types.
- Converts text to character/byte sequences and images to pixel tensors.
- Standardizes input length and format for training the encoder.

### Autoencoder-Based Compression
- Uses dense neural networks for encoding and decoding.
- Compresses input into a low-dimensional latent space.
- Encoder → Latent Vector → Decoder reconstructs input with minimal loss.

### Quantization (VQ-VAE)
- Latent vectors are quantized using a codebook.
- Each continuous vector is mapped to the closest discrete code.
- Enables symbolic representation suitable for Huffman coding.

### Huffman Coding
- Applies entropy coding on quantized vectors.
- Shorter codes for frequent symbols, enabling efficient lossless compression.
- Codebook is stored for accurate decompression.

### Decompression Workflow
- Huffman decoder reconstructs quantized latent vectors.
- VQ-VAE decoder regenerates the original file.
- Output matches original format and structure.

## Sample Compression Result

| File Name   | Original Size | Compressed Size | Decompressed Size | Compression Ratio | Space Saved |
|-------------|----------------|------------------|---------------------|-------------------|--------------|
| report.pdf  | 494.94 KB      | 207.82 KB        | 447.00 KB           | 2.38              | 58.01%       |

---

## Compression Flow
```text
Input File → Preprocessing → VQ-VAE Encoder → Quantization → Huffman Coding → Compressed Output

Compressed File → Huffman Decoding → VQ-VAE Decoder → Output File
