import React from 'react';
import { CSSTransition } from 'react-transition-group';

import Header from './header';
import LoadWithVideo from 'component/util/load_with_video';
import Search from 'component/search/search';
import CurrentlyPlayingFooter from 'component/currently_playing/currently_playing_footer';
import Playlist from 'component/playlist/playlist';
import PlaylistExpanded from 'component/playlist/playlist_expanded';
import PlaylistMask from 'component/playlist/playlist_mask';

import './content.css';

class Content extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      playlist_expanded: false,
      playlist_fully_expanded: false,
      playlist_fully_contracted: true,
      playlist_loading: false,
    };

    /* playlist callbacks */
    this.expandFooterPlaylist = this.expandFooterPlaylist.bind(this);
    this.contractFooterPlaylist = this.contractFooterPlaylist.bind(this);
    this.setPlaylistFullyExpanded = this.setPlaylistFullyExpanded.bind(this);
    this.setPlaylistFullyContracted = this.setPlaylistFullyContracted.bind(this);
  }

  render() {
    return (
      <div className="h-100">
        <PlaylistMask
          contractFooterPlaylist={this.contractFooterPlaylist}
          playlist_expanded={this.state.playlist_expanded}
          playlist_fully_expanded={this.state.playlist_fully_expanded}
          playlist_fully_contracted={this.state.playlist_fully_contracted}
        />

        <div className={this.state.playlist_fully_expanded ? 'lock content' : 'content'}>
          <Header />
          <div className='h-100'>
            <div className="d-block d-md-none h-100">
              {/* Phone View */}
              <Search
                loading={this.props.search_loading}
                search_term={this.props.search_term}
                search_results={this.props.search_results}
                onSearchTermChange={this.props.setSearchTerm}
                onSubmit={this.props.search}
                queueVideo={this.props.queueVideo}
                is_screensaver_enabled={this.props.is_screensaver_enabled}
              />

              <LoadWithVideo video={this.props.playlist_current_video}>
                <CurrentlyPlayingFooter
                  onClick={this.expandFooterPlaylist}
                  nextVideo={this.props.nextVideo}
                  clearQueue={this.props.clearQueue}
                />
              </LoadWithVideo>
            </div>

            <div className="d-none d-md-block h-100">
              {/* Desktop View */}
              <div className="row p-0 m-0 h-100">
                <div className="col-7 col-lg-8 p-0 m-0 bg-light pl-3">
                  <Search
                    loading={this.props.search_loading}
                    search_term={this.props.search_term}
                    search_results={this.props.search_results}
                    onSearchTermChange={this.props.setSearchTerm}
                    onSubmit={this.props.search}
                    queueVideo={this.props.queueVideo}
                    is_screensaver_enabled={this.props.is_screensaver_enabled}
                  />
                </div>

                <Playlist
                  loading={!this.props.playlist_loading}
                  current_video={this.props.playlist_current_video}
                  videos={this.props.playlist_videos}
                  nextVideo={this.props.nextVideo}
                  clearQueue={this.props.clearQueue}
                  removeVideo={this.props.removeVideo}
                  setVolPct={this.props.setVolPct}
                  vol_pct={this.props.vol_pct}
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
          onExited={() => this.setPlaylistFullyContracted(true)}
          >

          <div className="playlist-expander w-100 bg-primary">
            <div className="d-block d-md-none h-100 w-100 bg-primary">
              <PlaylistExpanded
                current_video={this.props.playlist_current_video}
                videos={this.props.playlist_videos}
                nextVideo={this.props.nextVideo}
                clearQueue={this.props.clearQueue}
                removeVideo={this.props.removeVideo}
                contractFooterPlaylist={this.contractFooterPlaylist}
                setVolPct={this.props.setVolPct}
                vol_pct={this.props.vol_pct}
              />
            </div>
          </div>

        </CSSTransition>
      </div>
    );
  }

  /* transitions */
  setPlaylistFullyExpanded(val) {
    this.setState({'playlist_fully_expanded':val});
  }
  setPlaylistFullyContracted(val) {
    this.setState({'playlist_fully_contracted':val});
  }
  expandFooterPlaylist() {
    this.setState({
      'playlist_expanded': true,
      'playlist_fully_contracted': false
    });
  }
  contractFooterPlaylist() {
    this.setState({'playlist_expanded':false});
  }
}

export default Content;