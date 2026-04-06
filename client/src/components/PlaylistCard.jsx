import PropTypes from "prop-types";

function FeaturePill({ label, value }) {
  return (
    <span className="feature-pill">
      {label}: {value}
    </span>
  );
}

FeaturePill.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.number.isRequired
};

export default function PlaylistCard({ playlist, shareUrl, onCopyShareUrl }) {
  const hasLink = Boolean(playlist.link);
  const hasSongParams = Boolean(playlist.songParams);

  return (
    <div className="playlist-bubble">
      <h1 className="bubble-title playlist-main-title">{playlist.title}</h1>

      {playlist.description && (
        <div className="playlist-description">
          <p className="description-text">{playlist.description}</p>
        </div>
      )}

      <p className="ready-text">Your personalized playlist is ready.</p>

      {hasSongParams && (
        <div className="feature-pill-row">
          <FeaturePill label="Valence" value={playlist.songParams.valence} />
          <FeaturePill label="Danceability" value={playlist.songParams.danceability} />
          <FeaturePill label="Energy" value={playlist.songParams.energy} />
        </div>
      )}

      {playlist.warnings?.length > 0 && (
        <ul className="warning-list">
          {playlist.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      )}

      {hasLink ? (
        <div className="playlist-action-row">
          <a
            className="spotify-open-btn"
            href={playlist.link}
            target="_blank"
            rel="noreferrer"
          >
            Open Playlist
          </a>
          <button className="tiny-link-btn" type="button" onClick={onCopyShareUrl}>
            Copy Share Link
          </button>
        </div>
      ) : (
        <p className="playlist-link-warning">
          Playlist created, but no Spotify URL was returned.
        </p>
      )}

      {shareUrl && <p className="share-url-text">{shareUrl}</p>}
    </div>
  );
}

PlaylistCard.propTypes = {
  playlist: PropTypes.shape({
    title: PropTypes.string.isRequired,
    description: PropTypes.string,
    link: PropTypes.string,
    warnings: PropTypes.arrayOf(PropTypes.string),
    songParams: PropTypes.shape({
      valence: PropTypes.number,
      danceability: PropTypes.number,
      energy: PropTypes.number
    })
  }).isRequired,
  shareUrl: PropTypes.string,
  onCopyShareUrl: PropTypes.func
};

PlaylistCard.defaultProps = {
  shareUrl: "",
  onCopyShareUrl: () => {}
};
