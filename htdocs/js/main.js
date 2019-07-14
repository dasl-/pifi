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
          <img src='${img_src}' class='img-responsive video-thumbnail' width='100%' />
          <span class='duration'>${duration}</span>
        </div>
        <div class='col-sm-8 video-data'>
          <div class='title-padding hidden-sm hidden-md hidden-lg'></div>
          <h4 class='title'>${title}</h4>
          <div><h6>${channel} | ${view_count} views | ${published} ago</h6></div>
          <p class='video-description'>${description}</p>
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
      target.find(".video-thumbnail").attr('src'),
      target.find(".title").text(),
      target
    )
  }
}

function post_playVideo(video_id, url, is_color, thumbnail, title, target) {
  $.ajax({
    type: "POST",
    url: "/index.html",
    data: JSON.stringify({
      action: 'enqueue',
      url: url,
      thumbnail: thumbnail,
      title: title,
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

      get_queue();
    },
    error: function() {
      setTimeout(function() {
        target.removeClass("loading");
      }, 500);

      get_queue();
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
      get_queue();
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
      get_queue();
    }
  });
}

function togglePlaylist() {
  if ($(".playlist-container").is(".expanded")) {
    $(".playlist-container").toggleClass("expanded");
  } else {
    $(".playlist-contents").empty();
    $(".playlist-container").toggleClass("expanded");
    get_queue();
  }
}

function get_queue() {
  $.ajax({
    type: "GET",
    url: "/api/get_queue",
    success: function(result) {
      result = JSON.parse(result);
      loadQueue(result.queue);
    }
  });
}

function loadQueue(videos) {
  var current = null;
  var video_contents = [];

  for (var video_i in videos) {
    var video = videos[video_i];
    var video_id = video.id;
    var video_status = video.status;
    var img_src = video.thumbnail;
    var title = video.title;
    var url = video.url;
    var is_current = video.is_current;
    var is_color = video.is_color;

    color_class = is_color ? 'color' : 'black-and-white';
    current_class = '';

    if (is_current) {
      current = video;
      current_class = 'current';
    }

    video_contents.push(
      `<div class='row playlist-video ${color_class} ${current_class}'>
        <div class='col-xs-4 col-sm-4 playlist-video't-image'>
          <img src='${img_src}' class='img-responsive video-thumbnail' width='100%' />
        </div>
        <div class='col-xs-7 col-sm-8 video-data'>
          <h5 class='title'>${title}</h5>
        </div>
      </div>`
    );
  }

  if (videos.length === 0) {
    $(".playlist-contents").html("<div class='empty'>&lt;Empty Queue&gt;</div>");
  } else {
    var existing_rows = $(".playlist-contents").find(".row")

    existing_rows.each(function(i, row) {
        if (typeof video_contents[i] !== "undefined") {
          $(row).replaceWith(video_contents[i]);
        } else {
          $(row).remove();
        }
    });

    if (video_contents.length > existing_rows.length) {
      $(".playlist-contents").append(video_contents.slice(existing_rows.length));
    }
  }

  if (current === null) {
    $(".currently-playing").html("Playing: &lt;Nothing&gt;")
  } else {
    $(".currently-playing").html("Playing: " + current.title)
  }
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
  get_queue();

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

  $(".playlist-details")
    .on('click', togglePlaylist)
});