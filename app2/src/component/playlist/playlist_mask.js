import React from 'react';

class PlaylistMask extends React.Component {
  getMaskClass() {
    var mask_class = 'd-md-none playlist-mask';

    if (!this.props.playlist_expanded) {
      mask_class += ' unmask';
    }
    if (this.props.playlist_fully_contracted) {
      mask_class += ' hidden-mask';
    }

    return mask_class;
  }

  render() {
    return (
      <div
       onClick={this.props.contractFooterPlaylist}
       className={this.getMaskClass()}></div>
    );
  }
}

export default PlaylistMask;