import React from 'react';

import { CSSTransition } from 'react-transition-group';

import './playlist.css';

import LoadWithVideo from 'component/util/load_with_video';
import CurrentlyPlayingRight from 'component/currently_playing/currently_playing_right';
import PlaylistVideo from './playlist_video';

class Playlist extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      loading: props.loading,
      initial_fadein: true
    };

    this.setInitialFadeIn = this.setInitialFadeIn.bind(this);
  }

  componentWillReceiveProps(nextProps) {
    if (this.state.initial_fadein && !nextProps.loading) {
      // the playlist has finished its initial load, trigger the fade in animation
      setTimeout(() => this.setInitialFadeIn(false), 500);
    }
  }

  setInitialFadeIn(val) {
    this.setState({'initial_fadein':val});
  }

  render() {
    return (
      <section className="col-5 col-lg-4 p-0 m-0 bg-dark text-light">

        {this.state.initial_fadein &&
          <section className="page-section h-100"></section>
        }

        <CSSTransition
          in={!this.state.initial_fadein}
          timeout={0}
          classNames="playlist"
          onEnter={() => this.setInitialFadeIn(false)}
          >

          <div className="playlist">
            <div className="p-2 px-4">
              <LoadWithVideo video={this.props.current_video}>
                <CurrentlyPlayingRight
                  nextVideo={this.props.nextVideo}
                  clearQueue={this.props.clearQueue}
                />
              </LoadWithVideo>

              <div className="play-queue">
                {
                  this.props.videos.map((video, index) => {
                    return (
                      <LoadWithVideo key={video.video_id} video={video}>
                        <PlaylistVideo
                          removeVideo={this.props.removeVideo}
                        />
                      </LoadWithVideo>
                    );
                  })
                }
              </div>
            </div>
          </div>
          </CSSTransition>
      </section>
    );
  }
}

export default Playlist;