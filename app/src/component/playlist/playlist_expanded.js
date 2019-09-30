import React from 'react';

import LoadWithVideo from 'component/util/load_with_video';
import SwipeableList from 'component/lib/SwipeableList/SwipeableList';
import SwipeableListItem from 'component/lib/SwipeableList/SwipeableListItem';
import CurrentlyPlaying from 'component/currently_playing/currently_playing_video';

class PlaylistExpanded extends React.Component {
  constructor(props) {
    super(props);

    this.onSwipeVideo = this.onSwipeVideo.bind(this);
    this.handleSkip = this.handleSkip.bind(this);
  }

  render() {
    return (
      <div className='container px-2'>
        <div className='col-12'>
          <section className=' playlist-expanded bg-dark text-light p-0 px-2 m-0'>
            <div className="w-100 text-center py-3 mb-0" onClick={this.props.contractFooterPlaylist}>
              <span className="glyphicon glyphicon-chevron-down bg-dark-text" aria-hidden="true" />
            </div>

            <LoadWithVideo video={this.props.current_video}>
              <CurrentlyPlaying
                nextVideo={this.props.nextVideo}
                setVolPct={this.props.setVolPct}
                vol_pct={this.props.vol_pct}
                clearQueue={this.props.clearQueue}
              />
            </LoadWithVideo>

            <div className="play-queue">
              { (this.props.videos.length === 0) &&
                <div className='container pt-2 px-0 mt-2 playlist-video'>
                  <div className="pink-top">
                    <div className="py-3 text-center">
                      &lt;Nothing&gt;
                    </div>
                  </div>
                </div>
              }

              <SwipeableList background={<span></span>}>
              {
                this.props.videos.map((video, index) => {
                  return (
                    <SwipeableListItem key={video.video_id} onSwipe={() => this.onSwipeVideo(video)}>
                      <div className='container pt-2 px-0 mt-2 playlist-video'>
                        <div className="pink-top">
                          <div className='row mr-0'>

                            <div className='col-7 px-2 pl-3 small-vertical-center'>
                              <img
                                className='img-fluid'
                                src={video.thumbnail}
                                alt={video.title}
                              />

                              <span className="duration badge badge-dark position-absolute mr-3 mb-1">{video.duration}</span>
                            </div>

                            <div className='col-5 px-2'>
                              <div className='small video-title-no-shadow'>{video.title}</div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </SwipeableListItem>
                  );
                })
              }
              </SwipeableList>
            </div>
          </section>
        </div>
      </div>
    );
  }

  onSwipeVideo(video) {
    this.props.removeVideo(video);
  }

  handleSkip(e) {
    e.preventDefault();
    e.stopPropagation();
    this.props.nextVideo();
  }
}

export default PlaylistExpanded;