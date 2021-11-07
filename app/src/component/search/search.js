import React from 'react';
import SearchBar from './search_bar';
import SearchResults from './search_results';
import Logo from './logo';
import './search.css';

class Search extends React.Component {
  render() {
    return (
      <div>
        <Logo />
        <section className="py-4 bg-light">
          <SearchBar
            loading={this.props.search_loading}
            search_term={this.props.search_term}
            onSearchTermChange={this.props.onSearchTermChange}
            onSubmit={this.props.onSubmit}
            is_screensaver_enabled={this.props.is_screensaver_enabled}
          />
          <SearchResults
            loading={this.props.search_loading}
            search_results={this.props.search_results}
            queueVideo={this.props.queueVideo}
          />
        </section>
      </div>
    );
  }
}

export default Search;