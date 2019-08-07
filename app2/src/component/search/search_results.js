import React from 'react';

import LoadWithVideo from 'component/util/load_with_video';
import SearchResult from './search_result';

class SearchResults extends React.Component {
  render() {
    return (
      <div className="px-0 m-0 search-results">
        {this.props.search_results.map((video, index) => {
          return (
            <LoadWithVideo
              key={video.video_id}
              video={video}>

              <SearchResult queueVideo={this.props.queueVideo} />

            </LoadWithVideo>
          );
        })}
      </div>
    );
  }
}

export default SearchResults;