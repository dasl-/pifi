//HIGH SCORE INITIAL INPUT
var high_score_inputter = (() => {

    var score_id;

        //alphabet array
    var alpha = ["A", "B", "C", "D", "E", "F", "G", "H",
                "I", "J", "K", "L", "M", "N", "O", "P",
                "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"];
    var letterlist = "";

    for (var i = 0; i < alpha.length; i++) {
        letterlist += "<span>" + alpha[i] + "</span>";
    }

    //populate letters into div
    $(".initiallist").html(letterlist);

    //height of letter in pixels
    var letteroffset = 102;

    //remove units from CSS values
    function CSSnum(value) {
        return Number(value.replace(/[^-\d\.]/g, ''));
    }

    function enterInitials(_score_id) {
        $(".initialcontainer").show();
        $("#init1").focus();
        registerEventListeners();
        score_id = _score_id;
        $(".initiallist").css("top", "0");
    }


    //move through letters in list
    function LetterScroll(list, direction, offset) {
    	var currentoffset;
    	var newoffset;
    	//finish animating previous scroll
    	list.finish();
    	//get current css value of top of letter list
    	currentoffset = CSSnum(list.css("top"));
    	if(direction == "up") {
    		if(currentoffset < 0) {
    			newoffset = (currentoffset + offset) + "px";
    		}
    	}
    	else if(direction == "down") {
    		if(currentoffset > -(offset*25)) {
    			newoffset = (currentoffset - offset) + "px";
    		}
    	}
    	else {
    		console.log(direction + "is not a valid direction");
    		return;
    	}
    	if(newoffset) {
    		list.animate({top: newoffset}, "swing");
    	}
    }

    //find alphabet letter from list
    function FindLetter(list) {
    	//make sure list has finished animating
    	list.finish();
    	offset = -(CSSnum(list.css("top")));
    	//divide current offset by height of letter to find numerical value of letter
    	letternum = offset / letteroffset;
    	//check if number is an integer and within alphabet range
    	if(Number.isInteger(letternum) && letternum >= 0 && letternum < 26) {
    		return alpha[letternum];
    	}
    }

    function registerEventListeners() {
    	//scroll through letters on click
    	$(".arrowup").click(function() {
    		var init = $(this).next(".initialinput").find(".initiallist");
    		LetterScroll(init, "up", letteroffset);
    	});

    	$(".arrowdown").click(function() {
    		var init = $(this).prev(".initialinput").find(".initiallist");
    		LetterScroll(init, "down", letteroffset);
    	});

    	//keyboard input
    	$(document).on('keydown.high-score-inputter', function(e) {
            var $focused = $(':focus');
            if (!$focused.hasClass('high-score-input-focusable')) {
                return;
            }

            var keyinput = e.keyCode;

         	//Move left and right
    		if(keyinput == 39) {
    			$focused.next().focus();
    		}
    		if(keyinput == 37) {
    			$focused.prev().focus();
    		}

            if ($focused.hasClass('initwrap')) {
                //Scroll through letters with up and down
                var list = $focused.find(".initiallist");
                if (keyinput == 38) {
                    LetterScroll(list, "up", letteroffset);
                    $focused.find(".arrowup").css("bottom","3px");
                    $focused.keyup(function(e) {
                        $focused.find(".arrowup").css("bottom","unset");
                    });
                }
                if (keyinput == 40) {
                    LetterScroll(list, "down", letteroffset);
                    $focused.find(".arrowdown").css("top","3px");
                    $focused.keyup(function(e) {
                        $focused.find(".arrowdown").css("top","unset");
                    });
                }
            }

        	//submit on enter key
        	if (keyinput == 13) {
        		$(".enterinit").click();
        	}
    	});

        //Submit initials
        $(".enterinit").click(function() {
            unregisterEventListeners();
            var init1 = FindLetter($("#init1").find(".initiallist"));
            var init2 = FindLetter($("#init2").find(".initiallist"));
            var init3 = FindLetter($("#init3").find(".initiallist"));
            var initials = init1 + init2 + init3;
            $.post({
                url: "/api/submit_game_score_initials",
                data: JSON.stringify({
                    score_id: score_id,
                    initials: initials
                }),
                success: function() {
                    $(".initialcontainer").hide();
                    page.showLeaderboard();
                }
            });
        });
    }

    function unregisterEventListeners() {
        // mouse input
        $(".arrowup").off("click");
        $(".arrowdown").off("click");
        $(".enterinit").off("click");

        // Keyboard input
        $(document).off("keydown.high-score-inputter");
    }

    return {
        enterInitials: enterInitials
    };

})();