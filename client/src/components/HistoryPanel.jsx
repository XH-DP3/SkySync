import PropTypes from "prop-types";

export default function HistoryPanel({ items, onOpenPlaylist }) {
  return (
    <div className="history-bubble">
      <h2 className="bubble-subtitle">Playlist History</h2>
      {items.length === 0 ? (
        <p className="history-empty">No history yet. Generate a playlist to start.</p>
      ) : (
        <ul className="history-list">
          {items.map((item) => (
            <li key={item.id} className="history-item">
              <div>
                <p className="history-title">{item.title}</p>
                <p className="history-meta">
                  {item.whenLabel} · {item.locationLabel} · {item.modeLabel}
                </p>
              </div>
              <button
                className="tiny-link-btn"
                type="button"
                onClick={() => onOpenPlaylist(item.link)}
                disabled={!item.link}
              >
                Open
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

HistoryPanel.propTypes = {
  items: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      title: PropTypes.string.isRequired,
      link: PropTypes.string,
      whenLabel: PropTypes.string.isRequired,
      locationLabel: PropTypes.string.isRequired,
      modeLabel: PropTypes.string.isRequired
    })
  ).isRequired,
  onOpenPlaylist: PropTypes.func.isRequired
};
