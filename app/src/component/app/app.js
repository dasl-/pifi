import React from 'react';
import { CSSTransition } from 'react-transition-group';
import api from 'api';

import Content from './content';

import SearchBar from 'component/search/search_bar';
import AddedToPlaylistAlert from 'component/alert/added_to_playlist';

import PlaylistVideo from 'dataobj/playlist_video';
import SearchResultVideo from 'dataobj/search_result_video';

import './app.css';

class App extends React.Component {

  static QUEUE_POLL_INTERVAL_MS = 1000;

  constructor(props) {
    super(props);

    this.apiClient = new api();

    var stored_results = [];
    try {
      stored_results = JSON.parse(localStorage.getItem("latest_results") || "[]");
    } catch (e) {
      stored_results = [];
    }

    this.state = {
      show_intro: props.is_new_session,
      show_search: !props.is_new_session,
      search_loading: false,
      search_term: props.is_new_session ? '' : (localStorage.getItem("last_search") || ""),
      search_results: SearchResultVideo.fromArray(stored_results),
      playlist_current_video: null,
      playlist_videos: [],
      color_mode: 'color',
      last_queued_videos: [],
      last_queued_video_color_modes: [],
      vol_pct: undefined,
      is_screensaver_enabled: true
    };

    /* intro transition */
    this.setShowIntro = this.setShowIntro.bind(this);
    this.setShowSearch = this.setShowSearch.bind(this);

    /* search callbacks */
    this.setSearchTerm = this.setSearchTerm.bind(this);
    this.search = this.search.bind(this);

    /* search result callbacks */
    this.queueVideo = this.queueVideo.bind(this);

    /* playlist callbacks */
    this.nextVideo = this.nextVideo.bind(this);
    this.clearQueue = this.clearQueue.bind(this);
    this.removeVideo = this.removeVideo.bind(this);
    this.setVolPct = this.setVolPct.bind(this);

    // https://github.com/mozilla-mobile/firefox-ios/issues/5772#issuecomment-573380173
    if (window.__firefox__) {
        window.__firefox__.NightMode.setEnabled(false);
    }
  }

  componentDidMount() {
    this.getPlaylistQueue();
  }

  render() {
    return (
      <div className='h-100 bg-primary bg-background'>
        {this.state.show_intro &&
          <div>
            <section className="bg-primary page-section vertical-center">
              <div className="splash">
                  <SearchBar
                    loading={this.state.search_loading}
                    search_term={this.state.search_term}
                    onSearchTermChange={this.setSearchTerm}
                    onSubmit={this.search}
                  />
              </div>
            </section>
          </div>
        }

        <CSSTransition
          in={this.state.show_search}
          timeout={300}
          classNames="intro"
          onEnter={() => this.setShowIntro(false)}
          >
          <div className={"container-fluid p-0 app-body h-100 " + ((this.state.show_search) ? '' : 'd-none')}>
            <Content
              playlist_loading={this.state.playlist_loading}
              search_loading={this.state.search_loading}
              search_term={this.state.search_term}
              search_results={this.state.search_results}
              playlist_current_video={this.state.playlist_current_video}
              playlist_videos={this.state.playlist_videos}
              color_mode={this.state.color_mode}

              setSearchTerm={this.setSearchTerm}
              search={this.search}
              queueVideo={this.queueVideo}
              nextVideo={this.nextVideo}
              clearQueue={this.clearQueue}
              removeVideo={this.removeVideo}
              setVolPct={this.setVolPct}
              vol_pct={this.state.vol_pct}
              is_screensaver_enabled={this.state.is_screensaver_enabled}
            />
          </div>
        </CSSTransition>

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

  /* transitions */
  setShowIntro(val) {
    this.setState({'show_intro':val});
  }
  setShowSearch(val) {
    this.setState({'show_search':val});
  }

  /* search callbacks */
  setSearchTerm(val) {
    this.setState({'search_term':val});
  }
  search() {
    this.setState({'search_loading':true});
    localStorage.setItem("last_search", this.state.search_term);

    this.apiClient.searchYoutube(this.state.search_term)
      .then((data) => {
        if (!data) {
          return;
        }

        localStorage.setItem("latest_results", JSON.stringify(data));
        this.setState({
          search_results: SearchResultVideo.fromArray(data),
          search_loading: false,
          show_search: true
        });
      });
  }

  /* search result callbacks */
  queueVideo(video) {
    this.cancelQueuePoll();
    this.setState({'playlist_loading':true});

    var color_mode = this.state.color_mode;
    return this.apiClient
      .enqueueVideo(video, color_mode)
      .then((data) => {
        if (data.success) {
          this.setState({
            last_queued_videos: [...this.state.last_queued_videos, video],
            last_queued_video_color_modes: [...this.state.last_queued_video_color_modes, color_mode],
            playlist_loading: false
          });
        }
      })
      .finally(() => this.getPlaylistQueue())
  }

  /* playlist callbacks */
  nextVideo() {
    if (this.state.playlist_current_video) {
      this.cancelQueuePoll();

      var current_video_id = this.state.playlist_current_video.playlist_video_id;

      return this.apiClient
        .nextVideo(current_video_id)
        .finally(() => {
          // need to do this on a timeout because the server isnt so great about
          // the currently playing video immediately after skipping
          setTimeout(() => {this.getPlaylistQueue()}, App.QUEUE_POLL_INTERVAL_MS)
        })
    }
  }
  clearQueue() {
    this.cancelQueuePoll();

    return this.apiClient
      .clearQueue()
      .finally(() => this.getPlaylistQueue())
  }
  removeVideo(video) {
    this.cancelQueuePoll();

    return this.apiClient
      .removeVideo(video)
      .finally(() => this.getPlaylistQueue())
  }
  setVolPct(vol_pct) {
    return this.apiClient.setVolPct(vol_pct)
  }

  cancelQueuePoll() {
    clearTimeout(this.queue_timeout);
  }
  getPlaylistQueue() {
    if (this.state.playlist_loading) {
      this.cancelQueuePoll();
      this.queue_timeout = setTimeout(this.getPlaylistQueue.bind(this), App.QUEUE_POLL_INTERVAL_MS);
      return;
    }

    this.setState({'playlist_loading':true});

    return this.apiClient
      .getQueue()
      .then((data) => {
        if (data.success) {
          var playlist_videos = PlaylistVideo.fromArray(data.queue);
          var vol_pct = +(data.vol_pct.toFixed(0));
          var playlist_current_video = this.state.playlist_current_video;
          var current_video = playlist_videos.find(function(video) {
            return video.status === 'STATUS_PLAYING';
          });

          if (current_video) {
            if (
              !playlist_current_video ||
              (playlist_current_video && playlist_current_video.playlist_video_id !== current_video.playlist_video_id)
            ) {
              playlist_current_video = current_video;
            }
          } else {
            playlist_current_video = null;
          }

          if (playlist_current_video) {
            // remove the currently playing video from the queue list
            playlist_videos = playlist_videos.filter((video) => {
              return video.playlist_video_id !== playlist_current_video.playlist_video_id;
            });
          }

          this.setState({
            playlist_current_video: playlist_current_video,
            playlist_videos: playlist_videos,
            vol_pct: vol_pct,
            is_screensaver_enabled: data.is_screensaver_enabled
          });
        }

        this.setState({ playlist_loading: false });
      })
      .finally((data) => {
        this.queue_timeout = setTimeout(this.getPlaylistQueue.bind(this), App.QUEUE_POLL_INTERVAL_MS);
      });
  }

}

export default App;