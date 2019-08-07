import React from 'react';

class SearchResult extends React.Component {
  constructor(props) {
    super(props);

    this.onQueueVideo = this.onQueueVideo.bind(this);
  }

  render() {
    var video = this.props.video;
    var row_class = 'search-result row px-0 m-0 ' + (this.props.loading ? 'loading' : '')

    return (
      <div key={video.video_id} className={row_class} onClick={(e) => this.onQueueVideo(e, video)}>
        <div className="col-7 col-sm-5 col-md-4 small-vertical-center text-center m-0 p-2">
          <div className="position-relative w-100 bg-dark">
            <img
              src={video.thumbnail}
              className="img-responsive video-thumbnail w-100"
              alt={video.title}
              onLoad={this.props.setImageLoaded}
            />

            <span className="duration badge badge-dark position-absolute mr-1 mb-1">{video.duration}</span>
            <div className='loading-cover'><div className='dot-pulse'></div></div>
          </div>
        </div>

        <div className="col-5 col-sm-7 col-md-8 p-2 m-0">
          <h6 className="video-title">{video.title}</h6>
          <div className="small pb-1 video-details">
          {video.channel} | {video.view_count} views | {video.published} ago
          </div>
          <div className="small video-description d-none d-sm-block">{video.description}</div>
        </div>
      </div>
    );
  }

  onQueueVideo(e, video) {
    e.preventDefault();
    this.props.setLoading();

    this.props
      .queueVideo(video)
      .then(this.props.removeLoading);
  }
}

export default SearchResult;