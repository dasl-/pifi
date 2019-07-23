import utils from 'utils';

class SearchResultVideo {
  fromProps(props, index) {
    return {
      index: index,
      video_id: props.id,
      thumbnail_img_src: props.snippet.thumbnails.high.url,
      video_url: 'https://www.youtube.com/watch?v=' + props.id,
      description: props.snippet.description.split(' ').slice(0,30).join(' ') + "...",
      title: props.snippet.title,
      channel: props.snippet.channelTitle,
      published: utils.timeDifference(Date.now(), Date.parse(props.snippet.publishedAt)),
      view_count: utils.abbreviateNumber(props.statistics.viewCount),
      duration: utils.convertISO8601ToSeconds(props.contentDetails.duration)
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