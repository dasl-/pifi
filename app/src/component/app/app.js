import React from 'react';

import api from 'api';
import Search from 'component/search/search';
import AddedToPlaylistAlert from 'component/alert/added_to_playlist';
import Playlist from 'component/playlist/playlist';

import './app.css';

class App extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      playlist_expanded: false,
      color_mode: 'color',
      last_queued_videos: [],
      last_queued_video_color_modes: []
    };
    this.apiClient = new api();

    this.toggleColorMode = this.toggleColorMode.bind(this);
    this.enqueueVideo = this.enqueueVideo.bind(this);
    this.togglePlaylist = this.togglePlaylist.bind(this);
    this.collapsePlaylist = this.collapsePlaylist.bind(this);
  }

  render() {
    var lock_class = "unlocked";
    if (this.state.playlist_expanded) {
      lock_class = "locked";
    }

    return (
      <div className={lock_class + " container color-mode-" + this.state.color_mode}>
        <div className="blur-on-lock">
          {
            this.state.playlist_expanded &&
            (<div className="background-mask" onClick={this.collapsePlaylist}></div>)
          }
          <Search
            toggleColorMode = {this.toggleColorMode}
            enqueueVideo = {this.enqueueVideo}
          />
        </div>

        <Playlist
          expanded = {this.state.playlist_expanded}
          togglePlaylist = {this.togglePlaylist}
        />

        {this.state.last_queued_videos.map(function(video, index) {
          return <AddedToPlaylistAlert
            key = {index}
            video = {video}
            color_mode = {this.state.last_queued_video_color_modes[index]}
            show = {index === this.state.last_queued_videos.length - 1} />
        }.bind(this))}
      </div>
    );
  }

  togglePlaylist(e) {
    this.setState({playlist_expanded: !this.state.playlist_expanded});
  }

  collapsePlaylist(e) {
    if (this.state.playlist_expanded) {
      this.setState({playlist_expanded: false});
    }
  }

  toggleColorMode(e) {
    if (this.state.color_mode === 'color') {
      this.setState({color_mode: 'bw'});
    } else if (this.state.color_mode === 'bw') {
      this.setState({color_mode: 'red'});
    } else if (this.state.color_mode === 'red') {
      this.setState({color_mode: 'green'});
    } else if (this.state.color_mode === 'green') {
      this.setState({color_mode: 'blue'});
    } else if (this.state.color_mode === 'blue') {
      this.setState({color_mode: 'color'});
    } else {
      this.setState({color_mode: 'color'});
    }
  }

  enqueueVideo(video) {
    return this.apiClient.enqueueVideo(video, this.state.color_mode)
      .then((data) => {
        if (data.success) {
          this.setState({
            last_queued_videos:[...this.state.last_queued_videos, video],
            last_queued_video_color_modes:[...this.state.last_queued_video_color_modes, this.state.color_mode]
          });
        }
      });
  }
}

export default App;