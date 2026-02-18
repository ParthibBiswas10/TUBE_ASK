const LoadingDots = () => (
  <div
    style={{
      display: "flex",
      gap: 5,
      alignItems: "center",
      padding: "8px 16px",
    }}
  >
    {[0, 1, 2].map((i) => (
      <span
        key={i}
        style={{
          width: 7,
          height: 7,
          borderRadius: "50%",
          background: "#888",
          animation: `blink 1.2s infinite`,
          animationDelay: `${i * 0.2}s`,
          display: "inline-block",
        }}
      />
    ))}
  </div>
);

export default LoadingDots;
