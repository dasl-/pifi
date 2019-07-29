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
    var row_class = this.props.video.color_mode;

    if (this.props.video.status === 'STATUS_PLAYING') {
      row_class += ' current';
    }

    if (this.props.video.is_favorite) {
      row_class += ' favorite';
    }


    return (
      <div className={"row playlist-video " + row_class}>
        <div className='col-xs-4 col-sm-4 playlist-video'>
          <div className='placeholder' style={{'backgroundImage': `url(${this.props.video.thumbnail})`}}>
          </div>
        </div>
        <div className='col-xs-7 col-sm-8 video-data'>
          <h5 className='title'>{this.props.video.title}</h5>
        </div>
        <div className='col-xs-7 col-sm-8 video-data'>
            <div onClick={(e) => this.handleFavoriteClick(e, this.props.video)}>
              <span className="glyphicon glyphicon-star" aria-hidden="true" />
            </div>
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