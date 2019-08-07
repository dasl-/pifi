import React from 'react';

/**
 * This class is used to detect went to go out of a loading state given a video being passed into a component
 * Loading will be set to false any time the video in the child component is altered
 * The child is expected to have a video thumbnail that calls back to setImageLoaded when its done loading
 */
class LoadWithVideo extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      image_loading: true,
      loading: false,
      video: props.video
    };

    this.setLoading = this.setLoading.bind(this);
    this.setImageLoaded = this.setImageLoaded.bind(this);
    this.removeLoading = this.removeLoading.bind(this);
  }

  static getDerivedStateFromProps(props, state) {
    if (props.video === null || (props.video && state.video && props.video.video_id !== state.video.video_id)) {
      return {
        image_loading: (props.video === null ? false : (props.video.thumbnail !== state.video.thumbnail)),
        loading: false,
        video: props.video
      };
    }

    return {
      video: props.video
    };
  }

  // Child component needs to call these functions when it should go into a loading state, and when its finished loading the thumbnail
  setLoading() {
    this.setState({'loading':true});
  }

  setImageLoaded() {
    this.setState({'image_loading':false});
  }

  removeLoading() {
    this.setState({'loading':false});
  }

  render() {
    const childrenWithLoading = React.Children.map(this.props.children, child => {
      return React.cloneElement(child, {
        video: this.props.video,
        loading: this.state.loading || this.state.image_loading,
        setLoading: this.setLoading,
        setImageLoaded: this.setImageLoaded,
        removeLoading: this.removeLoading
      });
    });

    return childrenWithLoading;
  }
}

export default LoadWithVideo;