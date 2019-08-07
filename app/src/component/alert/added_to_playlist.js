import React from 'react';
import './added_to_playlist.css'

class SuccessAlert extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      visible: false,
      show: props.show
    };
  }

  componentDidMount() {
    if (this.state.show) {
      setTimeout(this.trigger.bind(this), 10);
    }
  }

  render() {
    var color_class = ' color-mode-' + this.props.color_mode;
    var triggered_class = (!this.state.visible) ? ' untriggered' : '';

    return (
      <div className={'play-queue ' + color_class + triggered_class}>
        <div className='play-queue-trigger bg-success'>
          <div className='queue-thumbnail'>
            {(this.props.video) && (
              <div className="img-container px-2">
                <img
                  src={this.props.video.thumbnail}
                  className='img-responsive w-100 bg-dark'
                  alt={this.props.video.title}/>
              </div>
            )}
          </div>
          <div className="p-2 text-light">Added!</div>
       </div>
     </div>
    );
  }

  trigger() {
    this.setState({visible: true});
    setTimeout(this.hide.bind(this), 2000);
  }

  hide() {
    this.setState({show: false, visible: false});
  }
}

export default SuccessAlert;