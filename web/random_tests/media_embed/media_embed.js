var media_embed = {
    initialize: function(){
        var self = this;
        self.data = {"base_url": "",
                     "app_name": "",
                     "stream_name": "",
                     "embed_type": "rtmp",
                     "stream_url": ""};
        $("input", $("#stream_input_fieldset")).change(function(){
            self.buildUrl();
        });
        $("input", $("#embedtype_fieldset")).change(function(){
            var $this = $(this);
            self.data.embedtype = $this.val();
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
            self.doEmbed();
        });
        $("#stop-btn").on("click", function(){
            self.doStop();
        });
        $("#clear-btn").on("click", function(){
            self.clearForm();
        });
    },
    buildUrl: function(){
        var self = this;
        var url = self.data.stream_url;
        if (self.data.base_url != ""){
            url = self.embed_type + "://";
            url += [self.data.base_url, self.data.app_name, "_definst_", self.data.stream_name].join("/");
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
        self.doStop();
        if (!self.data.stream_url){
            return;
        }

    },
    doStop: function(){

    },
};

$("[data-role=page]").on("pagecreate", function(){
    media_embed.initialize();
});