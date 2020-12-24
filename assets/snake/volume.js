var volume = (() => {

    var VOL_POLL_INTERVAL_MS = 1000;
    var is_vol_locked = false;
    var is_vol_lock_releasable = true;
    var vol_lock_marked_releasable_time = 0;

    // Polling might be setup at the app level if there are more pieces of data the app is interested in,
    // rather than being setup at the volume component level.
    function init(should_setup_polling) {
        if (should_setup_polling) {
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
        }

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

    function maybeUpdateVolume(vol_pct) {
        if (is_vol_locked && is_vol_lock_releasable) {
            var millis_since_vol_locked_marked_releasable = (new Date()).getTime() - vol_lock_marked_releasable_time;
            if (millis_since_vol_locked_marked_releasable > (VOL_POLL_INTERVAL_MS + 500)) {
                releaseVolMutex();
            }
        }

        if (is_vol_locked) {
            return;
        }

        vol_pct = Math.round(vol_pct);
        $('#volume').val(vol_pct);
        document.getElementById('volumeval').innerHTML = vol_pct;
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
        maybeUpdateVolume: maybeUpdateVolume,
    };

})();