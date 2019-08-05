import React from 'react';

class Header extends React.Component {
  render() {
    return (
      <nav className='navbar navbar-expand-lg navbar-light fixed-top' style={{'width':'50px'}}>
        <div className='container p-0 m-0'>
          <span className='navbar-brand d-none d-sm-block'>PiFi</span>
          <span className='badge badge-light d-block d-sm-none'>PiFi</span>
        </div>
      </nav>
    );
  }
}

export default Header;