import React from 'react';

class PlaylistItem extends React.Component {
  render() {
    var color_class = this.props.video.color_mode;
    var current_class = '';

    if (this.props.video.status === 'STATUS_PLAYING') {
      current_class = ' current';
    }

    return (
      <div className={"row playlist-video " + color_class + current_class}>
        <div className='col-xs-4 col-sm-4 playlist-video'>
          <div className='placeholder' style={{'backgroundImage': `url(${this.props.video.thumbnail})`}}>
          </div>
        </div>
        <div className='col-xs-7 col-sm-8 video-data'>
          <h5 className='title'>{this.props.video.title}</h5>
        </div>
      </div>
    );
  }
}

export default PlaylistItem;