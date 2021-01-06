var snake_runner = (() => {

    var $new_game_button = $(".new-game");
    var is_new_game_request_in_progress = false;
    var last_new_game_request_finish_time = null; // see updateNewGameButton in page.js
    var new_game_promises, web_socket_connect_resolve, web_socket_connect_reject;
    var web_sockets = []; // web socket per player
    var player_counter = 0; // how many players are joined from this client
    var playlist_video_id = null;


    function newGame() {
        if (is_new_game_request_in_progress) {
            return;
        }

        is_new_game_request_in_progress = true;
        disableNewGameButton();
        new_game_promises = [];
        var num_players = $("#num_players").val();

        new_game_promises.push($.post({
            url: "/api/enqueue_or_join_game",
            data: JSON.stringify({
                title: 'snake',
                difficulty: $("#difficulty").val(),
                num_players: num_players
            })
        }));

        // TODO: confirm this still works with multiple websockets??
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
                    handle_new_game_promises_success(args[0], args[1], pending_web_socket);
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

    function handle_new_game_promises_success(enqueue_or_join_game_response, websocket_response, pending_web_socket) {
        var new_playlist_video_id = enqueue_or_join_game_response.playlist_video_id;
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
        if(message.message_type == "high_score") {
            unregisterEventListeners();
            high_score_inputter.enterInitials(message.score_id);
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
            $(document).on('keydown.snake-runner.player-' + player_index, function(e) {
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
            $(document).on('keydown.snake-runner.player-' + player_index + ".wasd", function(e) {
                var keyinput = e.keyCode;
                var direction;

                //WASD input
                if (keyinput == 87) { direction = 1; }
                if (keyinput == 83) { direction = 2; }
                if (keyinput == 65) { direction = 3; }
                if (keyinput == 68) { direction = 4; }

                if(direction) {
                    sendDirection(direction, player_index);
                }
            });
        } else if (player_index === 1) {
            // Unregister WASD from the first player
            $(document).off("keydown.snake-runner.player-0.wasd");

            // Keyboard input
            $(document).on('keydown.snake-runner.player-' + player_index, function(e) {
                var keyinput = e.keyCode;
                var direction;
                //WASD input
                if (keyinput == 87) { direction = 1; }
                if (keyinput == 83) { direction = 2; }
                if (keyinput == 65) { direction = 3; }
                if (keyinput == 68) { direction = 4; }

                if(direction) {
                    sendDirection(direction, player_index);
                }
            });
        }
    }

    function unregisterEventListeners() {
        // mouse input
        $(".quad").off("click");

        // Keyboard input
        $(document).off("keydown.snake-runner");

        // prevent memory leaks from the previous games' listeners hanging around?
        web_sockets.forEach(web_socket => {
            web_socket.close(1000, "closing because new game");
            web_socket.removeEventListener('open', onWebSocketOpen);
            web_socket.removeEventListener('close', onWebSocketClose);
            web_socket.removeEventListener('error', onWebSocketError);
            web_socket.removeEventListener('message', onWebSocketMessage);
        });
    }

    function sendDirection(direction, player_index) {
        console.log("yoyo");
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

    return {
        newGame: newGame,
        enableNewGameButton: enableNewGameButton,
        isNewGameRequestInProgress: isNewGameRequestInProgress,
        getLastNewGameRequestFinishTime: getLastNewGameRequestFinishTime
    };

})();
