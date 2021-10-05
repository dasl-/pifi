import React from 'react';
import api from 'api';

class Menu extends React.Component {
  constructor(props) {
    super(props);

    this.apiClient = new api();

    this.state = {
      expanded: false
    };

    this.onExpand = this.onExpand.bind(this);
    this.onClickScreensaver = this.onClickScreensaver.bind(this);
    this.close = this.close.bind(this);
  }

  render() {
    return (
        <span className='menu-wrapper'>
          <span className='glyphicon glyphicon-menu-hamburger bg-dark-text' onClick={this.onExpand}></span>
          <ul className={this.state.expanded ? 'menu expanded' : 'menu'}>
            <li><span role='img' aria-label='snake'>🐍</span> <a href='/snake'>Snake</a></li>
            <li>
              <a href='#' onClick={this.onClickScreensaver}>
                <span className='glyphicon glyphicon-off bg-dark-text' onClick={this.onExpand}></span> {this.props.is_screensaver_enabled ? 'Disable' : 'Enable'} screensaver
              </a>
            </li>
          </ul>
      </span>
    );
  }

  onExpand() {
    this.setState({'expanded': !this.state.expanded});
  }

  close() {
    this.setState({
      'expanded': false,
    });
  }

  componentDidUpdate(){
    setTimeout(() => {
      if(this.state.expanded){
        window.addEventListener('click', this.close)
      }
      else{
        window.removeEventListener('click', this.close)
      }
    }, 0)
  }

  /**
   * Toggle game of life screensaver
   */
  onClickScreensaver(e) {
    e.preventDefault();
    this.apiClient.setScreensaverEnabled(!this.props.is_screensaver_enabled);
  }
}

export default Menu;