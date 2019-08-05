import React from 'react';

class CurrentlyPlayingRight extends React.Component {
  constructor(props) {
    super(props);

    this.handleSkip = this.handleSkip.bind(this);
  }

  render() {
    var row_class = 'now-playing ' + (this.props.loading ? 'loading' : '')

    return (
      <div className={row_class}>
        <div className='navbar-brand container p-0 m-0'>
          Now Playing
          {(this.props.video) &&
            <a href='#' className='text-light float-right' onClick={this.handleSkip}>
              <span className='glyphicon glyphicon-forward' aria-hidden='true' />
            </a>
          }
        </div>

        <div className='bg-dark position-relative'>
          <div className='loading-cover'><div className='dot-pulse'></div></div>
          <img
            src={(this.props.video) ? this.props.video.thumbnail : 'img/playlist-placeholder.png'}
            className='img-fluid video-thumbnail w-100'
            alt={(this.props.video) ? this.props.video.title : ''}
            onLoad={this.props.setImageLoaded}
          />
          {(this.props.video) &&
            <span className='duration badge badge-dark position-absolute mr-1 mb-1'>{this.props.video.duration}</span>
          }
        </div>

        <div className='text-large text-center py-2'>
          {(this.props.video)
            ? this.props.video.title
            : <span>&lt;Nothing&gt;</span>
          }
        </div>
      </div>
    );
  }

  handleSkip(e) {
    e.preventDefault();
    this.props.setLoading();
    this.props.nextVideo();
  }
}

export default CurrentlyPlayingRight;