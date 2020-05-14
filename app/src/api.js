import axios from 'axios';
import gapi from 'gapi-client';

const client = axios.create({
 baseURL: "//" + window.location.host + "/api",
 json: true
});

//On load, called to load the auth2 library and API client library.
gapi.load('client:auth2', initGoogleClient);

// Initialize the API client library
function initGoogleClient() {
  gapi.client.init({
    discoveryDocs: ["https://www.googleapis.com/discovery/v1/apis/youtube/v3/rest"],
    client_id: process.env.REACT_APP_GOOGLE_CLIENT_ID
  }).then(function () {
    gapi.client.setApiKey(process.env.REACT_APP_GOOGLE_API_KEY);
  });
}

class APIClient {
  getQueue() {
   return this.perform('get', '/queue');
  }

  // Passing the id of the video to skip ensures our skips are "atomic". That is, we can ensure we skip the
  // video that the user intended to skip.
  nextVideo(playlist_video_id) {
    return this.perform('post', '/skip', {
      playlist_video_id: playlist_video_id
    });
  }

  removeVideo(video) {
    return this.perform('post', '/remove', {
      playlist_video_id: video.playlist_video_id
    });
  }

  setVolPct(vol_pct) {
    return this.perform('post', '/vol_pct', {
      vol_pct: vol_pct
    });
  }

  clearQueue() {
    return this.perform('post', '/clear');
  }

  enqueueVideo(video, color_mode) {
    return this.perform('post', '/queue', {
        url: video.video_url,
        color_mode: color_mode,
        thumbnail: video.thumbnail,
        title: video.title,
        duration: video.duration
    });
  }

  searchYoutube(query) {
    return gapi.client.youtube.search.list({
      "part": "snippet",
      "maxResults": 25,
      "q": query
    })
    .then(function(response) {
      var videos = response.result.items;
      var video_ids = '';
      for (var i in videos) {
        video_ids += videos[i].id.videoId + ",";
      }

      return gapi.client.youtube.videos.list({
        "part": "snippet,contentDetails,statistics",
        "id": video_ids
      })
      .then(function(response) {
        return response.result.items;
      },
      function(err) { console.error("Execute error", err); });
    },
    function(err) { console.error("Execute error", err); });
  }

  async perform (method, resource, data) {
    return client({
       method,
       url: resource,
       data,
       headers: {}
     }).then(resp => {
       return resp.data ? resp.data : [];
     })
  }
}

export default APIClient;
