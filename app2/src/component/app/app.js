import React from 'react';
import { CSSTransition } from 'react-transition-group';
import api from 'api';

import Header from './header';
import LoadWithVideo from 'component/util/load_with_video';
import Search from 'component/search/search';
import SearchBar from 'component/search/search_bar';
import CurrentlyPlayingFooter from 'component/currently_playing/currently_playing_footer';
import Playlist from 'component/playlist/playlist';
import PlaylistExpanded from 'component/playlist/playlist_expanded';
import AddedToPlaylistAlert from 'component/alert/added_to_playlist';

import PlaylistVideo from 'dataobj/playlist_video';
import SearchResultVideo from 'dataobj/search_result_video';

import './app.css';

class App extends React.Component {
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
      /* intro transition */
      show_intro: props.is_new_session,
      show_search: !props.is_new_session,

      /* search */
      search_loading: false,
      search_term: localStorage.getItem("last_search") || "",
      search_results: SearchResultVideo.fromArray(stored_results),

      /* playlist */
      playlist_expanded: false,
      playlist_fully_expanded: false,
      playlist_loading: false,
      playlist_current_video: null,
      playlist_videos: [],

      /* search results */
      color_mode: 'color',

      /* alerts */
      last_queued_videos: [],
      last_queued_video_color_modes: []
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
    this.expandFooterPlaylist = this.expandFooterPlaylist.bind(this);
    this.contractFooterPlaylist = this.contractFooterPlaylist.bind(this);
    this.setPlaylistFullyExpanded = this.setPlaylistFullyExpanded.bind(this);
  }

  componentDidMount() {
    this.getPlaylistQueue();
  }

  render() {
    return (
      <div className='h-100'>
        {!this.state.playlist_expanded &&
          <Header />
        }

        {this.state.show_intro &&
          <section className="bg-primary page-section vertical-center">
            <SearchBar
              loading={this.state.search_loading}
              search_term={this.state.search_term}
              onSearchTermChange={this.setSearchTerm}
              onSubmit={this.search}
            />
          </section>
        }

        <CSSTransition
          in={this.state.show_search}
          timeout={300}
          classNames="intro"
          onEnter={() => this.setShowIntro(false)}
          >
            <div className="container-fluid p-0 app-body h-100">
              {this.state.show_search &&
                <div>
                  {this.state.playlist_fully_expanded &&
                    <div className="playlist-mask"></div>
                  }

                  <div className={this.state.playlist_fully_expanded ? 'lock content' : 'content'}>
                    <div className='h-100'>
                      <div className="d-block d-md-none">
                        <Search
                          loading={this.state.search_loading}
                          search_term={this.state.search_term}
                          search_results={this.state.search_results}
                          onSearchTermChange={this.setSearchTerm}
                          onSubmit={this.search}
                          queueVideo={this.queueVideo}
                        />

                        <LoadWithVideo video={this.state.playlist_current_video}>
                          <CurrentlyPlayingFooter
                            onClick={this.expandFooterPlaylist}
                            nextVideo={this.nextVideo}
                            clearQueue={this.clearQueue}
                          />
                        </LoadWithVideo>
                      </div>

                      <div className="d-none d-md-block">
                        <div className="row p-0 m-0">
                          <div className="col-7 col-lg-8 p-0 m-0 bg-light">
                            <Search
                              loading={this.state.search_loading}
                              search_term={this.state.search_term}
                              search_results={this.state.search_results}
                              onSearchTermChange={this.setSearchTerm}
                              onSubmit={this.search}
                              queueVideo={this.queueVideo}
                            />
                          </div>

                          <Playlist
                            loading={!this.state.playlist_loading}
                            current_video={this.state.playlist_current_video}
                            videos={this.state.playlist_videos}
                            nextVideo={this.nextVideo}
                            clearQueue={this.clearQueue}
                            removeVideo={this.removeVideo}
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  <CSSTransition
                    in={this.state.playlist_expanded}
                    timeout={300}
                    classNames="playlist"
                    onEnter={() => this.setPlaylistFullyExpanded(false)}
                    onEntered={() => this.setPlaylistFullyExpanded(true)}
                    onExit={() => this.setPlaylistFullyExpanded(false)}
                    >

                    <div className="playlist-expander w-100 bg-dark">
                      <div className="d-block d-md-none h-100 w-100 bg-dark">
                        <PlaylistExpanded
                          loading={!this.state.playlist_loading}
                          current_video={this.state.playlist_current_video}
                          videos={this.state.playlist_videos}
                          nextVideo={this.nextVideo}
                          clearQueue={this.clearQueue}
                          removeVideo={this.removeVideo}
                          contractFooterPlaylist={this.contractFooterPlaylist}
                        />
                      </div>
                    </div>

                  </CSSTransition>
                </div>
              }
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
  setPlaylistFullyExpanded(val) {
    this.setState({'playlist_fully_expanded':val});
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
      .finally(() => this.getPlaylistQueue(false))
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
          setTimeout(() => {this.getPlaylistQueue(false)}, 1000)
        })
    }
  }
  clearQueue() {
    this.cancelQueuePoll();

    return this.apiClient
      .clearQueue()
      .finally(() => this.getPlaylistQueue(false))
  }
  removeVideo(video) {
    this.cancelQueuePoll();

    return this.apiClient
      .removeVideo(video)
      .finally(() => this.getPlaylistQueue(false))
  }
  expandFooterPlaylist() {
    this.setState({'playlist_expanded':true});
  }
  contractFooterPlaylist() {
    this.setState({'playlist_expanded':false});
  }
  cancelQueuePoll() {
    clearTimeout(this.queue_timeout);
  }
  getPlaylistQueue(poll = true) {
    if (this.state.playlist_loading) {
      this.cancelQueuePoll();
      this.queue_timeout = setTimeout(this.getPlaylistQueue.bind(this), 1000);
      return;
    }

    this.setState({'playlist_loading':true});

    return this.apiClient
      .getQueue()
      .then((data) => {
        if (data.success) {
          var playlist_videos = PlaylistVideo.fromArray(data.queue);
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
            playlist_videos: playlist_videos
          });
        }

        this.setState({ playlist_loading: false });
      })
      .finally((data) => {
        if (poll) {
          this.queue_timeout = setTimeout(this.getPlaylistQueue.bind(this), 1000);
        }
      });
  }

}

export default App;