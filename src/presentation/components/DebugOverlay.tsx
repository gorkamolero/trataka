interface DebugOverlayProps {
  messages: string[];
}

export const DebugOverlay = ({ messages }: DebugOverlayProps) => {
  return (
    <div style={styles.container}>
      <div style={styles.content}>
        {messages.map((msg, idx) => (
          <div key={idx} style={styles.message}>
            {msg}
          </div>
        ))}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    position: 'absolute',
    top: '10px',
    left: '10px',
    right: '10px',
    maxHeight: '200px',
    overflow: 'auto',
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    padding: '10px',
    borderRadius: '5px',
    fontFamily: 'monospace',
    fontSize: '12px',
    color: '#00ff00',
    zIndex: 2000,
    pointerEvents: 'none',
  },
  content: {
    display: 'flex',
    flexDirection: 'column',
    gap: '5px',
  },
  message: {
    wordBreak: 'break-word',
  },
};
