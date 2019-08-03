import React from 'react';

import api from 'api';

class PlaylistItem extends React.Component {
  constructor(props) {
    super(props);
    this.apiClient = new api();

    this.favoriteVideo = this.favoriteVideo.bind(this);
    this.nextVideo = this.nextVideo.bind(this);
  }

  render() {
    var row_class = 'color-mode-' + this.props.video.color_mode;

    if (this.props.video.is_favorite) {
      row_class += ' favorite';
    }

    return (
      <div className={"currently-playing-full " + row_class}>
        <div className='img-container'>
          <img src={this.props.video.thumbnail} />
          <span className='duration'>{this.props.video.duration}</span>
        </div>

        <div className="control-group">
          <div className='title'>{this.props.video.title}</div>

          <div className="input-group">
            <button className="btn btn-default fav-button" type="button" onClick={this.favoriteVideo}>
              <span className="glyphicon glyphicon-star" aria-hidden="true" />
            </button>
            <button className="btn btn-default" type="button" onClick={this.nextVideo}>
              <span className="glyphicon glyphicon-step-forward" aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  nextVideo(e) {
    e.preventDefault();
    this.apiClient.nextVideo(this.props.video.playlist_video_id);
  }

  favoriteVideo(e) {
    e.preventDefault();
    this.apiClient.favoriteVideo(this.props.video);
  }
}

export default PlaylistItem;