class PlaylistVideo {
  fromProps(props) {
    return {
      // Shared Data
      video_id: props.playlist_video_id,
      thumbnail: props.thumbnail,
      playlist_video_id: props.playlist_video_id,
      video_url: props.url,
      title: props.title,
      duration: props.duration,

      // Unique Data
      create_date: props.create_date,
      color_mode: props.color_mode,
      status: props.status,

      priority: props.priority,
    };
  }

  fromArray(video_props) {
    var videos = video_props.map((props) => {
      return PlaylistVideo.prototype.fromProps(props);
    });

    return videos;
  }
}

export default PlaylistVideo.prototype;