var snake_runner = (() => {

    var $new_game_button = $(".new-game");
    var is_new_game_request_in_progress = false;
    var last_new_game_request_finish_time = null; // see updateNewGameButton in page.js
    var web_socket_connect_resolve, web_socket_connect_reject;
    var web_sockets = []; // web socket per player
    var player_counter = 0; // how many players are joined from this client
    var playlist_video_id = null;


    function newGameOrJoinGame() {
        if (is_new_game_request_in_progress) {
            return;
        }

        is_new_game_request_in_progress = true;
        disableNewGameButton();
        var new_game_promises = [];
        var num_players = $("#num_players").val();

        new_game_promises.push($.post({
            url: "/api/enqueue_or_join_game",
            data: JSON.stringify({
                title: 'snake',
                difficulty: $("#difficulty").val(),
                num_players: num_players,
                apple_count: $("#apple_count").val()
            })
        }));

        new_game_promises.push(new Promise(function(resolve, reject) {
            web_socket_connect_resolve = resolve;
            web_socket_connect_reject = reject;
        }));

        var new_uri;
        if (window.location.protocol === "https:") {
            new_uri = "wss:";
        } else {
            new_uri = "ws:";
        }
        new_uri += "//" + window.location.hostname + ":8765/";

        var pending_web_socket = new WebSocket(new_uri);
        pending_web_socket.addEventListener('open', onWebSocketOpen);
        pending_web_socket.addEventListener('close', onWebSocketClose);
        pending_web_socket.addEventListener('error', onWebSocketError);
        pending_web_socket.addEventListener('message', onWebSocketMessage);

        Promise.all(new_game_promises)
            .then(
                function(args) {
                    handleNewGamePromisesSuccess(
                        args[0], args[1], pending_web_socket
                    );
                },
                function(err) {
                    console.log("Error waiting for new game promises.", err);
                    enableNewGameButton();
                }
            )
            .finally(function() {
                last_new_game_request_finish_time = Math.round(Date.now() / 1000);
                is_new_game_request_in_progress = false;
            });
    }

    function handleNewGamePromisesSuccess(
        enqueue_or_join_game_response, websocket_response, pending_web_socket
    ) {
        var new_playlist_video_id = enqueue_or_join_game_response.playlist_video_id;
        var num_players = enqueue_or_join_game_response.num_players;
        if (playlist_video_id !== new_playlist_video_id) {
            // This client is starting / joining a game that it hasn't been a part of before
            playlist_video_id = new_playlist_video_id;
            unregisterEventListeners();
            player_counter = 0;
            web_sockets = [];
        }

        // Send the playlist_video_id we expect to the websocket to be connected to on the server for validation.
        console.log("sending playlist_video_id: ", playlist_video_id);
        pending_web_socket.send(JSON.stringify({
            playlist_video_id: playlist_video_id,
        }));
        web_sockets[player_counter] = pending_web_socket;
        registerEventListeners(player_counter);
        player_counter += 1;
        if(player_counter == 1) {
            // Only necessary to do this once, even if two players are joining from a single browser, hence the player_counter check.
            var apple_count = enqueue_or_join_game_response.apple_count;
            setupScores(num_players, apple_count);
        }
        if((player_counter >= 2 && !page.is_touch_device) ||
            (player_counter >= 1 && page.is_touch_device)
        ) {
            // Keep the new game button disabled to prevent it from showing a multiplayer game as "joinable"
            // even after the max number of players has joined from this client. In multiplayer games, mobile
            // clients support one player joining from the device, and desktop clients support two players
            // joining from the device. The polling in page.js will re-enable it eventually.
        } else {
            enableNewGameButton();
        }
    }

    function onWebSocketOpen(event) {
        console.log("WebSocket is open.");
        web_socket_connect_resolve("websocket opened");
    }

    function onWebSocketError(event) {
        console.log("WebSocket errored.");
        web_socket_connect_reject("websocket errored");
    }

    function onWebSocketClose(event) {
        console.log("WebSocket is closed.");
    }

    function onWebSocketMessage(event) {
        var message = JSON.parse(event.data);
        switch (message.message_type) {
            case 'high_score':
                // unregister keyboard listeners so we can use them for initial inputter
                unregisterEventListeners();
                high_score_inputter.enterInitials(message.score_id);
                break;
            case 'multi_player_score':
                // Scores are sent to each player's websocket. Thus in a multiplayer game where two players have joined from a single
                // browser, scores will be updated with identical values twice. Oh well, nbd.
                $("#apple-scoring").text(message.apples_left);
                /* falls through */
            case 'single_player_score':
                message.player_scores.forEach(function(score, player_index) {
                    var player = player_index + 1;
                    $("#p" + player + "-score").text(score);
                });
                break;
            case 'player_index_message':
                // At game start, server sends client a message telling them what player number they are. This allows the
                // client to place a marker on the scoreboard next to their player number
                var player = message.player_index + 1;
                $("dt.p" + player + "-color").css("border-left", "2px solid");
                break;
            case 'multi_player_winners':
                //Display winner at end of game
                //Check first if winners have already been displayed
                if($(".winner").length != 0) {
                    break;
                }
                winner_data = "";
                $(".winnerboard").fadeIn();
                message.winners.forEach(winner => {
                    winner_data += "<div class='winner'>P" + (winner + 1) + "</div>";
                });
                $(".winnerboard").append(winner_data);
                if(message.winners.length > 1) {
                    var font_size = Math.round(4 / message.winners.length) + "em";
                    $(".winner").css("font-size", font_size);
                }
                break;
        }
    }

    function registerEventListeners(player_index) {
        if (player_index === 0) {
            // mouse input
            $(".quad").click(function() {
                var direction = $(this).data("direction");
                sendDirection(direction, player_index);
            });

            // Keyboard input
            $(document).on('keydown.snake-runner', function(e) {
                var keyinput = e.keyCode;
                var direction;
                //Arrow key input
                if (keyinput == 38) { direction = 1; }
                if (keyinput == 40) { direction = 2; }
                if (keyinput == 37) { direction = 3; }
                if (keyinput == 39) { direction = 4; }

                if(direction) {
                    sendDirection(direction, player_index);
                }
            });
        } else if (player_index === 1) {
            // Unregister WASD from the first player
            $(document).off("keydown.snake-runner.wasd");
        }

        // register WASD
        $(document).on('keydown.snake-runner.wasd', function(e) {
            var keyinput = e.keyCode;
            var direction;

            if (keyinput == 87) { direction = 1; }
            if (keyinput == 83) { direction = 2; }
            if (keyinput == 65) { direction = 3; }
            if (keyinput == 68) { direction = 4; }

            if(direction) {
                sendDirection(direction, player_index);
            }
        });
    }

    function unregisterEventListeners() {
        // mouse input
        $(".quad").off("click");

        // Keyboard input
        $(document).off("keydown.snake-runner");

        // prevent memory leaks from the previous games' listeners hanging around?
        web_sockets.forEach(web_socket => {
            web_socket.close(1000, "closing because new game or high score");
            web_socket.removeEventListener('open', onWebSocketOpen);
            web_socket.removeEventListener('close', onWebSocketClose);
            web_socket.removeEventListener('error', onWebSocketError);
            web_socket.removeEventListener('message', onWebSocketMessage);
        });
    }

    function sendDirection(direction, player_index) {
        web_sockets[player_index].send(direction);
        if (player_index === 0) {
            $(".button-active").hide();
            $(".button-active[data-direction='" + direction + "']").show();
        }
    }

    function enableNewGameButton() {
        $new_game_button.removeClass("disabled-button");
    }

    function disableNewGameButton() {
        $new_game_button.addClass("disabled-button");
    }

    function isNewGameRequestInProgress() {
        return is_new_game_request_in_progress;
    }

    function getLastNewGameRequestFinishTime() {
        return last_new_game_request_finish_time;
    }

    function setupScores(num_players, apple_count) {
        $(".playerscore").remove();
        if(num_players > 1) {
            $("#singleplayer-scores").hide();
            var player_content = "";
            $("#multiplayer-scores").fadeIn().css("display", "grid");
            $("#multiplayer-scores .playerscore").remove();
            for (var i = 1; i <= num_players; i++) {
                player_content += "<dt class='p" + i + "-color playerscore'>P" + i +  "</dt>" +
                    "<dd id='p" + i + "-score' class='p" + i +"-color playerscore'>0</dd>";
            }
            $("#multiplayer-scores").prepend(player_content);
            $("#apple-scoring").text(apple_count);
        }
        else {
            $("#multiplayer-scores").hide();
            $("#singleplayer-scores").fadeIn().css("display", "grid");
            $("#singleplayer-scores").append("<dd id='p1-score' class='playerscore'>0</dd>");
        }
    }

    return {
        newGameOrJoinGame: newGameOrJoinGame,
        enableNewGameButton: enableNewGameButton,
        isNewGameRequestInProgress: isNewGameRequestInProgress,
        getLastNewGameRequestFinishTime: getLastNewGameRequestFinishTime
    };

})();
