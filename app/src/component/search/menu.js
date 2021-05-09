import React from 'react';

class Menu extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      expanded: false
    };

    this.onExpand = this.onExpand.bind(this);
    this.onClickLinkTwo = this.onClickLinkTwo.bind(this);
    this.close = this.close.bind(this);
  }

  render() {
    return (
        <span className='menu-wrapper'>
          <span className='glyphicon glyphicon-menu-hamburger bg-dark-text' onClick={this.onExpand}></span>
          <ul className={this.state.expanded ? 'menu expanded': 'menu'}>
            <li><a href='/snake'>Snake</a></li>
            <li><a href='#' onClick={this.onClickLinkTwo}>Link Two</a></li>
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

  onClickLinkTwo() {
    alert("two");
  }
}

export default Menu;