import { useState, useRef, useEffect } from "react";
import Message from "./Message";
import LoadingDots from "./LoadingDots";

const ACCENT = "#FF3B3B";

const extractVideoId = (url) => {
  const match = url.match(
    /(?:youtu\.be\/|youtube\.com\/(?:watch\?v=|embed\/|v\/))([a-zA-Z0-9_-]{11})/,
  );
  return match ? match[1] : null;
};

export default function YouTubeQAApp() {
  const [videoUrl, setVideoUrl] = useState("");
  const [videoId, setVideoId] = useState(null);
  const [videoLoaded, setVideoLoaded] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [urlError, setUrlError] = useState("");
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleLoadVideo = async () => {
    const id = extractVideoId(videoUrl);
    if (!id) {
      setUrlError("Couldn't find a valid YouTube URL. Try again.");
      return;
    }
    setUrlError("");
    setVideoId(id);
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8080/load", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_url: videoUrl }),
      });
      const data = await res.json();

      if (!res.ok) {
        setUrlError(data.detail || "Failed to load video.");
        setLoading(false);
        return;
      }

      setVideoLoaded(true);
      setMessages([
        {
          role: "assistant",
          content: `Video loaded! Ask me anything about it — I'll analyze the transcript and answer your questions.`,
        },
      ]);
    } catch (error) {
      setUrlError(
        "Failed to connect to server. Make sure the backend is running.",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || !videoLoaded) return;
    const userMsg = { role: "user", content: input.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8080/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_url: videoUrl,
          question: userMsg.content,
        }),
      });
      const data = await res.json();

      if (!res.ok) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `Error: ${data.detail || "Something went wrong."}`,
          },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.answer },
        ]);
      }
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Failed to connect to server. Make sure the backend is running.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Bebas+Neue&display=swap');

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
          background: #0e0e0e;
          color: #e8e8e8;
          font-family: 'DM Mono', monospace;
          min-height: 100vh;
        }

        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }

        @keyframes blink {
          0%, 80%, 100% { opacity: 0.2; }
          40% { opacity: 1; }
        }

        @keyframes pulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(255,59,59,0.4); }
          50% { box-shadow: 0 0 0 8px rgba(255,59,59,0); }
        }

        input:focus, textarea:focus { outline: none; }

        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #333; border-radius: 2px; }

        .send-btn:hover { background: #ff1a1a !important; transform: scale(1.03); }
        .load-btn:hover { background: #ff1a1a !important; }
        .url-input:focus { border-color: ${ACCENT} !important; }
      `}</style>

      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          padding: "40px 20px 20px",
        }}
      >
        {/* Header */}
        <div style={{ width: "100%", maxWidth: 900, marginBottom: 32 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
            <h1
              style={{
                fontFamily: "'Bebas Neue', sans-serif",
                fontSize: 52,
                letterSpacing: 3,
                color: "#fff",
                lineHeight: 1,
              }}
            >
              TUBE
            </h1>
            <h1
              style={{
                fontFamily: "'Bebas Neue', sans-serif",
                fontSize: 52,
                letterSpacing: 3,
                color: ACCENT,
                lineHeight: 1,
              }}
            >
              ASK
            </h1>
          </div>
          <p
            style={{
              color: "#555",
              fontSize: 12,
              letterSpacing: 1,
              marginTop: 4,
            }}
          >
            PASTE A YOUTUBE LINK · ASK ANYTHING · GET ANSWERS
          </p>
        </div>

        {/* Main Layout */}
        <div
          style={{
            width: "100%",
            maxWidth: 900,
            display: "grid",
            gridTemplateColumns: videoLoaded ? "1fr 1fr" : "1fr",
            gap: 20,
            flex: 1,
          }}
        >
          {/* Left Panel */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* URL Input */}
            <div
              style={{
                background: "#141414",
                border: "1px solid #222",
                borderRadius: 12,
                padding: 20,
              }}
            >
              <p
                style={{
                  fontSize: 11,
                  color: "#555",
                  letterSpacing: 1,
                  marginBottom: 12,
                }}
              >
                YOUTUBE URL
              </p>
              <input
                className="url-input"
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleLoadVideo()}
                placeholder="https://youtube.com/watch?v=..."
                style={{
                  width: "100%",
                  background: "#0e0e0e",
                  border: "1px solid #2a2a2a",
                  borderRadius: 8,
                  padding: "10px 14px",
                  color: "#e8e8e8",
                  fontSize: 13,
                  fontFamily: "'DM Mono', monospace",
                  marginBottom: 10,
                  transition: "border-color 0.2s",
                }}
              />
              {urlError && (
                <p style={{ color: ACCENT, fontSize: 11, marginBottom: 10 }}>
                  {urlError}
                </p>
              )}
              <button
                className="load-btn"
                onClick={handleLoadVideo}
                style={{
                  width: "100%",
                  background: ACCENT,
                  color: "#fff",
                  border: "none",
                  borderRadius: 8,
                  padding: "10px",
                  fontSize: 12,
                  fontFamily: "'DM Mono', monospace",
                  letterSpacing: 1,
                  cursor: "pointer",
                  fontWeight: 500,
                  transition: "background 0.2s",
                }}
              >
                LOAD VIDEO
              </button>
            </div>

            {/* Video Embed */}
            {videoLoaded && videoId && (
              <div
                style={{
                  background: "#141414",
                  border: "1px solid #222",
                  borderRadius: 12,
                  overflow: "hidden",
                  animation: "fadeUp 0.4s ease forwards",
                }}
              >
                <iframe
                  width="100%"
                  height="220"
                  src={`https://www.youtube.com/embed/${videoId}`}
                  title="YouTube video"
                  frameBorder="0"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                  style={{ display: "block" }}
                />
              </div>
            )}

            {/* Info box */}
            {!videoLoaded && (
              <div
                style={{
                  background: "#141414",
                  border: "1px dashed #222",
                  borderRadius: 12,
                  padding: 24,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 12,
                  minHeight: 200,
                  textAlign: "center",
                }}
              >
                <div style={{ fontSize: 40 }}>🎬</div>
                <p
                  style={{
                    color: "#444",
                    fontSize: 12,
                    lineHeight: 1.7,
                    maxWidth: 280,
                  }}
                >
                  Paste a YouTube link above to load the video. Once loaded, the
                  AI will answer questions based on the transcript.
                </p>
              </div>
            )}
          </div>

          {/* Right Panel — Chat */}
          {videoLoaded && (
            <div
              style={{
                background: "#141414",
                border: "1px solid #222",
                borderRadius: 12,
                display: "flex",
                flexDirection: "column",
                height: "70vh",
                animation: "fadeUp 0.4s ease forwards",
              }}
            >
              <div
                style={{
                  padding: "14px 18px",
                  borderBottom: "1px solid #1e1e1e",
                  fontSize: 11,
                  color: "#555",
                  letterSpacing: 1,
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <span
                  style={{
                    width: 7,
                    height: 7,
                    borderRadius: "50%",
                    background: "#22c55e",
                    display: "inline-block",
                    animation: "pulse 2s infinite",
                  }}
                />
                CHAT WITH VIDEO
              </div>

              {/* Messages */}
              <div
                style={{
                  flex: 1,
                  overflowY: "auto",
                  padding: "18px",
                }}
              >
                {messages.map((msg, i) => (
                  <Message key={i} msg={msg} index={i} />
                ))}
                {loading && (
                  <div
                    style={{ display: "flex", alignItems: "center", gap: 8 }}
                  >
                    <div
                      style={{
                        width: 32,
                        height: 32,
                        borderRadius: "50%",
                        background: ACCENT,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: 14,
                        fontWeight: 700,
                        color: "#fff",
                        flexShrink: 0,
                      }}
                    >
                      AI
                    </div>
                    <div
                      style={{
                        background: "rgba(255,255,255,0.05)",
                        border: "1px solid rgba(255,255,255,0.08)",
                        borderRadius: "18px 18px 18px 4px",
                      }}
                    >
                      <LoadingDots />
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              {/* Input */}
              <div
                style={{
                  padding: 14,
                  borderTop: "1px solid #1e1e1e",
                  display: "flex",
                  gap: 10,
                }}
              >
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) =>
                    e.key === "Enter" && !e.shiftKey && handleSend()
                  }
                  placeholder="Ask something about the video..."
                  style={{
                    flex: 1,
                    background: "#0e0e0e",
                    border: "1px solid #2a2a2a",
                    borderRadius: 8,
                    padding: "10px 14px",
                    color: "#e8e8e8",
                    fontSize: 13,
                    fontFamily: "'DM Mono', monospace",
                  }}
                />
                <button
                  className="send-btn"
                  onClick={handleSend}
                  disabled={!input.trim() || loading}
                  style={{
                    background: ACCENT,
                    border: "none",
                    borderRadius: 8,
                    width: 44,
                    height: 44,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    transition: "all 0.2s",
                    flexShrink: 0,
                    opacity: !input.trim() || loading ? 0.4 : 1,
                  }}
                >
                  <svg
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="#fff"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <line x1="22" y1="2" x2="11" y2="13" />
                    <polygon points="22 2 15 22 11 13 2 9 22 2" />
                  </svg>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
