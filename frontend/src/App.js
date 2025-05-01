import React, { useState } from "react";
import axios from "axios";

// Loading Spinner component
const LoadingSpinner = () => (
  <div className="spinner-container">
    <div className="spinner"></div>
  </div>
);

// Main App component
const App = () => {
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");
  const [downloadUrl, setDownloadUrl] = useState("");
  const [codebookFilename, setCodebookFilename] = useState("");
  const [compressionInfo, setCompressionInfo] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [loading, setLoading] = useState(false);
  const [decompressing, setDecompressing] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const backendUrl = process.env.REACT_APP_BACKEND_URL || "http://127.0.0.1:5000";

  // Handle file change and validation
  const handleFileChange = (selectedFile) => {
    const allowedTypes = ["text/plain", "application/pdf", "image/png", "application/zip"];
    if (selectedFile && !allowedTypes.includes(selectedFile.type)) {
      setMessage("❌ Unsupported file type! Please upload a text, PDF, PNG, or ZIP file.");
      return;
    }

    setFile(selectedFile);
    setMessage("");
    setDownloadUrl("");
    setCodebookFilename("");
    setCompressionInfo(null);
    setUploadProgress(0);
  };

  // Handle file input change
  const handleInputChange = (event) => {
    const selectedFile = event.target.files[0];
    handleFileChange(selectedFile);
  };

  // Handle drag-and-drop
  const handleDragOver = (event) => {
    event.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setIsDragging(false);
    const droppedFile = event.dataTransfer.files[0];
    handleFileChange(droppedFile);
  };

  // Handle file upload and compression
  const handleUpload = async () => {
    if (!file) {
      setMessage("❌ Please select a file first!");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      setLoading(true);
      const response = await axios.post(`${backendUrl}/upload`, formData, {
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          setUploadProgress(percentCompleted);
        },
      });
      setMessage("✅ Upload and compression successful!");
      setDownloadUrl(response.data.download_url);
      setCodebookFilename(response.data.codebook_filename);
      setCompressionInfo({
        originalSize: (response.data.original_size_bytes / 1024).toFixed(2),
        compressedSize: (response.data.compressed_size_bytes / 1024).toFixed(2),
        compressionRatio: response.data.compression_ratio,
        spaceSaved: response.data.space_saved_percent,
      });
    } catch (error) {
      console.error("Compression error:", error);
      const errorMessage = error.response?.data?.message || "❌ Error uploading or compressing the file.";
      setMessage(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // Handle file decompression
  const handleDecompress = async () => {
    if (!downloadUrl || !codebookFilename) {
      setMessage("❌ No compressed file or codebook available. Please upload and compress a file first.");
      return;
    }

    try {
      setDecompressing(true);
      const compressedFileName = downloadUrl.split("/").pop();
      console.log("Compressed filename:", compressedFileName);
      console.log("Codebook filename:", codebookFilename);

      const response = await axios.get(downloadUrl, { responseType: "blob" });

      const formData = new FormData();
      formData.append("file", new File([response.data], compressedFileName));
      formData.append("codebook_filename", codebookFilename);

      const decompressResponse = await axios.post(`${backendUrl}/decompress`, formData, {
        responseType: "blob",
      });

      const decompressedBlob = new Blob([decompressResponse.data]);
      const decompressedUrl = window.URL.createObjectURL(decompressedBlob);
      const link = document.createElement("a");
      link.href = decompressedUrl;
      link.setAttribute(
        "download",
        compressedFileName.replace("_compressed", "_decompressed")
      );
      document.body.appendChild(link);
      link.click();
      link.remove();

      setMessage("✅ File successfully decompressed!");
    } catch (error) {
      console.error("Decompression error:", error);
      const errorMessage = error.response?.data?.message || "❌ Error decompressing the file.";
      if (error.response?.data?.message.includes("Codebook file not found")) {
        setMessage("❌ Decompression failed: The codebook file is missing. Please re-upload and compress the file.");
      } else {
        setMessage(errorMessage);
      }
    } finally {
      setDecompressing(false);
    }
  };

  // Get file icon based on type
  const getFileIcon = (fileType) => {
    switch (fileType) {
      case "text/plain":
        return "📝";
      case "application/pdf":
        return "📄";
      case "image/png":
        return "🖼️";
      case "application/zip":
        return "📦";
      default:
        return "📁";
    }
  };

  return (
    <div className="app-container">
      <h1>File Compression Tool</h1>
      <div
        className={`drop-zone ${isDragging ? "drag-active" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        role="region"
        aria-label="File upload drop zone"
      >
        <input
          type="file"
          onChange={handleInputChange}
          className="file-input"
          id="file-upload"
          title="Upload a text, PDF, PNG, or ZIP file"
          aria-label="Select a file to upload"
        />
        <label htmlFor="file-upload" className="drop-zone-label">
          {file ? (
            <span>Selected: {file.name}</span>
          ) : (
            <span>Drag & drop a file here or click to browse</span>
          )}
        </label>
      </div>

      {file && (
        <div className="file-info card">
          <p>
            <span className="file-icon">{getFileIcon(file.type)}</span>
            <strong>File Name:</strong> {file.name}
          </p>
          <p><strong>Size:</strong> {(file.size / 1024).toFixed(2)} KB</p>
          <p><strong>Type:</strong> {file.type || "Unknown"}</p>
        </div>
      )}

      <button
        onClick={handleUpload}
        disabled={loading}
        className="action-button compress-button"
        title="Compress the selected file"
        aria-label="Upload and compress file"
      >
        {loading ? "Compressing..." : "Upload & Compress"}
      </button>

      {uploadProgress > 0 && (
        <div className="progress-bar" role="progressbar" aria-valuenow={uploadProgress} aria-valuemin="0" aria-valuemax="100">
          <div
            className="progress-fill"
            style={{ width: `${uploadProgress}%` }}
          >
            {uploadProgress}%
          </div>
        </div>
      )}

      {decompressing && (
        <div className="progress-bar indeterminate" role="progressbar" aria-busy="true">
          <div className="progress-fill-indeterminate"></div>
        </div>
      )}

      {compressionInfo && (
        <div className="compression-info card">
          <p><strong>Original Size:</strong> {compressionInfo.originalSize} KB</p>
          <p><strong>Compressed Size:</strong> {compressionInfo.compressedSize} KB</p>
          <p><strong>Compression Ratio:</strong> {compressionInfo.compressionRatio}</p>
          <p><strong>Space Saved:</strong> {compressionInfo.spaceSaved}%</p>
        </div>
      )}

      {message && (
        <div className={`message-card ${message.includes("Error") ? "error" : "success"}`} role="alert">
          <span className="message-icon">{message.includes("Error") ? "❌" : "✅"}</span>
          {message}
          <button
            className="dismiss-button"
            onClick={() => setMessage("")}
            aria-label="Dismiss message"
          >
            ✕
          </button>
        </div>
      )}

      {loading && <LoadingSpinner />}

      {downloadUrl && (
        <div className="action-buttons">
          <a href={downloadUrl} download>
            <button
              className="action-button download-button"
              title="Download the compressed file"
              aria-label="Download compressed file"
            >
              Download Compressed File
            </button>
          </a>

          <button
            onClick={handleDecompress}
            disabled={decompressing || !downloadUrl || !codebookFilename}
            className="action-button decompress-button"
            title="Decompress the downloaded file"
            aria-label="Decompress file"
          >
            {decompressing ? "Decompressing..." : "Decompress File"}
          </button>
        </div>
      )}

      <style>
        {`
          .app-container {
            background-color: #E6F0FA;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            padding: 40px;
            font-family: 'Inter', system-ui, Arial, sans-serif;
            max-width: 700px;
            margin: 40px auto;
            text-align: center;
            animation: fadeIn 0.5s ease-in;
          }

          h1 {
            color: #2C3E50;
            font-size: 28px;
            margin-bottom: 30px;
            font-weight: 600;
          }

          .drop-zone {
            background-color: #FFFFFF;
            border: 2px dashed #D1DCE5;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            transition: border-color 0.3s, background-color 0.3s;
          }

          .drop-zone.drag-active {
            border-color: #4A90E2;
            background-color: #F1F5F9;
          }

          .file-input {
            display: none;
          }

          .drop-zone-label {
            display: block;
            font-size: 16px;
            color: #2C3E50;
            cursor: pointer;
            padding: 10px;
          }

          .drop-zone-label span {
            font-weight: 500;
          }

          .card {
            background-color: #FFFFFF;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            padding: 20px;
            margin: 20px 0;
            text-align: left;
            font-size: 16px;
            line-height: 1.6;
            animation: slideIn 0.3s ease-in;
          }

          .card p {
            margin: 8px 0;
            color: #2C3E50;
            display: flex;
            align-items: center;
            gap: 8px;
          }

          .file-icon {
            font-size: 20px;
          }

          .action-button {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            color: #FFFFFF;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
            margin: 8px;
            transition: background-color 0.3s, transform 0.2s, box-shadow 0.3s;
          }

          .action-button:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
          }

          .compress-button {
            background: linear-gradient(45deg, #4A90E2, #6AB0F3);
          }

          .compress-button:hover:not(:disabled) {
            background: linear-gradient(45deg, #3A80D2, #5AA0E3);
          }

          .download-button {
            background: linear-gradient(45deg, #2ECC71, #4BE98D);
          }

          .download-button:hover:not(:disabled) {
            background: linear-gradient(45deg, #1EBC61, #3BD97D);
          }

          .decompress-button {
            background: linear-gradient(45deg, #E67E22, #F89C44);
          }

          .decompress-button:hover:not(:disabled) {
            background: linear-gradient(45deg, #D66E12, #E88C34);
          }

          .action-button:disabled {
            background-color: #D1DCE5;
            cursor: not-allowed;
            transform: none;
          }

          .progress-bar {
            width: 100%;
            max-width: 400px;
            margin: 20px auto;
            background-color: #F1F5F9;
            border-radius: 6px;
            height: 20px;
            overflow: hidden;
            position: relative;
          }

          .progress-fill {
            height: 100%;
            background: linear-gradient(45deg, #4A90E2, #6AB0F3);
            border-radius: 6px;
            transition: width 0.4s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #FFFFFF;
            font-size: 12px;
            font-weight: 500;
          }

          .progress-bar.indeterminate .progress-fill-indeterminate {
            width: 50%;
            height: 100%;
            background: linear-gradient(45deg, #4A90E2, #6AB0F3);
            border-radius: 6px;
            animation: indeterminate 1.5s linear infinite;
          }

          @keyframes indeterminate {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(200%); }
          }

          .message-card {
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 20px auto;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 500;
            max-width: 500px;
            position: relative;
            animation: slideIn 0.3s ease-in;
          }

          .message-card.success {
            background-color: #E8F8F5;
            color: #2ECC71;
          }

          .message-card.error {
            background-color: #FDECEA;
            color: #E74C3C;
          }

          .message-icon {
            margin-right: 8px;
            font-size: 20px;
          }

          .dismiss-button {
            background: none;
            border: none;
            color: #7F8C8D;
            font-size: 16px;
            cursor: pointer;
            position: absolute;
            right: 10px;
            top: 50%;
            transform: translateY(-50%);
          }

          .dismiss-button:hover {
            color: #2C3E50;
          }

          .spinner-container {
            display: flex;
            justify-content: center;
            padding: 20px;
          }

          .spinner {
            border: 6px solid #F1F5F9;
            border-top: 6px solid #4A90E2;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1.5s linear infinite;
          }

          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }

          @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
          }

          @keyframes slideIn {
            from { transform: translateY(20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
          }

          .action-buttons {
            display: flex;
            justify-content: center;
            gap: 16px;
            margin-top: 20px;
          }

          /* Responsive Design */
          @media (max-width: 600px) {
            .app-container {
              padding: 20px;
              margin: 20px;
            }

            h1 {
              font-size: 24px;
            }

            .drop-zone {
              padding: 15px;
            }

            .card {
              padding: 15px;
              font-size: 14px;
            }

            .action-button {
              padding: 10px 20px;
              font-size: 14px;
            }

            .progress-bar {
              max-width: 100%;
            }

            .action-buttons {
              flex-direction: column;
              gap: 10px;
            }
          }
        `}
      </style>
    </div>
  );
};

export default App;