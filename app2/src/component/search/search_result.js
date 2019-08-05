import React from 'react';

class SearchResult extends React.Component {
  constructor(props) {
    super(props);

    this.onQueueVideo = this.onQueueVideo.bind(this);
  }

  render() {
    var video = this.props.video;
    var row_class = 'search-result row px-0 m-3 ' + (this.props.loading ? 'loading' : '')

    return (
      <div key={video.video_id} className={row_class} onClick={(e) => this.onQueueVideo(e, video)}>
        <div className="col-sm-4 col-md-12 col-lg-4 small-vertical-center text-center m-0 p-3 p-sm-0">
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

        <div className="col-sm-8 col-md-12 col-lg-8 py-md-2">
          <h6 className="title">{video.title}</h6>
          <div className="small pb-1">
          {video.channel} | {video.view_count} views | {video.published} ago
          </div>
          <div className="small">{video.description}</div>
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