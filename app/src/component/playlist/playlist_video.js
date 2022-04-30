import React from 'react';

import './playlist.css';
import {ReactComponent as PlayNextIcon} from '../../play-next-icon-filled.svg';

class PlaylistVideo extends React.Component {
  constructor(props) {
    super(props);

    this.onRemoveVideo = this.onRemoveVideo.bind(this);
    this.onPlayVideoNext = this.onPlayVideoNext.bind(this);
  }

  render() {
    var row_class = 'container py-2 px-0 playlist-video-common '
      + (this.props.loading ? 'playlist-video-loading' : 'playlist-video');

    return (
      <div className={row_class}>
        <div className='row mr-0'>
          <div className='col-4 px-2 pl-3 small-vertical-center'>
            <div className='playlist-video-thumbnail-container'>
              <img
                className='img-fluid'
                src={this.props.video.thumbnail}
                alt={this.props.video.title}
                onLoad={this.props.setImageLoaded}
              />
            </div>
          </div>
          <div className='col-7 px-2'>
            <div className='small'>{this.props.video.title}</div>
            <div className='small badge badge-secondary'>{this.props.video.duration}</div>
          </div>
          <div className='col-1 p-0 playlist-video-icon-container align-items-end'>
              <a href='#' onClick={this.onRemoveVideo}>
                <span className='glyphicon glyphicon-remove bg-light-text' aria-hidden='true' />
              </a>
              {
                (this.props.index !== 0) &&
                <PlayNextIcon className='play-next-icon svg-icon' onClick={this.onPlayVideoNext} />
              }
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

  onPlayVideoNext(e) {
    e.preventDefault();
    this.props.setLoading();
    this.props
      .playVideoNext(this.props.video)
      .then(this.props.removeLoading);
  }

}

export default PlaylistVideo;
