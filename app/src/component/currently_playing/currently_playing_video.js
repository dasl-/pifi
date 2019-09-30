import './currently_playing.css';
import App from '../app/app';

import 'rc-slider/assets/index.css';
import React from 'react';
import Slider from 'rc-slider';

class CurrentlyPlayingRight extends React.Component {
  constructor(props) {
    super(props);

    this.handleSkip = this.handleSkip.bind(this);
    this.state = {
      vol_pct: this.props.vol_pct,
      is_vol_locked: false,
      is_vol_lock_releasable: true,
      vol_lock_marked_releasable_time: 0
    };
  }

  render() {
    var row_class = 'now-playing ' + (this.props.loading ? 'loading' : '');
    return (
      <div>
        <div className={row_class}>
          <div className='bg-dark position-relative'>
            <div className='loading-cover'><div className='dot-pulse'></div></div>
            <img
              src={(this.props.video) ? this.props.video.thumbnail : 'img/playlist-placeholder.png'}
              className='img-fluid video-thumbnail w-100'
              alt={(this.props.video) ? this.props.video.title : ''}
              onLoad={this.props.setImageLoaded}
            />
            {(this.props.video) &&
              <span className='duration badge badge-dark position-absolute mr-1 mb-1'>{this.props.video.duration}</span>
            }
          </div>

          <div className='text-large text-center py-2'>
            {(this.props.video)
              ? this.props.video.title
              : <span>&lt;Nothing&gt;</span>
            }
          </div>
        </div>

        <div className='row'>
          <div className='col-1 p-0 text-right'><span className='glyphicon glyphicon-volume-down bg-light-text vol-icon' aria-hidden='true' /></div>
          <div className='col-10 volume-container'>
            <Slider
              className='volume'
              min={0}
              max={100}
              step={1}
              onBeforeChange={this.grabVolMutex}
              onChange={this.onVolChange}
              onAfterChange={this.markVolMutexReleasable}
              value={this.state.is_vol_locked ? this.state.vol_pct : this.props.vol_pct}
              trackStyle={{
                border: '1px solid #686E7B',
                backgroundColor: '#686E7B',
                height: 10
              }}
              railStyle={{
                border: '1px solid #686E7B',
                backgroundColor: 'transparent',
                height: 10
              }}
              handleStyle={{
                border: '1px solid #5cedf9',
                boxShadow: '0px 0px 3.5px #52c6f3, 0px 0px 0px #6acef5',
                height: 30,
                width: 30,
                marginLeft: -16,
                marginTop: -9,
                backgroundColor: '#2e3135',
              }}
            />
          </div>
          <div className='col-1 p-0'><span className='glyphicon glyphicon-volume-up bg-light-text vol-icon' aria-hidden='true' /></div>
        </div>

        <div className='container pt-2 px-0 mt-2'>
          <div className='row mr-0'>
            <div className='col-8 px-2 pl-3 small-vertical-center'>
                Up Next
            </div>
            <div className='col-3 px-0'>

            </div>
            <div className='col-1 px-0'>
                {(this.props.video) &&
                  <a href='#' className='text-light skip-icon' onClick={this.handleSkip}>
                    <span className='glyphicon glyphicon-forward bg-light-text' aria-hidden='true' />
                  </a>
                }
            </div>
          </div>
        </div>
      </div>
    );
  }

  handleSkip(e) {
    e.preventDefault();
    e.stopPropagation();
    this.props.setLoading();
    this.props.nextVideo();
  }

  onVolChange = (vol_pct) => {
    this.props.setVolPct(vol_pct)
    this.setState({vol_pct: vol_pct});
  };

  grabVolMutex = () => {
    this.setState({
      is_vol_locked: true,
      is_vol_lock_releasable: false
    });
  };
  markVolMutexReleasable = () => {
    this.setState({
      is_vol_lock_releasable: true,
      vol_lock_marked_releasable_time: (new Date()).getTime()
    });
  };
  releaseVolMutex = () => {
    this.setState({
      is_vol_locked: false,
      is_vol_lock_releasable: true
    });
  };

  // TODO: this is deprecated
  componentWillReceiveProps(nextProps) {
    if (this.state.is_vol_locked && this.state.is_vol_lock_releasable) {
      var millis_since_vol_locked_marked_releasable = (new Date()).getTime() - this.state.vol_lock_marked_releasable_time;
      if (millis_since_vol_locked_marked_releasable > (App.QUEUE_POLL_INTERVAL_MS + 500)) {
        this.releaseVolMutex();
      }
    }

    if (!this.state.is_vol_locked) {
      this.setState({vol_pct: nextProps.vol_pct});
    }
  }

}

export default CurrentlyPlayingRight;