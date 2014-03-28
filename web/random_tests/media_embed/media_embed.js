var media_embed = {
    embed_type_map: {
        "rtmp": ["http", "jwplayer.rss"],
        "hls": ["http", "playlist.m3u8"],
        "vidtag": ["http", "playlist.m3u8"],
    },
    initialized: false,
    player_size: [640, 360],
    player_max_width: 1280,
    aspect_ratio: [16, 9],
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
        $("input", $("#stream_input_fieldset")).on('keyup focusout', function(){
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
        $("#stream_url_input").on('keyup focusout', function(){
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
        $(window).on("orientationchange", function(){
            var player = null;
            self.player_size = self.calcPlayerSize();
            if (!$("#player").length){
                return;
            }
            if ($("video").length){
                player = $("video");
                player.width(self.player_size[0].toString() + 'px');
                player.height(self.player_size[1].toString() + 'px');
            }
        });
        self.loadJWScript();
        self.displayMediaSupport();
        self.initialized = true;
    },
    loadJWScript: function(){
        // jwtoken.js must declare the var "JWP_TOKEN" as is required by jwplayer6
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
            //$("#stream_url_input").val(url);
        }
        self.updateFormFields();
    },
    updateFormFields: function(){
        var self = this;
        $.each(self.data, function(key, val){
            var $elem = $("[name=KEY]".replace('KEY', key));
            if (key == 'embed_type'){
                $("[value=VAL]".replace('VAL', val), $elem).trigger('click');
                $elem.checkboxradio('refresh');
            }
            if (!$elem.length){
                return;
            }
            if ($elem.val() == val){
                return;
            }
            $elem.val(val);
        });
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
            var androidMethodSet = false;
            if (MobileDetector.browser == "Chrome"){
                var bversion = MobileDetector.browserVersion.split(".")[0]
                bversion = parseInt(bversion);
                if (bversion >= 34){
                    self.data.embed_type = "vidtag";
                    self.updateFormFields();
                    androidMethodSet = true;
                    //container.append('<a href="URL">Click to Play</a>'.replace('URL', [self.data.stream_url, 'playlist.m3u8'].join('/')));
                }
            }
            if (!androidMethodSet){
                self.insertAndroidFallbacks(container);
            }
        }
        var player = $('<div id="player"></div>');
        container.append(player);
        self.player_size = self.calcPlayerSize();
        if (self.data.embed_type != "vidtag"){
            jwplayer("player").setup({
                width: self.player_size[0].toString(),
                height: self.player_size[1].toString(),
                sources: [{
                    file: [self.data.stream_url, "jwplayer.smil"].join("/"),
                }, {
                    file: [self.data.stream_url, "playlist.m3u8"].join("/"),
                }],
                fallback: false,
            });
        } else {
            var vidtag = $('<video controls="true" autoplay="true"></video>');
            vidtag.append('<source src="URL" type="application/vnd.apple.mpegurl">'.replace('URL', [self.data.stream_url, 'playlist.m3u8'].join('/')));
            container.append(vidtag);
            vidtag.width(self.player_size[0].toString() + 'px');
            vidtag.height(self.player_size[1].toString() + 'px');
            vidtag[0].load();
        }
    },
    doStop: function(){
        if ($("div", $("#player-container")).length){
            $("#player-container").empty();
        }
    },
    calcPlayerSize: function(container){
        if (typeof(container) == "undefined"){
            container = $("#player-container");
        }
        var self = this;
        var complete = null;
        var x = container.innerWidth();
        var xMin = x * 0.5;
        var y = null;
        var ratio = self.aspect_ratio[0] / self.aspect_ratio[1];
        function integersFound(_x, _y){
            if (Math.floor(_x) != _x){
                return false;
            }
            if (Math.floor(_y) != _y){
                return false;
            }
        }
        y = x / ratio;
        complete = integersFound(x, y);
        while (!complete){
            x -= 1;
            y = x / ratio;
            complete = integersFound(x, y);
            if (!complete && x <=xMin){
                x = container.innerWidth();
                y = x / ratio;
                y = Math.floor(y);
                break;
            }
        }
        return [x, y];
    },
    insertAndroidFallbacks: function(container){
        var self = this;
        var rtspUrl = self.data.stream_url;
        var hlsUrl = [self.data.stream_url, 'playlist.m3u8'].join('/');
        rtspUrl = ['rtsp', rtspUrl.split('://')[1]].join('://');
        container.append('<p><a href="RTSPURL">Click to watch using RTSP</a></p>'.replace('RTSPURL', rtspUrl));
        container.append('<p><a href="HLSURL">Click to watch using HLS</a></p>'.replace('HLSURL', hlsUrl));
    },
    displayMediaSupport: function(container){
        var vidElem, mimeTypes, tableDiv, tblHead, tblBody;
        mimeTypes = ['application/x-mpegurl', 'application/vnd.apple.mpegurl'];
        if (typeof(container) == "undefined"){
            container = $("[data-role=content]");
        }
        vidElem = $('<video id="video-test-element"></video>');
        container.append(vidElem);
        tableDiv = $('<table data-role="table" id="media-support-table"><thead></thead><tbody></tbody></table>');
        container.append(tableDiv);
        tblHead = $("thead", tableDiv);
        tblBody = $("tbody", tableDiv);
        tblHead.append('<tr><th>MIME Type</th><th>Support</th></tr>');
        $.each(mimeTypes, function(i, mType){
            var row = $('<tr></tr>');
            var supportStr = vidElem[0].canPlayType(mType);
            row.append('<td>M</td>'.replace('M', mType));
            row.append('<td>R</td>'.replace('R', supportStr));
            tblBody.append(row);
        });
        vidElem.remove();
        tableDiv.table();
    },
};

$("[data-role=page]").on("pagecreate", function(){
    media_embed.initialize();
});

$("form").submit(function(e){
    e.preventDefault();
});
