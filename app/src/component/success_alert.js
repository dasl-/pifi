import React from 'react';

class SuccessAlert extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      visible: false,
      show: props.show
    };
  }

  render() {
    var triggered_class = (!this.state.visible) ? 'untriggered' : '';

    if (this.state.show) {
      setTimeout(this.trigger.bind(this), 10);
    }

    return (
      <div className={'play-queue ' + triggered_class}>
        <div className='play-queue-trigger bg-success'>
          <div className='queue-thumbnail'>
            {(this.props.video) && (
              <img
                src={this.props.video.thumbnail_img_src}
                className='img-responsive'
                alt={this.props.video.title}/>
            )}
          </div>
          <p>Added!</p>
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