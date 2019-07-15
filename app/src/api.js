import axios from 'axios';
import gapi from 'gapi-client';

const client = axios.create({
 baseURL: process.env.REACT_APP_API_BASE_URL,
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

  nextVideo() {
    return this.perform('post', '/skip');
  }

  clearQueue() {
    return this.perform('post', '/clear');
  }

  queueVideo(video, color_mode) {
    return this.perform('post', '/queue', {
        url: video.video_url,
        color: color_mode,
        thumbnail: video.thumbnail_img_src,
        title: video.title
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
      var video_ids = ''
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