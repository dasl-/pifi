import React from 'react';

import './playlist.css';

class PlaylistVideo extends React.Component {
  constructor(props) {
    super(props);

    this.onRemoveVideo = this.onRemoveVideo.bind(this);
  }

  render() {
    var row_class = 'container py-2 px-0 mt-2 '
      + (this.props.loading ? 'playlist-video-loading' : 'playlist-video');

    return (
      <div className={row_class}>
        <div className='row mr-0'>
          <div className='col-4 px-2 pl-3 small-vertical-center'>
            <img
              className='img-fluid'
              src={this.props.video.thumbnail}
              alt={this.props.video.title}
              onLoad={this.props.setImageLoaded}
            />
          </div>
          <div className='col-7 px-2'>
            <div className='small'>{this.props.video.title}</div>
            <div className='small badge badge-secondary'>{this.props.video.duration}</div>
          </div>
          <div className='col-1 p-0 small-vertical-center'>
            <a href='#' onClick={this.onRemoveVideo}>
              <span className='glyphicon glyphicon-remove bg-light-text' aria-hidden='true' />
            </a>
          </div>
        </div>
      </div>
    );
  }

  onRemoveVideo(e) {
    e.preventDefault();
    this.props.setLoading();
    this.props.removeVideo(this.props.video);
  }
}

export default PlaylistVideo;