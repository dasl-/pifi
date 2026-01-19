var pong_page = (() => {

    var is_touch_device = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

    function init() {

        // Initialize volume from server
        $.get("/api/vol_pct", function(data) {
            $("#volume").val(data.vol_pct);
            $("#volumeval").text(data.vol_pct);
        });

        // Set up event listeners
        setupEventListeners();

        // Update settings display
        updateSettingsDisplay();

        // Show touch controls on mobile
        if (is_touch_device) {
            $(".touch-controls").show();
            $(".control-hint").hide();
        } else {
            $(".touch-controls").hide();
            $(".control-hint").show();
        }
    }

    function setupEventListeners() {
        // New game button
        $(".new-game").click(function() {
            if (!$(this).hasClass("disabled-button")) {
                pong_runner.newGameOrJoinGame();
            }
        });

        // Menu toggle
        $(".menubutton").click(function() {
            $(".menu").slideToggle();
        });

        // Settings dropdown
        $(".settings_dropdown").click(function(e) {
            e.preventDefault();
            $(this).siblings("ul").slideToggle();
        });

        // Volume slider
        $("#volume").on("input", function() {
            var vol = $(this).val();
            $("#volumeval").text(vol);
            $.post("/api/vol_pct", JSON.stringify({ vol_pct: vol }));
        });

        // Difficulty slider
        $("#difficulty").on("input", function() {
            updateSettingsDisplay();
        });

        // Target score slider
        $("#target_score").on("input", function() {
            updateSettingsDisplay();
        });

        // Close menu when clicking outside
        $(document).click(function(e) {
            if (!$(e.target).closest('.menu-container').length) {
                $(".menu").slideUp();
            }
        });

        // Keyboard shortcuts
        $(document).keydown(function(e) {
            // Escape to toggle menu
            if (e.keyCode === 27) {
                $(".menu").slideToggle();
            }
            // Enter/Space to start new game when button is enabled
            if ((e.keyCode === 13 || e.keyCode === 32) && !$(".new-game").hasClass("disabled-button")) {
                if (!$(e.target).is('input')) {
                    e.preventDefault();
                    pong_runner.newGameOrJoinGame();
                }
            }
        });
    }

    function updateSettingsDisplay() {
        $("#difficultyval").text($("#difficulty").val());
        $("#target_score_val").text($("#target_score").val());
    }

    return {
        init: init,
        is_touch_device: is_touch_device
    };

})();
