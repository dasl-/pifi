import React from 'react';

class Header extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      expanded: false
    };

    this.onExpand = this.onExpand.bind(this);
    this.onClickLinkOne = this.onClickLinkOne.bind(this);
    this.onClickLinkTwo = this.onClickLinkTwo.bind(this);
  }

  render() {
    return (
      <div className='p-2 pl-md-4 m-0 position-absolute logo-container'>
        <div className={this.state.expanded ? 'logo-wrapper expanded': 'logo-wrapper'}>
          {this.state.expanded && 
            <span className='badge badge-light neon80s logo' >
              <span onClick={this.onExpand}>pi-fi</span>

              <ul class="menu">
                <li><a href="#" onClick={this.onClickLinkOne}>Link One</a></li>
                <li><a href="#" onClick={this.onClickLinkTwo}>Link Two</a></li>
              </ul>
            </span>
          }
          {!this.state.expanded && 
            <span className='badge badge-light neon80s logo' onClick={this.onExpand}>pi-fi</span>
          }
        </div>
      </div>
    );
  }

  onExpand() {
    this.setState({'expanded': !this.state.expanded});
  }

  onClickLinkOne() {
    alert("one");
  }

  onClickLinkTwo() {
    alert("two");
  }
}

export default Header;