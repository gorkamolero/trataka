interface AudioIndicatorProps {
  breathIntensity: number;
  volume: number;
}

export const AudioIndicator = ({
  breathIntensity,
  volume,
}: AudioIndicatorProps) => {
  return (
    <div style={styles.container}>
      <div style={{ ...styles.bar, width: `${breathIntensity * 100}%` }} />
      <div
        style={{
          ...styles.bar,
          width: `${volume * 100}%`,
          backgroundColor: "rgba(76, 175, 80, 0.6)",
        }}
      />
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    height: "4px",
    display: "flex",
    flexDirection: "column",
    gap: "1px",
    zIndex: 1000,
  },
  bar: {
    height: "2px",
    backgroundColor: "rgba(255, 107, 53, 0.6)",
    transition: "width 0.1s ease-out",
  },
};
