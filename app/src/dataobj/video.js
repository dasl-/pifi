import utils from 'utils';

class Video {
  constructor(props) {
    this.video_id = props.id;
    this.thumbnail_img_src = props.snippet.thumbnails.high.url;
    this.video_url = 'https://www.youtube.com/watch?v=' + props.id;
    this.description = props.snippet.description.split(' ').slice(0,30).join(' ') + "...";
    this.title = props.snippet.title;
    this.channel = props.snippet.channelTitle;
    this.published = utils.timeDifference(Date.now(), Date.parse(props.snippet.publishedAt));
    this.view_count = utils.abbreviateNumber(props.statistics.viewCount);
    this.duration = utils.convertISO8601ToSeconds(props.contentDetails.duration);
  }

  fromArray(video_props) {
    return video_props.map(function(props) {
      return new Video(props);
    });
  }
}

export default Video;