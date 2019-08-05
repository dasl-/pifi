import React from 'react';

import LoadWithVideo from 'component/util/load_with_video';
import SwipeableList from 'component/lib/SwipeableList/SwipeableList';
import SwipeableListItem from 'component/lib/SwipeableList/SwipeableListItem';
import CurrentlyPlaying from 'component/currently_playing/currently_playing_right';

class PlaylistExpanded extends React.Component {
  constructor(props) {
    super(props);

    this.onSwipeVideo = this.onSwipeVideo.bind(this);
  }

  render() {
    return (
      <div className='container px-2'>
        <div className='col-12'>
          <section className=' playlist-expanded bg-dark text-light p-0 px-2 m-0'>
            <div className="w-100 text-center py-2 mb-2 border-bottom border-secondary" onClick={this.props.contractFooterPlaylist}>
              <span className="glyphicon glyphicon-chevron-down" aria-hidden="true" />
            </div>

            <LoadWithVideo video={this.props.current_video}>
              <CurrentlyPlaying
                nextVideo={this.props.nextVideo}
                clearQueue={this.props.clearQueue}
              />
            </LoadWithVideo>


            <div className="play-queue">
              <SwipeableList background={<span></span>}>
              {
                this.props.videos.map((video, index) => {
                  return (
                    <SwipeableListItem key={video.video_id} onSwipe={() => this.onSwipeVideo(video)}>
                      <div className='container py-2 px-0 mt-2 border-top border-secondary playlist-video'>
                        <div className='row mr-0'>
                          <div className='col-4 px-2 pl-3 small-vertical-center'>
                            <img
                              className='img-fluid'
                              src={video.thumbnail}
                              alt={video.title}
                            />
                          </div>
                          <div className='col-8 px-2'>
                            <div className='small'>{video.title}</div>
                            <div className='small badge badge-secondary'>{video.duration}</div>
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
    console.log(video);
    this.props.removeVideo(video);
  }
}

export default PlaylistExpanded;