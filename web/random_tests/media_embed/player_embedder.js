
var playerEmbedder = {
    embed_methods: ['auto', 'videojs', 'strobe'],
    cssUrls: {
        'videojs':'//vjs.zencdn.net/4.5/video-js.css',
        'strobe':'strobe-media/jquery.strobemediaplayback.css',
    },
    scriptUrls: {
        'videojs':'//vjs.zencdn.net/4.5/video.js',
        'swfobject':'//ajax.googleapis.com/ajax/libs/swfobject/2.2/swfobject.js',
        'strobe':'strobe-media/jquery.strobemediaplayback.js',
    },
    streamSrc: function(base_url){
            var d = {};
            d.base_url = base_url
            d.hls_url = [base_url, 'playlist.m3u8'].join('/')
            d.hds_url = [base_url, 'manifest.f4m'].join('/')
            return d;
        }
    },
    embedDataDefaults: {
        streamSrc: '',
        playerId: 'player',
        embed_method: 'auto',
        size: [640, 360],
        aspect_ratio: [16, 9],
        container: null,
        swfUrl: 'strobe-media/StrobeMediaPlayback.swf',
        expressInstallSwfUrl: 'strobe-media/expressInstall.swf',
    },
    embedData: function(data){
        d = {}
        $.each(playerEmbedder.embedDataDefaults, function(key, val){
            if (typeof(data[key]) != 'undefined'){
                val = data[key];
            }
            if (key == 'streamSrc'){
                val = playerEmbedder.streamSrc(val);
            }
            d[key] = val;
        });
        return d;
    },

    doEmbed: function(data){
        var self = this;
        data = self.embedData(data);
        if (typeof(data.container.jquery) == 'undefined'){
            data.container = $(data.container);
            if (data.container.length == 0){
                data.container = $("#" + data.container);
            }
        }

    },
    doEmbed_auto: function(data){
        var self = this;
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