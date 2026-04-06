import PropTypes from "prop-types";

export default function SharedPlaylistCard({ sharedItem }) {
  if (!sharedItem) {
    return null;
  }

  return (
    <div className="shared-bubble">
      <h2 className="bubble-subtitle">Shared Playlist</h2>
      <p className="shared-title">{sharedItem.title}</p>
      {sharedItem.description && <p className="shared-description">{sharedItem.description}</p>}
      <p className="shared-meta">
        {sharedItem.locationLabel} · {sharedItem.modeLabel}
      </p>
      {sharedItem.link ? (
        <a className="spotify-open-btn" href={sharedItem.link} target="_blank" rel="noreferrer">
          Open Shared Playlist
        </a>
      ) : (
        <p className="playlist-link-warning">Shared card did not include a playlist URL.</p>
      )}
    </div>
  );
}

SharedPlaylistCard.propTypes = {
  sharedItem: PropTypes.shape({
    title: PropTypes.string,
    description: PropTypes.string,
    link: PropTypes.string,
    locationLabel: PropTypes.string,
    modeLabel: PropTypes.string
  })
};

SharedPlaylistCard.defaultProps = {
  sharedItem: null
};
