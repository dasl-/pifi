import React from 'react';

class CurrentlyPlayingRight extends React.Component {
  constructor(props) {
    super(props);

    this.handleSkip = this.handleSkip.bind(this);
  }

  render() {
    var row_class = 'now-playing ' + (this.props.loading ? 'loading' : '')

    return (
      <div>
        <div className={row_class}>
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

        <div className='container pt-2 px-0 mt-2'>
          <div className='row mr-0'>
            <div className='col-8 px-2 pl-3 small-vertical-center'>
                Up Next
            </div>
            <div className='col-3 px-0'>

            </div>
            <div className='col-1 px-0'>
                {(this.props.video) &&
                  <a href='#' className='text-light skip-icon' onClick={this.handleSkip}>
                    <span className='glyphicon glyphicon-forward bg-light-text' aria-hidden='true' />
                  </a>
                }
            </div>
          </div>
        </div>
      </div>
    );
  }

  handleSkip(e) {
    e.preventDefault();
    e.stopPropagation();
    this.props.setLoading();
    this.props.nextVideo();
  }
}

export default CurrentlyPlayingRight;