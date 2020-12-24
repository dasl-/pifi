var page = (() => {

    var POLL_INTERVAL_MS = 1000;

    var is_game_joinable = true;

    var is_touch_device = 'ontouchstart' in document.documentElement;

    function init() {
        $(".initialcontainer").hide();

        setupUiHandlers();
        setupDifficultyInput();
        setupNumPlayersInput();

        // https://github.com/mozilla-mobile/firefox-ios/issues/5772#issuecomment-573380173
        if (window.__firefox__) {
            window.__firefox__.NightMode.setEnabled(false);
        }

        volume.init(false);

        setupPolling();
    }

    function setupUiHandlers() {
        setupNewGameButton();

        //Menu button for mobile
        $(".menubutton").click(function() {
            $(".menu").slideToggle("fast");
        });

        //Settings dropdown menu toggle
        $(".settings_dropdown").click(function() {
            $(this).next("ul").toggle("fast","swing");
        });

        //Show/hide leaderboard
        $("#leader").click(function() {
            showLeaderboard();
        });

        $(document).mouseup(function (e) {
            var $leaderboard_container = $(".leaderboard");
            if (!$leaderboard_container.is(e.target) && $leaderboard_container.has(e.target).length === 0){
                hideLeaderboard();
            }

            var $settings_dropdown_container = $(".settings_dropdown").siblings('ul');
            if (!$settings_dropdown_container.is(e.target) && $settings_dropdown_container.has(e.target).length === 0 &&
                !$('.settings_dropdown').is(e.target)
            ){
                hideSettingsDropdown();
            }

            var $menu_container = $(".menu");
            if (!$menu_container.is(e.target) && $menu_container.has(e.target).length === 0 &&
                !$('.menubutton').is(e.target) && is_touch_device
            ){
                hideMenu();
            }
        });

        $(document).on('keydown.page', function(e) {
            if(e.keyCode == 27) { // esc
                hideLeaderboard();
                hideSettingsDropdown();
            }
        });

        if ( is_touch_device ) {
            // do mobile handling
            $(".new-game").click(function() {
                $(".menu").hide();
            });
        }
    }

    function setupDifficultyInput() {
        var $difficulty_input = $('#difficulty');
        if (is_touch_device) {
            $difficulty_input.val(3);
        }

        $difficulty_input.on('input', function() {
            localStorage.setItem('difficulty', this.value);
            document.getElementById('difficultyval').innerHTML = this.value;
        });

        // set difficulty from saved value per browser
        var saved_difficulty = localStorage.getItem('difficulty');
        if (saved_difficulty !== null && parseInt(saved_difficulty) == saved_difficulty &&
            saved_difficulty > 0 && saved_difficulty < 10
        ) {
            $difficulty_input.val(saved_difficulty);
        }

        document.getElementById('difficultyval').innerHTML = document.getElementById('difficulty').value;
    }

    function setupNumPlayersInput() {
        $('#num_players').on('input', function() {
            document.getElementById('num_players_val').innerHTML = this.value;
        });
        document.getElementById('num_players_val').innerHTML = document.getElementById('num_players').value;
    }

    function setupPolling() {
        window.setInterval(
            function() {
                $.get({
                    url: "/api/snake",
                    success: function(response) {
                        updateNewGameButton(response.is_game_joinable, response.game_joinable_countdown_s);
                        volume.maybeUpdateVolume(Math.round(response.vol_pct));
                    }
                });
            },
            POLL_INTERVAL_MS
        );
    }

    function showLeaderboard() {
        getHighScores();
        $(".leaderboard").fadeIn();
    }

    function hideLeaderboard() {
        $(".leaderboard").fadeOut();
    }

    function hideSettingsDropdown() {
        $('.settings_dropdown').next("ul").hide("fast","swing");
    }

    function hideMenu() {
        $('.menu').hide("fast","swing");
    }

    function setupNewGameButton() {
        $(".new-game").click(function(){
            snake_runner.newGame();
        });
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
                        "<div class='scorespacer'>&nbsp;............</div>" +
                        "<span class='leaderscore rank-" + rank + "'></span></li>");
                    $("#leaderrow .leaderinitial.rank-" + rank).text(high_score.initials);
                    $("#leaderrow .leaderscore.rank-" + rank).text(score);
                });
            }
        });
    }

    function updateNewGameButton(is_game_joinable, game_joinable_countdown_s) {
        if (is_game_joinable) {
            $(".new-game").html("Join Game&nbsp;" + game_joinable_countdown_s.toString().padStart(2, "0"));
        } else {
            $(".new-game").html("New Game");
            $(".new-game").removeClass("disabled-button");
            setupNewGameButton();
        }
    }

    return {
        init: init,
        showLeaderboard: showLeaderboard,
        is_touch_device: is_touch_device
    };

})();