import React from 'react';

import api from 'api';
import App from 'component/app/app';
import SearchResult from './search_result';
import SearchResultVideo from 'dataobj/search_result_video';

import './search.css';

class Search extends React.Component {
  constructor(props) {
    super(props);
    this.apiClient = new api();

    var stored_results = [];
    try {
      stored_results = JSON.parse(localStorage.getItem("latest_results") || "[]");
    } catch (e) {
      stored_results = [];
    }

    this.state = {
      loading: false,
      search_term: localStorage.getItem("last_search") || "",
      search_results: SearchResultVideo.fromArray(stored_results)
    };

    this.search = this.search.bind(this);
    this.changeSearchTerm = this.changeSearchTerm.bind(this);

    this.searchInputRef = React.createRef();
  }

  render() {
    return (
      <div>
        <form onSubmit={this.search} action="/">
          <div className="header">
            <div className="form-group">
              <div className="input-group search-input-group">
                <input type="search" className="form-control" id="query" placeholder="Search YouTube..." ref={this.searchInputRef}
                       value={this.state.search_term} onChange={(value) => this.changeSearchTerm(value)} />

                <div className="input-group-btn">
                  <button className="btn btn-primary" type="button" id="submitquery" onClick={this.search}>
                    <span className='hidden-xs'>Search <span className="glyphicon glyphicon-search" aria-hidden="true"></span></span>
                    <span className='hidden-sm hidden-md hidden-lg'><span className="glyphicon glyphicon-search" aria-hidden="true"></span></span>
                  </button>
                  <button className="btn btn-primary toggle-color use-color-mode" type="button" onClick={this.props.toggleColorMode}>
                     <span className='hidden-xs'><span className="glyphicon glyphicon-eye-open" aria-hidden="true"></span> Color Mode</span>
                     <span className='hidden-sm hidden-md hidden-lg'><span className="glyphicon glyphicon-eye-open" aria-hidden="true"></span></span>
                  </button>

                </div>
              </div>
            </div>
          </div>
        </form>

        { this.state.loading
          ? <div className="search-results-loading"><div className='dot-pulse'></div></div>
          : <div className="search-results">
              {this.state.search_results.map(function(video, index) {
                return <SearchResult
                  key = {index}
                  video = {video}
                  enqueueVideo = {this.props.enqueueVideo} />
              }.bind(this))}
            </div>
        }
      </div>
    );
  }

  changeSearchTerm(e) {
    this.setState({search_term: e.target.value});
  }

  search(e) {
    e.preventDefault();

    // make sure soft keyboards get hidden
    var target = this.searchInputRef.current;
    setTimeout(() => {
      target.focus();
      target.blur();
    }, 20);

    localStorage.setItem("last_search", this.state.search_term);

    this.setState({loading: true});

    this.apiClient.searchYoutube(this.state.search_term)
      .then((data) => {
        localStorage.setItem("latest_results", JSON.stringify(data));
        this.setState({
          search_results: SearchResultVideo.fromArray(data),
          loading: false
        });
      });
  }
}

export default Search;