import React from 'react';

class SearchResult extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      loading: false
    };

    this.handleSearchResultClick = this.handleSearchResultClick.bind(this);
  }

  render() {
    var row_class = 'row search-result ' + (this.state.loading ? 'loading' : '')

    return (
      <div key={this.props.video.video_id} className={row_class} onClick={this.handleSearchResultClick} >
        <div className='col-sm-4 search-result-image'>
          <div className='loading-cover'><div className='dot-pulse'></div></div>
          <img
            src={this.props.video.thumbnail_img_src}
            className='img-responsive video-thumbnail'
            alt={this.props.video.title}
            width='100%' />
          <span className='duration'>{this.props.video.duration}</span>
        </div>
        <div className='col-sm-8 video-data'>
          <div className='title-padding hidden-sm hidden-md hidden-lg'></div>
          <h4 className='title'>{this.props.video.title}</h4>
          <div><h6>{this.props.video.channel} | {this.props.video.view_count} views | {this.props.video.published} ago</h6></div>
          <p className='video-description'>{this.props.video.description}</p>
        </div>
      </div>
    );
  }

  handleSearchResultClick(e) {
    e.preventDefault();

    this.setState(state => ({
      loading: true
    }));

    this.props.enqueueVideo(this.props.video)
      .then((data) => {
        this.setState(state => ({
          loading: false
        }));
      });
  }
}

export default SearchResult;