import React from 'react';

import api from 'api';

class PlaylistItem extends React.Component {
  constructor(props) {
    super(props);
    this.apiClient = new api();

    this.handleRemoveClick = this.handleRemoveClick.bind(this);
    this.handleFavoriteClick = this.handleFavoriteClick.bind(this);
  }

  render() {
    var row_class = 'color-mode-' + this.props.video.color_mode;

    if (this.props.video.status === 'STATUS_PLAYING') {
      row_class += ' current';
    }

    if (this.props.video.is_favorite) {
      row_class += ' favorite';
    }

    return (
      <div className={"row playlist-video " + row_class}>
        <div className='col-xs-4 col-sm-4 playlist-video'>
          <div className='img-container'>
            <div className='placeholder use-color-mode' style={{'backgroundImage': `url(${this.props.video.thumbnail})`}}>
            </div>
            <span className='duration'>{this.props.video.duration}</span>
          </div>
        </div>
        <div className='col-xs-7 col-sm-8 video-data'>
          <span className='title'>{this.props.video.title}</span>
          <span onClick={(e) => this.handleFavoriteClick(e, this.props.video)}>
            <span className="glyphicon glyphicon-star" aria-hidden="true" />
          </span>
        </div>
      </div>
    );
  }

  handleRemoveClick(e, video) {
    e.preventDefault();
    this.apiClient.removeVideo(video);
  }

  handleFavoriteClick(e, video) {
    e.preventDefault();
    this.apiClient.favoriteVideo(video);
  }
}

export default PlaylistItem;