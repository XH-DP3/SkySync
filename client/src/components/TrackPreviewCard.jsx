import PropTypes from "prop-types";

function TrackItem({ track }) {
  const artistLabel = track.artists?.length ? track.artists.join(", ") : "Unknown artist";

  return (
    <li className="preview-item">
      <div className="preview-item-left">
        {track.image_url ? (
          <img
            className="preview-art"
            src={track.image_url}
            alt={`${track.name} artwork`}
          />
        ) : (
          <div className="preview-art preview-art-placeholder" />
        )}
      </div>
      <div className="preview-item-content">
        <p className="preview-track-name">{track.name}</p>
        <p className="preview-track-meta">{artistLabel}</p>
        {track.genres?.length > 0 && (
          <p className="preview-track-genres">{track.genres.slice(0, 3).join(" · ")}</p>
        )}
      </div>
      <div className="preview-item-right">
        {track.explicit && <span className="explicit-badge">E</span>}
        {track.spotify_url && (
          <a href={track.spotify_url} target="_blank" rel="noreferrer" className="tiny-link-btn">
            Open
          </a>
        )}
      </div>
    </li>
  );
}

export default function TrackPreviewCard({ tracks }) {
  return (
    <div className="preview-bubble">
      <h2 className="bubble-subtitle">Preview Tracks</h2>
      <ol className="preview-list">
        {tracks.map((track) => (
          <TrackItem key={track.id} track={track} />
        ))}
      </ol>
    </div>
  );
}

TrackItem.propTypes = {
  track: PropTypes.shape({
    id: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    artists: PropTypes.arrayOf(PropTypes.string),
    genres: PropTypes.arrayOf(PropTypes.string),
    explicit: PropTypes.bool,
    image_url: PropTypes.string,
    spotify_url: PropTypes.string
  }).isRequired
};

TrackPreviewCard.propTypes = {
  tracks: PropTypes.arrayOf(TrackItem.propTypes.track).isRequired
};
