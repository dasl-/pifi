export default {
  abbreviateNumber(value) {
    var newValue = value;
    if (value >= 1000) {
        var suffixes = ["", "K", "M", "B","T"];
        var suffixNum = Math.floor( (""+value).length/3 );
        var shortValue = '';
        for (var precision = 2; precision >= 1; precision--) {
            shortValue = parseFloat( (suffixNum !== 0 ? (value / Math.pow(1000,suffixNum) ) : value).toPrecision(precision));
            var dotLessShortValue = (shortValue + '').replace(/[^a-zA-Z 0-9]+/g,'');
            if (dotLessShortValue.length <= 2) { break; }
        }
        newValue = shortValue+suffixes[suffixNum];
    }
    return newValue;
  },

  timeDifference(current, previous) {
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
  },

  convertISO8601ToSeconds(input) {
    var reptms = /^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$/;
    var hours = 0, minutes = 0, seconds = 0, totalseconds;

    if (reptms.test(input)) {
        var matches = reptms.exec(input);
        if (matches[1]) hours = Number(matches[1]);
        if (matches[2]) minutes = Number(matches[2]);
        if (matches[3]) seconds = Number(matches[3]);
        totalseconds = (hours * 3600)  + (minutes * 60) + seconds;
    }

    var show_minutes, show_seconds;

    if (totalseconds > 3600) {
      show_minutes = Math.round((totalseconds%3600)/60).toString().padStart(2, '0');
      show_seconds = Math.round((totalseconds%3600)%60).toString().padStart(2, '0');
      return Math.floor(totalseconds/3600).toString().padStart(2, '0') + ":" + show_minutes + ":" + show_seconds;
    } else {
      show_minutes = Math.floor(totalseconds/60)
      show_seconds = Math.round(totalseconds%60).toString().padStart(2, '0');
      return show_minutes + ":" + show_seconds;
    }
  },

  areArraysEqual(a, b) {
    if (a === b) return true;
    if (a == null || b == null) return false;
    if (a.length !== b.length) return false;

    a.sort();
    b.sort();

    for (var i = 0; i < a.length; ++i) {
      if (a[i] !== b[i]) return false;
    }
    return true;
  }
}