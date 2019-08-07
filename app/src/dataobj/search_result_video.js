import utils from 'utils';

class SearchResultVideo {
  fromProps(props, index) {
    return {
      // Shared Data
      video_id: props.id,
      thumbnail: props.snippet.thumbnails.medium.url,
      video_url: 'https://www.youtube.com/watch?v=' + props.id,
      title: props.snippet.title,
      duration: utils.convertISO8601ToSeconds(props.contentDetails.duration),

      // Unique Data
      index: index,
      description: props.snippet.description.split(' ').slice(0,30).join(' ') + "...",
      channel: props.snippet.channelTitle,
      published: utils.timeDifference(Date.now(), Date.parse(props.snippet.publishedAt)),
      view_count: utils.abbreviateNumber(props.statistics.viewCount),
    };
  }

  fromArray(video_props) {
    var videos = video_props.map((props, i) => {
      return SearchResultVideo.prototype.fromProps(props, i);
    });

    return videos.sort((a, b) => {return a.index > b.index})
  }
}

export default SearchResultVideo.prototype;