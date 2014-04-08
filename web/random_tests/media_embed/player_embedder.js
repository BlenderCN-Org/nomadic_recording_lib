
var playerEmbedder = {
    embed_methods: ['auto', 'videojs', 'strobe'],
    libRootUrls: {
        'videojs':'/videojs',
        'strobe':'/strobe-media',
    },
    cssUrls: [
        '//vjs.zencdn.net/4.5/video-js.css',
        //'_ROOTURL_STROBE_/jquery.strobemediaplayback.css',
    ],
    scriptUrls: [
        '//vjs.zencdn.net/4.5/video.js',
        '//ajax.googleapis.com/ajax/libs/swfobject/2.2/swfobject.js',
        //'_ROOTURL_VIDEOJS_/videojs.hls.min.js',
        '_ROOTURL_STROBE_/jquery.strobemediaplayback.js',
    ],
    formatLibUrl: function(url){
        var self = this;
        var replTxt = null;
        var lib = null;
        var libUrl = null;
        if (url.indexOf('_ROOTURL_') == -1){
            return url;
        }
        lib = url.split('_ROOTURL_')[1].split('_')[0];
        replTxt = ['', 'ROOTURL', lib, ''].join('_');
        libUrl = self.libRootUrls[lib.toLowerCase()];
        return url.replace(replTxt, libUrl);
    },
    loadSources: function(){
        var self = this;
        var cssComplete = false;
        var scriptsComplete = false;
        function loadCss(){
            var numResponse = 0;
            $.each(self.cssUrls, function(i, url){
                url = self.formatLibUrl(url);
                $.get(url, function(data){
                    var s = $('<style type="text/css"></style');
                    s.text(data);
                    $("body").append(s);
                    numResponse += 1;
                    if (numResponse == self.cssUrls.length){
                        $("body").trigger('player_embedder_css_loaded');
                    }
                });
            });
        }
        function loadJs(){
            var numResponse = 0;
            $.each(self.scriptUrls, function(i, url){
                url = self.formatLibUrl(url);
                $.getScript(url, function(){
                    numResponse += 1;
                    if (numResponse == self.scriptUrls.length){
                        $("body").trigger('player_embedder_scripts_loaded');
                    }
                });
            });
        }
        function doComplete(){
            if (cssComplete && scriptsComplete){
                $("body").trigger('player_embedder_sources_loaded');
            }
        }
        $("body").bind('player_embedder_css_loaded', function(){
            cssComplete = true;
            doComplete();
        });
        $("body").bind('player_embedder_scripts_loaded', function(){
            scriptsComplete = true;
            doComplete();
        });
        loadCss();
        loadJs();
    },
    streamSrc: function(base_url){
            var d = {};
            d.base_url = base_url
            d.hls_url = [base_url, 'playlist.m3u8'].join('/')
            d.hds_url = [base_url, 'manifest.f4m'].join('/')
            return d;
    },
    embedDataDefaults: {
        streamSrc: '',
        playerId: 'player',
        embed_method: 'auto',
        size: [640, 360],
        aspect_ratio: [16, 9],
        container: null,
        swfUrl: '_ROOTURL_STROBE_/StrobeMediaPlayback.swf',
        expressInstallSwfUrl: '_ROOTURL_STROBE_/expressInstall.swf',
    },
    embedData: function(data){
        d = {}
        $.each(playerEmbedder.embedDataDefaults, function(key, val){
            if (typeof(data[key]) != 'undefined'){
                val = data[key];
            }
            if (key == 'streamSrc'){
                val = playerEmbedder.streamSrc(val);
            } else if (key == 'swfUrl' || key == 'expressInstallSwfUrl'){
                val = playerEmbedder.formatLibUrl(val);
            }
            d[key] = val;
        });
        return d;
    },

    doEmbed: function(data){
        var self = this;
        var embed_fn = null;
        if (typeof(data) == 'string'){
            data = {'streamSrc':data};
        }
/*
        if (typeof(data.container.jquery) == 'undefined'){
            data.container = $(data.container);
            if (data.container.length == 0){
                data.container = $("#" + data.container);
            }
        }
*/
        if (typeof(data.container) == 'undefined'){
            data.container = $("body");
        }
        data = self.embedData(data);
        embed_fn = self['doEmbed_' + data.embed_method];
        embed_fn(data);
    },
    doEmbed_auto: function(data){
        var self = playerEmbedder;
        var vidtag = $('<video></video>');
        data.container.append(vidtag);
        if (vidtag[0].canPlayType('application/vnd.apple.mpegurl') != ''){
            self.doEmbed_videojs(data);
        } else {
            vidtag.remove();
            self.doEmbed_strobe(data);
        }
    },
    doEmbed_videojs: function(data){
        var vidtag = $("video", data.container);
        var opts = {
            'controls': true,
            'autoplay': true,
            'width':data.size[0].toString(),
            'height':data.size[1].toString(),
        };
        if (vidtag.length == 0){
            vidtag = $('<video></video>');
            data.container.append(vidtag);
        }
        vidtag.addClass('video-js vjs-default-skin');
        vidtag.attr('id', data.playerId);
        vidtag.append('<source src="URL" type="application/vnd.apple.mpegurl">'.replace('URL', data.streamSrc.hls_url));
        videojs(data.playerId, opts);
    },
    doEmbed_strobe: function(data){
        var opts = {
            'width': data.size[0],
            'height': data.size[1],
            'src': data.streamSrc.hds_url,
            'swf': data.swfUrl,
            'expressInstallSwfUrl':data.expressInstallSwfUrl,
        };
        var player = $('<div id="ID"></div>'.replace('ID', data.playerId));
        data.container.append(player);
        opts = $.fn.adaptiveexperienceconfigurator.adapt(opts);
        player.strobemediaplayback(strobeOpts);
    },
};