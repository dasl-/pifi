var page = (() => {

    var POLL_INTERVAL_MS = 1000;

    var is_touch_device = 'ontouchstart' in document.documentElement;
    var is_poll_in_progress = false;
    var last_poll_start_time = null;
    var $new_game_button = $(".new-game");


    function init() {
        $(".initialcontainer").hide();
        $(".button-active").hide();

        if($('#num_players').val() == 1) {
            $(".multiplayer-option").hide();
        }

        setupUiHandlers();
        setupDifficultyInput();
        setupNumPlayersInput();
        setupAppleCountInput();

        volume.init(false);

        setupPolling();
    }

    function setupUiHandlers() {
        $new_game_button.click(function(){
            if ($new_game_button.hasClass("disabled-button")) {
                return;
            }
            snake_runner.newGameOrJoinGame();
        });

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

            var $multiplayer_winner_container = $(".multiplayer_winnerboard");
            if (!$multiplayer_winner_container.is(e.target) && $multiplayer_winner_container.has(e.target).length === 0){
                hideMultiplayerWinner();
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
                hideMultiplayerWinner();
            }
        });

        if ( is_touch_device ) {
            // do mobile handling
            $new_game_button.click(function() {
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
            if (this.value == 1) {
                $('.multiplayer-option').slideUp('fast');
            }
            else {
                $('.multiplayer-option').slideDown('fast');
            }
        });
        document.getElementById('num_players_val').innerHTML = document.getElementById('num_players').value;
    }

    function setupAppleCountInput() {
        $('#apple_count').on('input', function() {
            document.getElementById('apple_count_val').innerHTML = this.value;
        });
        document.getElementById('apple_count_val').innerHTML = document.getElementById('apple_count').value;
    }

    function setupPolling() {
        window.setInterval(
            function() {
                if (is_poll_in_progress) {
                    return;
                }
                is_poll_in_progress = true;
                last_poll_start_time = Math.round(Date.now() / 1000);
                $.get({
                    url: "/api/snake",
                })
                    .done(function(response) {
                        updateNewGameButton(response.is_game_joinable, response.game_joinable_countdown_s);
                        volume.maybeUpdateVolume(Math.round(response.vol_pct));
                    })
                    .always(function(response) {
                        is_poll_in_progress = false;
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

    function hideMultiplayerWinner() {
        $(".multiplayer_winnerboard").fadeOut();
        $(".multiplayer_winner").remove();
    }

    function hideSettingsDropdown() {
        $('.settings_dropdown').next("ul").hide("fast","swing");
    }

    function hideMenu() {
        $('.menu').hide("fast","swing");
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
                    var num_dots = 12 - (score.length - 3);
                    var dots = '.'.repeat(num_dots);
                    rank = index + 1;
                    $("#leaderrow").append("<li><span class='leaderinitial rank-" + rank + "'></span>" +
                        "<div class='scorespacer'>&nbsp;" + dots + "</div>" +
                        "<span class='leaderscore rank-" + rank + "'></span></li>");
                    $("#leaderrow .leaderinitial.rank-" + rank).text(high_score.initials);
                    $("#leaderrow .leaderscore.rank-" + rank).text(score);
                });
            }
        });
    }

    function updateNewGameButton(is_game_joinable, game_joinable_countdown_s) {
        if (is_game_joinable) {
            $new_game_button.html("Join Game&nbsp;" + game_joinable_countdown_s.toString().padStart(2, "0"));
        } else {
            $new_game_button.html("New Game");
            /*
                Prevent a race condition:
                1) new game button clicked, button is disabled, new game promise reuests are fired
                2) we wait for new game promises, JS event loop allows something else to execute meanwhile.
                3) snake polling api request fired (once per second)
                4) snake api request sees no game is joinable yet (i.e. new game button text should be "New Game" and it should be enabled)
                5) new game promise request from (1) updates the game to "joinable" on the server
                6) new game promises from (1) return, and they leave button disabled bc we have the max number of players for this client
                    (one player joined from mobile)
                7) snake api request from (3) returns, and we call updateNewGameButton
                    a) set button text to "new game"
                    b) if no new game request is in progressm, enable the button (there is no new game request in progress after (6))
                8) another snake polling api request is fired, returns, and updates the text to "Join Game" (it stays enabled)

                At the end of this, the button will say "Join Game", and it will be enabled, even if one player has already joined from
                the mobile client. This is because the polling snake api request info we based our enabling of the button on had
                information that was out of date by the time we got around to trying to enable the button. Since that information was
                obtained, a game was created and joinable. Thus, we add a check:

                    `last_poll_start_time > snake_runner.getLastNewGameRequestFinishTime()`

                This ensures we only update based on our polling info if the polling info is more recent than whenever the last time
                someone clicked and finished executing the "New Game" button logic.
             */
            if (!snake_runner.isNewGameRequestInProgress() && last_poll_start_time > snake_runner.getLastNewGameRequestFinishTime()) {
                snake_runner.enableNewGameButton();
            }
        }
    }

    return {
        init: init,
        showLeaderboard: showLeaderboard,
        is_touch_device: is_touch_device
    };

})();