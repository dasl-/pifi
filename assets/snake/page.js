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

        $(document).keydown(function(e) {
            if(e.keyCode == 27) { // esc
                hideLeaderboard();
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
    }

    function showLeaderboard() {
        getHighScores();
        $(".leaderboard").fadeIn();
    }

    function hideLeaderboard() {
        $(".leaderboard").fadeOut();
    }

    function getHighScores() {
        $("#leaderrow").html("Loading...");
        $.get({
            url: "/api/get_high_scores",
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

    return {
        init: init,
        showLeaderboard: showLeaderboard
    };

})();