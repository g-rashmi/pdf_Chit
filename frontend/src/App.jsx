import React, { useState } from "react";
import { b_url } from "./config";
import AppBar from "@mui/material/AppBar";
import ReactMarkdown from "react-markdown";
import Toolbar from "@mui/material/Toolbar";
import { TbSend2 } from "react-icons/tb";
import { AiOutlinePlus } from "react-icons/ai";
import { FaFilePdf } from "react-icons/fa";
import axios from "axios";
import CircularProgress from "@mui/material/CircularProgress";

function App() {
  const [filen, setfile] = useState("");
  const [question, setQuestion] = useState("");
  const [chat, setChat] = useState([]);
  const [loader, setLoader] = useState(false);

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file || file.type !== "application/pdf") {
      alert("Please upload a valid PDF file.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    setfile(file.name);

    try {
      await axios.post(`${b_url}/upload`, formData);
      setChat([]);
    } catch (error) {
      alert("Failed to upload PDF.");
      console.error(error);
    }
  };

  const handleSend = async () => {
    if (!filen) {
      alert("Please upload a PDF first.");
      return;
    }
    if (!question.trim()) {
      alert("Please enter a question.");
      return;
    }

    setLoader(true);
    const formData = new FormData();
    formData.append("filename", filen);
    formData.append("question", question);

    try {
      const res = await axios.post(`${b_url}/ask`, formData);
      setChat((prevChat) => [
        ...prevChat,
        { question: question, answer: res.data.answer },
      ]);
      setQuestion("");
    } catch (error) {
      alert("Error getting the answer.");
      setChat((prevChat) => [...prevChat, { question: question, answer: "" }]);
      setQuestion("");
      console.error(error);
    } finally {
      setLoader(false);
      setQuestion("");
    }
  };

  return (
    <div
      style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}
    >
      <AppBar position="static" style={{ backgroundColor: "white" }}>
        <Toolbar style={{ justifyContent: "space-between" }}>
          <span
            style={{
              color: "black",
              fontWeight: "bold",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            {filen && <FaFilePdf size={20} color="green" />}
            {filen}
          </span>

          <div>
            <input
              type="file"
              id="fileUpload"
              style={{ display: "none" }}
              accept="application/pdf"
              onChange={handleFileChange}
            />
            <label
              htmlFor="fileUpload"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                backgroundColor: "white",
                color: "black",
                padding: "8px 16px",
                borderRadius: "8px",
                cursor: "pointer",
                border: "1px solid",
                fontWeight: "bold",
              }}
            >
              <AiOutlinePlus size={18} />
              {filen ? "" : "Upload PDF"}
            </label>
          </div>
        </Toolbar>
      </AppBar>

      <div style={{ padding: "20px", flex: 1, overflowY: "auto" }}>
        {chat.map((item, index) => (
          <div key={index} style={{ marginBottom: "16px" }}>
            <div
              style={{ fontWeight: "bold", fontSize: "16px", color: "#333" }}
            >
              Q: {item.question}
            </div>
            <div style={{ marginTop: "4px", color: "#555", fontSize: "15px" }}>
              A:
              <ReactMarkdown>{item.answer}</ReactMarkdown>
            </div>
          </div>
        ))}

        {loader && (
          <div
            style={{
              padding: "10px",
              display: "flex",
              justifyContent: "center",
            }}
          >
            <CircularProgress color="primary" />
          </div>
        )}
      </div>

      <div
        style={{
          position: "sticky",
          bottom: 0,
          padding: "10px",
          backgroundColor: "#fff",
          zIndex: 999,
          borderTop: "1px solid #eee",
        }}
      >
        <div style={{ position: "relative", width: "100%" }}>
          <input
            type="text"
            placeholder="Ask your question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            style={{
              width: "100%",
              height: "45px",
              borderRadius: "10px",
              border: "1px solid lightgray",
              paddingRight: "40px",
              paddingLeft: "10px",
              fontSize: "16px",
              boxSizing: "border-box",
            }}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
          />
          <TbSend2
            onClick={handleSend}
            style={{
              position: "absolute",
              right: "12px",
              top: "50%",
              transform: "translateY(-50%)",
              cursor: "pointer",
              fontSize: "22px",
              color: "gray",
            }}
          />
        </div>
      </div>
    </div>
  );
}

export default App;
