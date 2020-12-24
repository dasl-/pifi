var snake_runner = (() => {

    var is_new_game_request_in_progress = false;
    var new_game_promises, web_socket_connect_resolve, web_socket_connect_reject;
    var web_socket = null;

    function newGame() {
        if (is_new_game_request_in_progress) {
            return;
        }

        is_new_game_request_in_progress = true;
        unregisterEventListeners();
        new_game_promises = [];

        new_game_promises.push($.post({
            url: "/api/enqueue_or_join_game",
            data: JSON.stringify({
                title: 'snake',
                difficulty: $("#difficulty").val(),
                num_players: $("#num_players").val()
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

        // prevent memory leaks from the previous games' listeners hanging around?
        if (web_socket) {
            web_socket.close(1000, "closing because new game");
            web_socket.removeEventListener('open', onWebSocketOpen);
            web_socket.removeEventListener('close', onWebSocketClose);
            web_socket.removeEventListener('error', onWebSocketError);
            web_socket.removeEventListener('message', onWebSocketMessage);
        }

        var pending_web_socket = new WebSocket(new_uri);
        pending_web_socket.addEventListener('open', onWebSocketOpen);
        pending_web_socket.addEventListener('close', onWebSocketClose);
        pending_web_socket.addEventListener('error', onWebSocketError);
        pending_web_socket.addEventListener('message', onWebSocketMessage);

        Promise.all(new_game_promises).then(
            function(args) {
                console.log("sending playlist_video_id: ", args[0].playlist_video_id);
                // Send the playlist_video_id we expect to the websocket to be connected to on the server for validation.
                pending_web_socket.send(JSON.stringify({
                    playlist_video_id: args[0].playlist_video_id,
                }));
                web_socket = pending_web_socket;
                is_new_game_request_in_progress = false;
                registerEventListeners();
            },
            function(err) {
                console.log("Error waiting for new game promises.", err);
                is_new_game_request_in_progress = false;
            }
        );
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

    function registerEventListeners() {
        // mouse input
        $(".quad").click(function() {
            var direction = $(this).data("direction");
            sendDirection(direction);
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

            //WASD input
            if (keyinput == 87) { direction = 1; }
            if (keyinput == 83) { direction = 2; }
            if (keyinput == 65) { direction = 3; }
            if (keyinput == 68) { direction = 4; }

            if(direction) {
                sendDirection(direction);
            }
        });
    }

    function unregisterEventListeners() {
        // mouse input
        $(".quad").off("click");

        // Keyboard input
        $(document).off("keydown.snake-runner");
    }

    function sendDirection(direction) {
        web_socket.send(direction);
        //change to pre-loaded images
        $(".button").css("background-image", "url('/assets/snake/snake.png')");
        $(".button[data-direction='" + direction + "']").css("background-image", "url('/assets/snake/snake-active.png')");
    }

    return {
        newGame: newGame
    };

})();
