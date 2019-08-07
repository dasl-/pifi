import React from 'react';

class Header extends React.Component {
  render() {
    return (
      <div className='p-2 pl-md-4 m-0 position-absolute logo-container'>
        <div className='logo-wrapper'>
          <span className='badge badge-light neon80s logo'>pi-fi</span>
        </div>
      </div>
    );
  }
}

export default Header;