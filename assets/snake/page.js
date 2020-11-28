var page = (() => {

    function init() {
        $(".initialcontainer").hide();

        $(".new-game").click(function(){
            snake_runner.newGame();
        });

        //Menu button for mobile
        $(".menubutton").click(function() {
            $(".menu").slideToggle("fast");
        });

        //Dropdown menu toggle
        $(".dropdown").click(function() {
            $(this).next("ul").toggle("fast","swing");
        });

        //Show/hide leaderboard
        $("#leader").click(function() {
            showLeaderboard();
        });

        $(document).mouseup(function (e) {
            var container = $(".leaderboard");
            if (!container.is(e.target) && container.has(e.target).length === 0){
                hideLeaderboard();
            }
        });

        $(document).on('keydown.page', function(e) {
            if(e.keyCode == 27) { // esc
                hideLeaderboard();
                hideDropdown();
            }
        });

        //Lower difficulty if mobile
        var isTouchDevice = 'ontouchstart' in document.documentElement;
        if ( isTouchDevice ) {
            // do mobile handling
            var difficulty = $('#difficulty');
            difficulty.val('3');

            $(".new-game").click(function() {
                $(".menu").hide();
            });
        }

        // set difficulty from saved value per browser
        $('#difficulty').on('input', function() {
            localStorage.setItem('difficulty', this.value);
            document.getElementById('difficultyval').innerHTML = this.value;
        });

        var saved_difficulty = localStorage.getItem('difficulty');
        if (saved_difficulty !== null && parseInt(saved_difficulty) == saved_difficulty &&
            saved_difficulty > 0 && saved_difficulty < 10
        ) {
            $('#difficulty').val(saved_difficulty);
        }

        document.getElementById('difficultyval').innerHTML = document.getElementById('difficulty').value;

        setupVolume();

        // https://github.com/mozilla-mobile/firefox-ios/issues/5772#issuecomment-573380173
        if (window.__firefox__) {
            window.__firefox__.NightMode.setEnabled(false);
        }
    }

    function showLeaderboard() {
        getHighScores();
        $(".leaderboard").fadeIn();
    }

    function hideLeaderboard() {
        $(".leaderboard").fadeOut();
    }

    function hideDropdown() {
        $('.dropdown').next("ul").hide("fast","swing");
    }

    function getHighScores() {
        $("#leaderrow").html("Loading...");
        $.get({
            url: "/api/high_scores",
            data: JSON.stringify({
                game_type: 'snake'
            }),
            success: function(response) {
                var high_scores = response.high_scores;
                var rank;
                if(high_scores === undefined || high_scores.length == 0) {
                    $("#leaderrow").html("No High Scores");
                    return;
                }
                $("#leaderrow").html("");
                high_scores.forEach((high_score, index) => {
                    //add leading zeros to 1 and 2 digit scores
                    var score = high_score.score.toString().padStart(3, '0');
                    rank = index + 1;
                    $("#leaderrow").append("<li><span class='leaderinitial rank-" + rank + "'></span>" +
                        " .............<span class='leaderscore rank-" + rank + "'></span></li>");
                    $("#leaderrow .leaderinitial.rank-" + rank).text(high_score.initials);
                    $("#leaderrow .leaderscore.rank-" + rank).text(score);
                });
            }
        });
    }

    var VOL_POLL_INTERVAL_MS = 1000;
    var is_vol_locked = false;
    var is_vol_lock_releasable = true;
    var vol_lock_marked_releasable_time = 0;

    function setupVolume() {
        window.setInterval(
            function() {
                if (is_vol_locked && is_vol_lock_releasable) {
                    var millis_since_vol_locked_marked_releasable = (new Date()).getTime() - vol_lock_marked_releasable_time;
                    if (millis_since_vol_locked_marked_releasable > (VOL_POLL_INTERVAL_MS + 500)) {
                        releaseVolMutex();
                    }
                }

                if (is_vol_locked) {
                    return;
                }

                $.get({
                    url: "/api/vol_pct",
                    success: function(response) {
                        var volume = Math.round(response.vol_pct);
                        $('#volume').val(volume);
                        document.getElementById('volumeval').innerHTML = volume;
                    }
                });
            },
            VOL_POLL_INTERVAL_MS
        );

        // happens many times while the slider is dragged
        $('#volume').on('input', function() {
            grabVolMutex();
            document.getElementById('volumeval').innerHTML = this.value;
            $.post({
                url: "/api/vol_pct",
                data: JSON.stringify({
                    vol_pct: this.value
                })
            });
        });

        // happens once when the slider is released
        $('#volume').on('change', function() {
            markVolMutexReleasable();
        });
    }

    function grabVolMutex() {
        is_vol_locked = true;
        is_vol_lock_releasable = false;
    }

    function markVolMutexReleasable() {
        is_vol_lock_releasable = true;
        vol_lock_marked_releasable_time = (new Date()).getTime();
    }

    function releaseVolMutex() {
        is_vol_locked = false;
        is_vol_lock_releasable = true;
    }

    return {
        init: init,
        showLeaderboard: showLeaderboard
    };

})();