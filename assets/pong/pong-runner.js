var pong_runner = (() => {

    var $new_game_button = $(".new-game");
    var is_new_game_request_in_progress = false;
    var last_new_game_request_finish_time = null;
    var web_socket_connect_resolve, web_socket_connect_reject;
    var web_sockets = [];
    var player_counter = 0;
    var playlist_video_id = null;
    var my_player_index = null;

    function newGameOrJoinGame() {
        if (is_new_game_request_in_progress) {
            return;
        }

        is_new_game_request_in_progress = true;
        disableNewGameButton();
        $(".waiting-message").fadeIn();
        $(".winner-display").hide();

        var new_game_promises = [];

        new_game_promises.push($.post({
            url: "/api/enqueue_or_join_game",
            data: JSON.stringify({
                title: 'pong',
                difficulty: $("#difficulty").val(),
                target_score: $("#target_score").val()
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
                    handleNewGamePromisesSuccess(args[0], args[1], pending_web_socket);
                },
                function(err) {
                    console.log("Error waiting for new game promises.", err);
                    enableNewGameButton();
                    $(".waiting-message").hide();
                }
            )
            .finally(function() {
                last_new_game_request_finish_time = Math.round(Date.now() / 1000);
                is_new_game_request_in_progress = false;
            });
    }

    function handleNewGamePromisesSuccess(enqueue_or_join_game_response, websocket_response, pending_web_socket) {
        var new_playlist_video_id = enqueue_or_join_game_response.playlist_video_id;

        if (playlist_video_id !== new_playlist_video_id) {
            playlist_video_id = new_playlist_video_id;
            unregisterEventListeners();
            player_counter = 0;
            web_sockets = [];
            my_player_index = null;
        }

        console.log("Sending playlist_video_id:", playlist_video_id);
        pending_web_socket.send(JSON.stringify({
            playlist_video_id: playlist_video_id,
        }));

        web_sockets[player_counter] = pending_web_socket;
        my_player_index = player_counter;
        registerEventListeners(player_counter);
        player_counter += 1;

        // Update UI to show which player you are
        updatePlayerIndicator();

        // Highlight your score
        highlightPlayerScores();

        // Reset scores display (only on first join)
        if (player_counter === 1) {
            $("#p1-score").text("0");
            $("#p2-score").text("0");
        }

        // Re-enable button if we haven't reached max local players yet
        // Desktop: allow 2 players, Mobile: allow 1 player
        if ((player_counter >= 2 && !pong_page.is_touch_device) ||
            (player_counter >= 1 && pong_page.is_touch_device)
        ) {
            // Keep button disabled - max players joined from this device
        } else {
            enableNewGameButton();
        }
    }

    function onWebSocketOpen(event) {
        console.log("WebSocket is open.");
        web_socket_connect_resolve("websocket opened");
        $(".waiting-message").text("Connected! Waiting for game to start...");
    }

    function onWebSocketError(event) {
        console.log("WebSocket errored.");
        web_socket_connect_reject("websocket errored");
    }

    function onWebSocketClose(event) {
        console.log("WebSocket is closed.");
        $(".waiting-message").hide();
        enableNewGameButton();
    }

    function onWebSocketMessage(event) {
        var message = JSON.parse(event.data);
        console.log("Received message:", message);

        switch (message.message_type) {
            case 'score_update':
                $(".waiting-message").hide();
                $("#p1-score").text(message.scores[0]);
                $("#p2-score").text(message.scores[1]);
                break;

            case 'game_over':
                var winner = message.winner;
                var winner_text;

                // If both players are local, show who won without YOU WIN/YOU LOSE
                if (player_counter >= 2) {
                    winner_text = "PLAYER " + (winner + 1) + " WINS!";
                    $(".winner-display").addClass("victory");
                } else if (winner === my_player_index) {
                    winner_text = "YOU WIN!";
                    $(".winner-display").addClass("victory");
                } else {
                    winner_text = "YOU LOSE";
                    $(".winner-display").removeClass("victory");
                }
                $(".winner-text").text(winner_text);
                $(".winner-display").fadeIn();

                // Show final scores
                $("#p1-score").text(message.scores[0]);
                $("#p2-score").text(message.scores[1]);

                // Re-enable new game button
                enableNewGameButton();
                break;

            case 'player_index_message':
                // This message is sent when joining a game in progress
                // For new games, player index is set in handleNewGamePromisesSuccess
                my_player_index = message.player_index;
                updatePlayerIndicator();
                highlightPlayerScores();
                break;
        }
    }

    function registerEventListeners(player_index) {
        if (player_index === 0) {
            // Player 1: W/S keys and arrow keys
            $(document).on('keydown.pong-runner.player0', function(e) {
                var keyCode = e.keyCode;
                var direction = null;

                if (keyCode === 87) { direction = 'up'; }   // W
                if (keyCode === 83) { direction = 'down'; } // S
                if (keyCode === 38) { direction = 'up'; }   // Up arrow
                if (keyCode === 40) { direction = 'down'; } // Down arrow

                if (direction) {
                    e.preventDefault();
                    sendDirection(direction, player_index);
                }
            });

            // Touch controls for player 1 (left zone)
            $(".left-zone .touch-button").on("touchstart.pong-runner.player0 mousedown.pong-runner.player0", function(e) {
                e.preventDefault();
                var direction = $(this).data("direction");
                sendDirection(direction, player_index);
            });
        } else if (player_index === 1) {
            // Player 2 joins - need to unregister arrow keys from player 0 and use them for player 1
            $(document).off('keydown.pong-runner.player0');

            // Re-register player 0 with only W/S
            $(document).on('keydown.pong-runner.player0', function(e) {
                var keyCode = e.keyCode;
                var direction = null;

                if (keyCode === 87) { direction = 'up'; }   // W
                if (keyCode === 83) { direction = 'down'; } // S

                if (direction) {
                    e.preventDefault();
                    sendDirection(direction, 0);
                }
            });

            // Register player 1 with arrow keys
            $(document).on('keydown.pong-runner.player1', function(e) {
                var keyCode = e.keyCode;
                var direction = null;

                if (keyCode === 38) { direction = 'up'; }   // Up arrow
                if (keyCode === 40) { direction = 'down'; } // Down arrow

                if (direction) {
                    e.preventDefault();
                    sendDirection(direction, player_index);
                }
            });

            // Touch controls for player 2 (right zone)
            $(".right-zone .touch-button").on("touchstart.pong-runner.player1 mousedown.pong-runner.player1", function(e) {
                e.preventDefault();
                var direction = $(this).data("direction");
                sendDirection(direction, player_index);
            });
        }
    }

    function unregisterEventListeners() {
        $(document).off("keydown.pong-runner.player0");
        $(document).off("keydown.pong-runner.player1");
        $(".touch-button").off("touchstart.pong-runner.player0 mousedown.pong-runner.player0");
        $(".touch-button").off("touchstart.pong-runner.player1 mousedown.pong-runner.player1");

        web_sockets.forEach(web_socket => {
            if (web_socket && web_socket.readyState === WebSocket.OPEN) {
                web_socket.close(1000, "closing for new game");
            }
        });
    }

    function sendDirection(direction, player_index) {
        var socket = web_sockets[player_index];
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(direction + ' ' + (new Date() / 1000));

            // Visual feedback
            $(".touch-button[data-direction='" + direction + "']").addClass("active");
            setTimeout(function() {
                $(".touch-button[data-direction='" + direction + "']").removeClass("active");
            }, 100);
        }
    }

    function updatePlayerIndicator() {
        var indicator_text = "";
        if (player_counter === 1) {
            indicator_text = "You are Player " + (my_player_index + 1);
        } else if (player_counter === 2) {
            indicator_text = "You are both players (local 2P)";
        }
        $(".player-indicator").text(indicator_text).fadeIn();
    }

    function highlightPlayerScores() {
        // Highlight all local players' scores
        for (var i = 0; i < player_counter; i++) {
            if (i === 0) {
                $(".player1-score").addClass("my-score");
            } else if (i === 1) {
                $(".player2-score").addClass("my-score");
            }
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

    return {
        newGameOrJoinGame: newGameOrJoinGame,
        enableNewGameButton: enableNewGameButton,
        isNewGameRequestInProgress: isNewGameRequestInProgress,
        getLastNewGameRequestFinishTime: getLastNewGameRequestFinishTime
    };

})();
