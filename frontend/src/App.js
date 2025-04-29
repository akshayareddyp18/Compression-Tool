import React, { useState } from "react";
import axios from "axios";

function App() {
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");
  const [downloadUrl, setDownloadUrl] = useState("");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [loading, setLoading] = useState(false);
  const [decompressing, setDecompressing] = useState(false);

  const backendUrl = process.env.REACT_APP_BACKEND_URL || "http://127.0.0.1:5000";

  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
    setMessage("");
    setDownloadUrl("");
    setUploadProgress(0);
  };

  const handleUpload = async () => {
    if (!file) return alert("Please select a file first!");

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
      setMessage(response.data.message);
      setDownloadUrl(response.data.download_url);
      alert("✅ Upload and compression successful!");
    } catch (error) {
      console.error(error);
      setMessage("❌ Error uploading or compressing the file.");
      alert("❌ Error occurred. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleDecompress = async () => {
    if (!downloadUrl) return alert("No compressed file found to decompress!");

    try {
      setDecompressing(true);
      const compressedFileName = downloadUrl.split("/").pop();
      const response = await axios.get(downloadUrl, { responseType: "blob" });

      const formData = new FormData();
      formData.append("file", new File([response.data], compressedFileName));

      const decompressResponse = await axios.post(`${backendUrl}/decompress`, formData, {
        responseType: "blob",
      });

      const decompressedBlob = new Blob([decompressResponse.data]);
      const decompressedUrl = window.URL.createObjectURL(decompressedBlob);
      const link = document.createElement("a");
      link.href = decompressedUrl;
      link.setAttribute("download", compressedFileName.replace("_compressed.zip", "_decompressed" + compressedFileName.split('.').pop()));
      document.body.appendChild(link);
      link.click();
      link.remove(); // Simplified instead of removeChild

      setMessage("✅ File successfully decompressed!");
      alert("✅ Decompression successful!");
    } catch (error) {
      console.error(error);
      setMessage("❌ Error decompressing the file.");
      alert("❌ Decompression error. Please try again.");
    } finally {
      setDecompressing(false);
    }
  };

  return (
    <div style={{ textAlign: "center", padding: "30px", fontFamily: "Arial" }}>
      <h1 style={{ color: "#4A90E2" }}>File Compression Tool</h1>
      <input type="file" onChange={handleFileChange} />

      {file && (
        <div style={{ marginTop: "10px" }}>
          <p><strong>File Name:</strong> {file.name}</p>
          <p><strong>Size:</strong> {(file.size / 1024).toFixed(2)} KB</p>
          <p><strong>Type:</strong> {file.type || "Unknown"}</p>
        </div>
      )}

      <button
        onClick={handleUpload}
        disabled={loading}
        style={{
          marginTop: "15px",
          padding: "10px 20px",
          backgroundColor: "#4A90E2",
          color: "white",
          border: "none",
          borderRadius: "8px",
          cursor: "pointer",
        }}
      >
        {loading ? "Compressing..." : "Upload & Compress"}
      </button>

      {uploadProgress > 0 && (
        <div style={{ width: "300px", margin: "15px auto", border: "1px solid #ccc", borderRadius: "5px" }}>
          <div
            style={{
              width: `${uploadProgress}%`,
              height: "10px",
              backgroundColor: "#4A90E2",
              borderRadius: "5px",
            }}
          ></div>
        </div>
      )}

      {message && <p style={{ marginTop: "15px", fontSize: "18px" }}>{message}</p>}

      {downloadUrl && (
        <div>
          <button
            onClick={handleDecompress}
            disabled={decompressing}
            style={{
              marginTop: "15px",
              padding: "10px 20px",
              backgroundColor: "#32CD32",
              color: "white",
              border: "none",
              borderRadius: "8px",
              cursor: "pointer",
            }}
          >
            {decompressing ? "Decompressing..." : "Decompress"}
          </button>
        </div>
      )}
    </div>
  );
}

export default App;
