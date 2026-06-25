// Minimal sketch-styled dialog. Click backdrop or ✕ to close.
export default function Modal({ children, onClose, width }) {
  return (
    <div className="backdrop" onClick={onClose}>
      <div className="dialog" style={width ? { maxWidth: width } : undefined}
        onClick={(e) => e.stopPropagation()}>
        <button className="btn btn-ghost btn-sm dialog-x" onClick={onClose}>✕</button>
        {children}
      </div>
    </div>
  );
}

export function scoreClass(n) {
  return n >= 70 ? "good" : n >= 45 ? "ok" : "low";
}
