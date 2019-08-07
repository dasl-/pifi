import React from 'react';

class CurrentlyPlayingFooter extends React.Component {
  constructor(props) {
    super(props);

    this.handleSkip = this.handleSkip.bind(this);
  }

  render() {
    var row_class = 'row ' + (this.props.loading ? 'loading' : '')

    return (
      <footer className='playlist-footer navbar bg-dark text-light fixed-bottom p-0 m-0' onClick={this.props.onClick}>
        <div className='container p-2 now-playing-footer'>
          <div className={row_class}>
            <div className='col-4 col-sm-3 col-md-2 small-vertical-center bg-dark position-relative'>
              <div className='loading-cover'><div className='dot-pulse'></div></div>
              <img
                src={(this.props.video) ? this.props.video.thumbnail : 'img/playlist-placeholder.png'}
                className='img-fluid video-thumbnail w-100'
                alt={(this.props.video) ? this.props.video.title : ''}
                onLoad={this.props.setImageLoaded}
              />
            </div>
            <div className='col-7 col-sm-8 pl-0 small-vertical-center'>
              <div className='small'>
                {(this.props.video)
                  ? this.props.video.title
                  : <span>&lt;Nothing&gt;</span>
                }
              </div>
            </div>
            <div className='col-1 pl-0 small-vertical-center'>
              {(this.props.video) &&
                <a href='#' className='text-light float-right' onClick={this.handleSkip}>
                  <span className='glyphicon glyphicon-forward bg-dark-text' aria-hidden='true' />
                </a>
              }
            </div>
          </div>
        </div>
      </footer>
    );
  }

  handleSkip(e) {
    e.preventDefault();
    e.stopPropagation();
    this.props.setLoading();
    this.props.nextVideo();
  }
}

export default CurrentlyPlayingFooter;