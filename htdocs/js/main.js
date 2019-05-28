var last_request;

function loadClient() {
  gapi.client.setApiKey(API_KEY);
  return gapi.client.load("https://www.googleapis.com/discovery/v1/apis/youtube/v3/rest")
      .then(function() { console.log("GAPI client loaded for API"); },
            function(err) { console.error("Error loading GAPI client for API", err); });
}

function abbreviateNumber(value) {
  var newValue = value;
  if (value >= 1000) {
      var suffixes = ["", "K", "M", "B","T"];
      var suffixNum = Math.floor( (""+value).length/3 );
      var shortValue = '';
      for (var precision = 2; precision >= 1; precision--) {
          shortValue = parseFloat( (suffixNum != 0 ? (value / Math.pow(1000,suffixNum) ) : value).toPrecision(precision));
          var dotLessShortValue = (shortValue + '').replace(/[^a-zA-Z 0-9]+/g,'');
          if (dotLessShortValue.length <= 2) { break; }
      }
      if (shortValue % 1 != 0)  shortNum = shortValue.toFixed(1);
      newValue = shortValue+suffixes[suffixNum];
  }
  return newValue;
}

function timeDifference(current, previous) {
  var msPerMinute = 60 * 1000;
  var msPerHour = msPerMinute * 60;
  var msPerDay = msPerHour * 24;
  var msPerMonth = msPerDay * 30;
  var msPerYear = msPerDay * 365;
  var elapsed = current - previous;

  if (elapsed < msPerMinute) {
       return Math.round(elapsed/1000) + ' seconds';
  } else if (elapsed < msPerHour) {
       return Math.round(elapsed/msPerMinute) + ' minutes';
  } else if (elapsed < msPerDay ) {
       return Math.round(elapsed/msPerHour ) + ' hours';
  } else if (elapsed < msPerMonth) {
      return Math.round(elapsed/msPerDay) + ' days';
  } else if (elapsed < msPerYear) {
      return Math.round(elapsed/msPerMonth) + ' months';
  } else {
      return Math.round(elapsed/msPerYear ) + ' years';
  }
}

function convertISO8601ToSeconds(input) {
  var reptms = /^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$/;
  var hours = 0, minutes = 0, seconds = 0, totalseconds;

  if (reptms.test(input)) {
      var matches = reptms.exec(input);
      if (matches[1]) hours = Number(matches[1]);
      if (matches[2]) minutes = Number(matches[2]);
      if (matches[3]) seconds = Number(matches[3]);
      totalseconds = hours * 3600  + minutes * 60 + seconds;
  }


  if (totalseconds > 3600) {
    var show_minutes = Math.round(totalseconds/60).toString().padStart(2, '0')
    var show_seconds = Math.round(totalseconds%60).toString().padStart(2, '0')
    return Math.floor(totalseconds/3600).toString().padStart(2, '0') + ":" + show_minutes + ":" + show_seconds;
  } else {
    var show_minutes = Math.floor(totalseconds/60)
    var show_seconds = Math.round(totalseconds%60).toString().padStart(2, '0')
    return show_minutes + ":" + show_seconds;
  }
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
        $("#search_results").empty();
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

    $("#search_results").append(
      `<div class='row search-result' data-load-url='https://www.youtube.com/watch?v=${video_id}'>
        <div class='col-sm-4 search-result-image'>
          <img src='${img_src}' class='img-responsive' width='100%' />
          <span class='duration'>${duration}</span>
        </div>
        <div class='col-sm-8'>
          <div class='title-padding hidden-sm hidden-md hidden-lg'></div>
          <h4 class='title'>${title}</h4>
          <div><h6>${channel} | ${view_count} views | ${published} ago</h6></h6>
          <p>${description}</p>
        </div>
      </div>`
    );
  }
}

function runQuery() {
  localStorage.setItem("latest_query", $("#query").val());
  if ($("#query").val() != "") {
    clearTimeout(last_request);
    last_request = setTimeout(function() {
      search(
        $("#query").val(),
        ($('#color').is(':checked') ? true : false)
      );
    }, 50)
  }
}

function setBodyClass() {
  $('body').toggleClass('black-and-white', !$('#color').is(':checked'));
}

function playVideo(url, is_color) {
  $.ajax({
    type: "POST",
    url: "/index.html",
    data: JSON.stringify({
      url: url,
      color: is_color
    }),
    success: function() {
      alert("LOADING...")
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

  $('#color')
    .on("click", setBodyClass)

  $("#search_results")
    .on("click", ".search-result", function() {
      playVideo($(this).closest(".search-result").data("load-url"), false)
    })

  $('.toggle-color')
    .on('click', function() {
      $('#color').trigger('click');
    })
});