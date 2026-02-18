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
        {msg.content}
      </div>
    </div>
  );
};

export default Message;
