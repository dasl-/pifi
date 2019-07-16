class QueuedVideo {
  constructor(props) {
      this.id = props.id;
      this.create_date = props.create_date;
      this.is_color = props.is_color;
      this.is_current = props.is_current;
      this.status = props.status;
      this.thumbnail = props.thumbnail;
      this.title = props.title;
      this.url = props.url;
  }

  fromArray(video_props) {
    return video_props.map(function(props) {
      return new QueuedVideo(props);
    });
  }
}

export default QueuedVideo;