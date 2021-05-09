import React from 'react';
import Menu from './menu';

class SearchBar extends React.Component {
  constructor(props) {
    super(props);

    this.onSubmit = this.onSubmit.bind(this);
    this.onSearchTermChange = this.onSearchTermChange.bind(this);
    this.search_input = React.createRef();
  }

  render() {
    return (

      <form onSubmit={this.onSubmit} action='/' className='text-center px-2'>

        <div className='input-group input-group-lg px-3'>
          <div className='input-group-wrapper'>
            <div className='input-group-append'>
              <span className='input-group-text input-left'>
                <Menu
                  is_screensaver_enabled={this.props.is_screensaver_enabled}
                />

              </span>
            </div>

            <input disabled = {this.props.loading ? 'disabled' : ''}
              type='search' className='form-control' placeholder='Search YouTube...'
              value={this.props.search_term} ref={this.search_input}
              onChange={this.onSearchTermChange} />

            <div className='input-group-append'>
              <span className='input-group-text input-right' onClick={this.onSubmit}>
                <span className='glyphicon glyphicon-search bg-dark-text'></span>
              </span>
            </div>
          </div>
        </div>
      </form>
    );
  }

  onSubmit(e) {
    e.preventDefault();

    // make sure soft keyboards get hidden
    var target = this.search_input.current;
    setTimeout(() => {
      target.focus();
      target.blur();
    }, 20);

    this.props.onSubmit();
  }

  onSearchTermChange(e) {
    e.preventDefault();
    this.props.onSearchTermChange(e.target.value);
  }
}

export default SearchBar;