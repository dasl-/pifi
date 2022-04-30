import axios from 'axios';
import gapi from 'gapi-client';

// By default, include the port i.e. 'pifi.club:666' in the api host to
// support running the pifi on a custom port
function getApiHost() {
  var api_host = window.location.host;
  if (process.env.REACT_APP_API_HOST !== undefined) {
    api_host = process.env.REACT_APP_API_HOST;
  } else {
    if (process.env.NODE_ENV === 'development') {
      if (window.location.hostname === 'localhost') {
        // 'localhost' indicates we are probably running the npm development server on a laptop / desktop computer
        // via `npm start --prefix app`
        api_host = 'pifi.club'; // Default to this
      } else {
        // API url should not include the :3000 port that is present in the development server url
        api_host = window.location.hostname;
      }
    }
  }
  return api_host;
}

const client = axios.create({
  baseURL: "//" + getApiHost() + "/api",
  json: true
});

//On load, called to load the auth2 library and API client library.
gapi.load('client', initGoogleClient);

// Initialize the API client library
function initGoogleClient() {
  const api_client = new APIClient();
  api_client.getYoutubeApiKey().then((data) => {
    if (data.success) {
      gapi.client.init({
        apiKey: data.youtube_api_key,
        discoveryDocs: ["https://www.googleapis.com/discovery/v1/apis/youtube/v3/rest"],
      });
    }
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

  playVideoNext(video) {
    return this.perform('post', '/play_next', {
      playlist_video_id: video.playlist_video_id
    });
  }

  setVolPct(vol_pct) {
    return this.perform('post', '/vol_pct', {
      vol_pct: vol_pct
    });
  }

  setScreensaverEnabled(is_enabled) {
    return this.perform('post', '/screensaver', {
      is_screensaver_enabled: is_enabled
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
    .then(
      function(response) {
        var videos = response.result.items;
        var video_ids = '';
        for (var i in videos) {
          video_ids += videos[i].id.videoId + ",";
        }

        return gapi.client.youtube.videos.list({
          "part": "snippet,contentDetails,statistics",
          "id": video_ids
        })
        .then(
          function(response) {
            return response.result.items;
          },
          function(err) {
            console.error("Execute error", err);
          }
        );
      },
      function(err) {
        console.error("Execute error", err);
        if (
          "result" in err &&
          "error" in err["result"] &&
          "code" in err["result"]["error"] &&
          err["result"]["error"]["code"] === 403
        ) {
          // youtube api quota exceeded. Reload the page to see if the API key we are supposed to use changed
          // on the server side
          // See: https://github.com/dasl-/piwall2/blob/main/docs/youtube_api_keys.adoc#quota
          window.location.reload();
        }
      }
    );
  }

  getYoutubeApiKey() {
    return this.perform('get', '/youtube_api_key');
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
