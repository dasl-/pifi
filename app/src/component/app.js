import React from 'react';

import api from 'api';
import Search from 'component/search';
import SuccessAlert from 'component/success_alert';
import Playlist from 'component/playlist';

class App extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      color_mode: 'color',
      last_queued_videos: []
    };
    this.apiClient = new api();

    this.toggleColorMode = this.toggleColorMode.bind(this);
    this.queueVideo = this.queueVideo.bind(this);
  }

  render() {
    return (
      <div className={"container " + this.state.color_mode}>
        <Search
          toggleColorMode = {this.toggleColorMode}
          queueVideo = {this.queueVideo}
        />

        <Playlist />

        {this.state.last_queued_videos.map(function(video, index) {
          return <SuccessAlert
            key = {index}
            video = {video}
            show = {index === this.state.last_queued_videos.length - 1} />
        }.bind(this))}
      </div>
    );
  }

  toggleColorMode(e) {
    if (this.state.color_mode === 'color') {
      this.setState({color_mode: 'black-and-white'});
    } else {
      this.setState({color_mode: 'color'});
    }
  }

  queueVideo(video) {
    return this.apiClient.queueVideo(video, true)
      .then((data) => {
        if (data.success) {
          this.setState({
            last_queued_videos:[...this.state.last_queued_videos, video]
          });
        }
      });
  }
}

export default App;