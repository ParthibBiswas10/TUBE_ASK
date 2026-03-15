import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const ACCENT = "#FF3B3B";

const Message = ({ msg, index }) => {
  const isUser = msg.role === "user";
  return (
    <div
      style={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        marginBottom: "18px",
        animation: `fadeUp 0.3s ease forwards`,
        animationDelay: `${index * 0.04}s`,
        opacity: 0,
      }}
    >
      {!isUser && (
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
            marginRight: 10,
            flexShrink: 0,
            marginTop: 2,
            fontFamily: "'DM Mono', monospace",
          }}
        >
          AI
        </div>
      )}
      <div
        style={{
          maxWidth: "72%",
          background: isUser ? ACCENT : "rgba(255,255,255,0.05)",
          border: isUser ? "none" : "1px solid rgba(255,255,255,0.08)",
          color: isUser ? "#fff" : "#e8e8e8",
          padding: "12px 16px",
          borderRadius: isUser ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
          fontSize: 14,
          lineHeight: 1.65,
          fontFamily: "'DM Mono', monospace",
          letterSpacing: 0.2,
        }}
      >
        {isUser ? (
          msg.content
        ) : (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              p: ({ children }) => (
                <p style={{ margin: "0 0 8px 0", lineHeight: 1.65 }}>
                  {children}
                </p>
              ),
              strong: ({ children }) => (
                <strong style={{ color: "#fff", fontWeight: 700 }}>
                  {children}
                </strong>
              ),
              ul: ({ children }) => (
                <ul style={{ paddingLeft: 18, margin: "6px 0" }}>{children}</ul>
              ),
              ol: ({ children }) => (
                <ol style={{ paddingLeft: 18, margin: "6px 0" }}>{children}</ol>
              ),
              li: ({ children }) => (
                <li style={{ marginBottom: 4 }}>{children}</li>
              ),
              h2: ({ children }) => (
                <h2
                  style={{
                    color: "#fff",
                    fontSize: 15,
                    fontWeight: 700,
                    margin: "12px 0 6px",
                  }}
                >
                  {children}
                </h2>
              ),
              h3: ({ children }) => (
                <h3
                  style={{
                    color: "#fff",
                    fontSize: 14,
                    fontWeight: 700,
                    margin: "10px 0 4px",
                  }}
                >
                  {children}
                </h3>
              ),
              code: ({ children }) => (
                <code
                  style={{
                    background: "rgba(255,59,59,0.15)",
                    color: ACCENT,
                    padding: "2px 6px",
                    borderRadius: 4,
                    fontSize: 13,
                  }}
                >
                  {children}
                </code>
              ),
              hr: () => (
                <hr
                  style={{
                    border: "none",
                    borderTop: "1px solid rgba(255,255,255,0.1)",
                    margin: "10px 0",
                  }}
                />
              ),
            }}
          >
            {msg.content}
          </ReactMarkdown>
        )}
      </div>
    </div>
  );
};

export default Message;
