var media_embed = {
    embed_type_map: {
        "rtmp": ["http", "jwplayer.rss"],
        "hls": ["http", "playlist.m3u8"],
        "vidtag": ["http", "playlist.m3u8"],
    },
    initialized: false,
    player_size: ["640", "360"],
    initialize: function(){
        var self = this;
        if (self.initialized){
            return;
        }
        self.data = {"base_url": "",
                     "app_name": "",
                     "stream_name": "",
                     "embed_type": "rtmp",
                     "stream_url": ""};
        $("input", $("#stream_input_fieldset")).change(function(){
            var $this = $(this);
            var key = $this.attr("id").split("_input")[0];
            self.data[key] = $this.val();
            self.buildUrl();
        });
        $("input", $("#embedtype_fieldset")).change(function(){
            var $this = $(this);
            self.data.embed_type = $this.val();
            self.buildUrl();
        });
        $("#stream_url_input").change(function(){
            var $this = $(this);
            var value = $this.val();
            if (value == ""){
                return;
            }
            if (!self.data.stream_url){
                return;
            }
            if (value == self.data.stream_url){
                return;
            }
            self.clearForm();
            self.data.stream_url = value;
            if ($this.val() != value){
                $this.val(value);
            }
        });
        $("#start-btn").on("click", function(){
            try{
                self.doEmbed();
            } catch (e){
                showDebug([e.fileName, e.lineNumber, e.message]);
            }
        });
        $("#stop-btn").on("click", function(){
            self.doStop();
        });
        $("#clear-btn").on("click", function(){
            self.clearForm();
        });
        self.loadJWScript();
        self.initialized = true;
    },
    loadJWScript: function(){
        var jsUrl = "http://jwpsrv.com/library/TOKEN.js";
        var tkUrl = "jwtoken.js"
        $.getScript(tkUrl, function(){
            jsUrl = jsUrl.replace("TOKEN", JWP_TOKEN);
            $.getScript(jsUrl);
        });
    },
    buildUrl: function(){
        var self = this;
        var url = self.data.stream_url;
        if (self.data.base_url != ""){

            url = self.embed_type_map[self.data.embed_type][0] + "://";
            url += [self.data.base_url,
                    self.data.app_name, "_definst_",
                    self.data.stream_name].join("/");
                    //self.embed_type_map[self.data.embed_type][1]].join("/");
            self.data.stream_url = url;
            $("#stream_url_input").val(url);
        }
    },
    clearForm: function(){
        var self = this;
        $.each(['stream_url', 'base_url', 'app_name', 'stream_name', 'embed_type'], function(i, key){
            var newData = "";
            var $elem = $("#" + key + "_fieldset");
            if (!$elem.length){
                $elem = $("#" + key + "_input");
            }
            if (key == 'embed_type'){
                newData = "rtmp"
            }
            self.data[key] = newData;
            $elem.val(newData);
        });
    },
    doEmbed: function(){
        var self = this;
        var container = $("#player-container");
        self.doStop();
        if (!self.data.stream_url){
            return;
        }
        if (MobileDetector.os == "android"){
            if (MobileDetector.browser == "Chrome"){
                var bversion = MobileDetector.browserVersion.split(".")[0]
                bversion = parseInt(bversion);
                if (bversion >= 34){
                    self.data.embed_type = "vidtag";
                    //container.append('<a href="URL">Click to Play</a>'.replace('URL', [self.data.stream_url, 'playlist.m3u8'].join('/')));
                }
            }
        }
        var player = $('<div id="player"></div>');
        container.append(player);
        if (self.data.embed_type != "vidtag"){
            jwplayer("player").setup({
                width: self.player_size[0],
                height: self.player_size[1],
                sources: [{
                    file: [self.data.stream_url, "jwplayer.smil"].join("/"),
                }, {
                    file: [self.data.stream_url, "playlist.m3u8"].join("/"),
                }],
                fallback: false,
            });
        } else {
            var vidtag = $('<video control="" autoplay="" name="player" id="player"></video>');
            vidtag.append('<source src="URL" type="application/vnd.apple.mpegurl">'.replace('URL', [self.data.stream_url, 'playlist.m3u8'].join('/')));
            container.append(vidtag);
        }
    },
    doStop: function(){
        if ($("div", $("#player-container")).length){
            $("#player-container").empty();
        }
    },
};

$("[data-role=page]").on("pagecreate", function(){
    media_embed.initialize();
});

$("form").submit(function(e){
    e.preventDefault();
});
