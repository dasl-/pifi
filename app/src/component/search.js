import React from 'react';

import api from 'api';
import SearchResult from 'component/search-result';
import Video from 'dataobj/video';

class Search extends React.Component {
  constructor(props) {
    super(props);
    this.apiClient = new api();

    this.state = {
      loading: false,
      search_term: localStorage.getItem("last_search") || "",
      search_results: Video.prototype.fromArray(JSON.parse(localStorage.getItem("latest_results") || "[]"))
    };

    this.search = this.search.bind(this);
    this.changeSearchTerm = this.changeSearchTerm.bind(this);
  }

  render() {
    return (
      <div>
        <form onSubmit={this.search}>
          <div className="header">
            <div className="form-group">
              <div className="input-group search-input-group">
                <input type="text" className="form-control" id="query" placeholder=""
                       value={this.state.search_term} onChange={(value) => this.changeSearchTerm(value)} />

                <div className="input-group-btn">
                  <button className="btn btn-primary" type="button" id="submitquery" onClick={this.search}>
                    <span className='hidden-xs'>Search <span className="glyphicon glyphicon-search" aria-hidden="true"></span></span>
                    <span className='hidden-sm hidden-md hidden-lg'><span className="glyphicon glyphicon-search" aria-hidden="true"></span></span>
                  </button>
                  <button className="btn btn-success show-in-color toggle-color" type="button" onClick={this.props.toggleColorMode}>
                     <span className='hidden-xs'><span className="glyphicon glyphicon-eye-open" aria-hidden="true"></span> Color</span>
                     <span className='hidden-sm hidden-md hidden-lg'><span className="glyphicon glyphicon-eye-open" aria-hidden="true"></span></span>
                  </button>
                  <button className="btn btn-default show-in-black-and-white toggle-color" type="button" onClick={this.props.toggleColorMode}>
                    <span className='hidden-xs'><span className="glyphicon glyphicon-eye-open" aria-hidden="true"></span> B&W</span>
                    <span className='hidden-sm hidden-md hidden-lg'><span className="glyphicon glyphicon-eye-open" aria-hidden="true"></span></span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </form>

        { this.state.loading
          ? <div id="search-results-loading"><div className='dot-pulse'></div></div>
          : <div id="search-results">
              {this.state.search_results.map(function(video, index) {
                return <SearchResult
                  key = {index}
                  video = {video}
                  queueVideo = {this.props.queueVideo} />
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
    localStorage.setItem("last_search", this.state.search_term);

    this.setState(state => ({
      loading: true
    }));

    this.apiClient.searchYoutube(this.state.search_term)
      .then((data) => {
        localStorage.setItem("latest_results", JSON.stringify(data));
        this.setState(state => ({
          search_results: Video.prototype.fromArray(data),
          loading: false
        }));
      });
  }
}

export default Search;