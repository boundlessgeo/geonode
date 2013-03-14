/**
 * Copyright (c) 2012 OpenGeo
 *
 */

Ext.ns("GeoExplorer");

GeoExplorer.PlaybackToolbar = Ext.extend(gxp.PlaybackToolbar,{
    playbackMode: 'ranged',    
    /* i18n */
    prevTooltip: 'Reverse One Frame',
    
    fullSizeTooltip: 'Fullscreen',
    
    smallSizeTooltip: 'Back to Smaller Size',
    
    legendTooltip: 'Show Map Legend',
    
    editTooltip: 'Edit This Map',

    overlayNodeText: "Storylayers",

    legendOffsetY: 93,
    
    initComponent: function() {

        if(!this.playbackActions){
            this.playbackActions = [
                "play","slider","loop","fastforward","prev","next",
                {xtype: "tbspacer"},"legend",{xtype:"tbfill"},
                "settings",{xtype: "tbspacer"},"togglesize","edit"]; 
        }
        this.defaults = Ext.applyIf(this.defaults || {},{
            scale: 'large'
        });
        if(this.playbackActions.indexOf('legend')>-1){
            this.layerManager = this.addLayerManager();    
        }
        this.aggressive = (window.location.href.match(/view|new/)===null);

        // if the app is in the fullscreen mode we want to show the
        // legend
        if (app.fullScreen) {
            this.toggleLegend(null, true);
        }

        app.on('toggleSize', function (fullScreen) {
            this.setToggleButton(fullScreen);
        }, this);

        // TODO, We use a delay here because we have to wait until the
        // portal is the correct size in order to resize the legend
        // This is a hacked, ideally we would not need this delay
        app.portal.on('resize', function (event) {
            // using the lastSize seems wrong as from what I can tell
            // the last size is actually the size that the panel is
            // going into.
            this.resizeLegend(event.lastSize.height);
        }, this, {delay: 100});

        GeoExplorer.PlaybackToolbar.superclass.initComponent.call(this);
    },

    getAvailableTools:function(){
        var tools = GeoExplorer.PlaybackToolbar.superclass.getAvailableTools.call(this);        
        Ext.apply(tools, {
            'modegroup' : {
                xtype : 'buttongroup',
                columns : 3,
                defaults : {
                    handler : this.toggleModes,
                    toggleGroup : 'playback_mode',
                    enableToggle : true
                },
                items : [{
                    text : 'R',
                    pressed : this.playbackMode === 'ranged'
                }, {
                    text : 'C',
                    pressed : this.playbackMode === 'cumulative'
                }, {
                    text : 'S',
                    pressed : this.playbackMode === 'track'
                }]
            },
            'togglesize' : {
                iconCls: 'gxp-icon-fullScreen',
                toggleHandler: this.toggleMapSize,
                hidden: this.layerManager === null,
                ref: 'btnToggle',
                enableToggle: true,
                allowDepress: true,
                scope: this
            },
            'legend' : {
                iconCls: 'gxp-icon-legend',
                hidden: this.layerManager === null,
                // TODO, this is a hack, but I could not find a better
                // way of doing this. This issue is that when the app
                // is fullscreen, then I need to set the state of the
                // toggle button as the legend is showing, but the
                // button is not toggled. Maybe a better way of
                // handling is this an another event.
                pressed: app.fullScreen,
                ref: 'btnLegend',
                toggleHandler: this.toggleLegend,
                tooltip: this.legendTooltip,
                enableToggle: true,
                scope: this
            },
            'prev' : {
                iconCls: 'gxp-icon-prev',
                handler: this.reverseStep,
                scope: this,
                tooltip: this.prevTooltip
            },
            'edit' : {
                iconCls: 'gxp-icon-editMap',
                handler: this.loadComposser,
                hidden: true,
                scope: this,
                ref: 'btnEdit',
                tooltip: this.editTooltip,
                disabled: window.location.href.match(/view|new/) !== null
            }
        });
        return tools;
    },

    buildPlaybackItems: function() {
        var items = GeoExplorer.PlaybackToolbar.superclass.buildPlaybackItems.call(this);
        return items;
    },

    setToggleButton: function (fullScreen) {
        var btn = this.btnToggle;

        if (fullScreen) {
            btn.btnEl.removeClass('gxp-icon-fullScreen');
            btn.btnEl.addClass('gxp-icon-smallScreen');
        } else {
            btn.btnEl.removeClass('gxp-icon-smallScreen');
            btn.btnEl.addClass('gxp-icon-fullScreen');
        }
        btn.removeClass('x-btn-pressed');
        return btn;
    },

    toggleMapSize: function(btn, pressed) {

        if (app.fullScreen) {
            app.setMinMapSize();
        } else {
            app.setMaxMapSize()
        }

        btn.el.removeClass('x-btn-pressed');
        window.scrollTo(0,0);
    },
    
    toggleLegend: function(btn, pressed){

        if (!this.layerPanel) {
            this.layerPanel = this.buildLayerPanel();
        }

        if (pressed) {
            // global
            this.layerPanel.show();
            this.resizeLegend(app.mapPanel.getHeight());
        } else {
            this.layerPanel.hide();
        }

    },

    resizeLegend: function (height) {

        if (this.layerPanel) {

            this.layerPanel.setHeight(height - this.legendOffsetY);
            this.layerPanel.el.alignTo(
                app.mapPanel.el,'tr-tr',[-1, 33]
            );

            this.layerPanel.doLayout();
        }

    },

    buildLayerPanel: function(btn, pressed) {
        var layerPanel = this.layerManager.output[0];
        // uses global
        layerPanel.el.anchorTo(app.mapPanel.el,'tr-tr',[-1,33]);
        return layerPanel;
    },

    
    reverseStep:function(btn,pressed){
        var timeManager = this.control;
        timeManager.stop();
        timeManager.step *= -1;
        timeManager.tick();
        timeManager.step *= -1;
    },
    
    loadComposser: function(btn){
        window.location.href += '/view';
    },

    addLayerManager: function(){
        var key;
        for (key in app.tools) {
            var tool = app.tools[key];
            if (tool.ptype === "gxp_layermanager") {
                return null;
            }
        }
        var layerManager = new gxp.plugins.LayerManager({
            id:'layermanager-tool',
            outputTarget:'map',
            loader: {
                baseAttrs: {
                    baseParams: {
                        legend_options: "fontAntiAliasing:true;fontSize:11;fontName:Arial;fontColor:#FFA500;fontStyle:bold"
                    }
                }
            },
            overlayNodeText: this.overlayNodeText,
            outputConfig: {
                hidden:true,
                boxMaxWidth: 300,
                height: app.mapPanel.getHeight()-this.legendOffsetY,
                autoScroll: true,
                plain: true,
                border: false,
                floating: true,
                padding: 5,
                shadow: false
            }
        });
        layerManager.init(app);
        layerManager.addOutput();
        return layerManager;
    }
});

Ext.reg('app_playbacktoolbar',GeoExplorer.PlaybackToolbar);
