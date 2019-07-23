class PlaylistVideo {
  fromProps(props) {
    return {
      playlist_video_id: props.playlist_video_id,
      create_date: props.create_date,
      color_mode: props.color_mode,
      status: props.status,
      thumbnail: props.thumbnail,
      title: props.title,
      url: props.url,
      is_favorite: props.is_favorite
    };
  }

  fromArray(video_props) {
    var videos = video_props.map((props) => {
      return PlaylistVideo.prototype.fromProps(props);
    });

    return videos.sort((a, b) => {return a.playlist_video_id > b.playlist_video_id})
  }
}

export default PlaylistVideo.prototype;