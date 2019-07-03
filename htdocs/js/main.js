var last_request;

function loadClient() {
  gapi.client.setApiKey(API_KEY);
  return gapi.client.load("https://www.googleapis.com/discovery/v1/apis/youtube/v3/rest")
      .then(function() { console.log("GAPI client loaded for API"); },
            function(err) { console.error("Error loading GAPI client for API", err); });
}

function search(query) {
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

      gapi.client.youtube.videos.list({
        "part": "snippet,contentDetails,statistics",
        "id": video_ids
      })
      .then(function(response) {
        $("#search-results").empty();
        var videos = response.result.items;

        localStorage.setItem("latest_results", JSON.stringify(videos));
        showVideos(videos);
      },
      function(err) { console.error("Execute error", err); });
    },
    function(err) { console.error("Execute error", err); });
}

function showVideos(videos) {
  for (var video_i in videos) {
    var video = videos[video_i];
    var video_id = video.id;
    var img_src = video.snippet.thumbnails.high.url;
    var description = video.snippet.description.split(' ').slice(0,30).join(' ') + "...";
    var title = video.snippet.title;
    var channel = video.snippet.channelTitle;
    var published = timeDifference(Date.now(), Date.parse(video.snippet.publishedAt));
    var view_count = abbreviateNumber(video.statistics.viewCount);
    var duration = convertISO8601ToSeconds(video.contentDetails.duration)

    $("#search-results-loading").addClass("hidden");
    $("#search-results").append(
      `<div class='row search-result' data-load-url='https://www.youtube.com/watch?v=${video_id}' data-video-id="${video_id}">
        <div class='col-sm-4 search-result-image'>
          <div class='loading-cover'><div class='dot-pulse'></div></div>
          <img src='${img_src}' class='img-responsive' width='100%' />
          <span class='duration'>${duration}</span>
        </div>
        <div class='col-sm-8 video-data'>
          <div class='title-padding hidden-sm hidden-md hidden-lg'></div>
          <h4 class='title'>${title}</h4>
          <div><h6>${channel} | ${view_count} views | ${published} ago</h6></div>
          <p>${description}</p>
        </div>
      </div>`
    );
  }
}

function runQuery() {
  localStorage.setItem("latest_query", $("#query").val());
  if ($("#query").val() != "") {
    $("#search-results").empty();
    $("#search-results-loading").removeClass("hidden");
    clearTimeout(last_request);
    last_request = setTimeout(function() {
      search($("#query").val());
    }, 50)
  }
}

function setBodyClass() {
  $('body').toggleClass('black-and-white', !$('#color').is(':checked'));
}

function handleSearchResultClick(target) {
  if (!target.is(".loading")) {
    target.addClass("loading")

    post_playVideo(
      target.data("video-id"),
      target.data("load-url"),
      ($('#color').is(':checked') ? true : false),
      target
    )
  }
}

function post_playVideo(video_id, url, is_color, target) {
  $.ajax({
    type: "POST",
    url: "/index.html",
    data: JSON.stringify({
      action: 'enqueue',
      url: url,
      color: is_color
    }),
    success: function() {
      setTimeout(function() {
        target.removeClass("loading");
        showPlaylistSuccess(
          video_id,
          target.find("img.img-responsive").attr("src")
        );
      }, 500);
    },
    error: function() {
      setTimeout(function() {
        target.removeClass("loading");
      }, 500);
    },
  });
}

function post_skip() {
  $.ajax({
    type: "POST",
    url: "/index.html",
    data: JSON.stringify({
      action: 'skip'
    }),
    success: function() {

    }
  });
}

function post_clear() {
  $.ajax({
    type: "POST",
    url: "/index.html",
    data: JSON.stringify({
      action: 'clear'
    }),
    success: function() {

    }
  });
}

function load() {
  try {
    $("#query").val(localStorage.getItem("latest_query"));
    showVideos(JSON.parse(localStorage.getItem("latest_results")));
  } catch(err) {
    //ignore
  }
}

function showPlaylistSuccess(video_id, img_src) {
  let alert = $(`<div class='play-queue untriggered'>
      <div class='play-queue-trigger bg-success'>
        <div class='queue-thumbnail'>
          <img src='${img_src}' class='img-responsive' />
        </div>
        <p>Added!</p>
      </div>
    </div>`);

  $('body').append(alert);

  setTimeout(function() {
    alert.removeClass("untriggered");
    setTimeout(function() {
      alert.addClass("untriggered");
      setTimeout(function() {
        alert.remove();
      }, 2000);
    }, 2000);
  }, 100);
}

$(document).ready(function() {
  setBodyClass();

  gapi.load("client:auth2", function() {
    gapi.auth2.init({
      quotaUser: QUOTA_USER
      // removing the client id lets me run it, but hits cap
      //client_id: CLIENT_ID
    });
  })
  setTimeout(function(){
    loadClient().then(load)
  }, 500);

  $('#submitquery')
    .on("tap", runQuery)
    .on("click", runQuery)

  $('#query')
    .on("keypress", function(e){
      var code = e.which;
      console.log(code);
      if(code==13||code==188||code==186){
          runQuery();
      }
    });

  $('#color')
    .on("click", setBodyClass)

  $("#search-results")
    .on("click", ".search-result", function() {
      handleSearchResultClick($(this).closest(".search-result"));
    })

  $(".action-skip")
    .on("click", function(e) {
      e.preventDefault();
      post_skip();
    });

  $(".action-clear")
    .on("click", function(e) {
      e.preventDefault();
      post_clear();
    });

  $('.toggle-color')
    .on('click', function() {
      $('#color').trigger('click');
    })
});