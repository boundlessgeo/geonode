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
                iconCls:'gxp-icon-fullScreen',
                toggleHandler: this.toggleMapSize,
                hidden: this.layerManager === null,
                enableToggle: true,
                allowDepress: true,
                scope: this
            },
            'legend' : {
                iconCls:'gxp-icon-legend',
                hidden: this.layerManager === null,
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
    
    buildPlaybackItems:function(){
        var items = GeoExplorer.PlaybackToolbar.superclass.buildPlaybackItems.call(this);
        return items;
    },

    resize: function(offsets) {
        var main = Ext.get('main');
        var headerHeight = Ext.get('header').getHeight() + Ext.get('top-crossbar').getHeight() + Ext.get('crossbar').getHeight();
        var fullBox = {
            width : window.innerWidth +1,
            height : window.innerHeight - headerHeight + 2
        };
        app.portal.setSize(fullBox.width, fullBox.height);
        app.portal.el.alignTo(main, 'tl-tl', offsets);
    },

    toggleMapSize: function(btn,pressed){
        var mapviewer = app.id;
        if(pressed) {
            if (mapviewer) {
                Ext.getCmp('timeline-container').show();
                if (app.isAuthorized()) {
                    this.btnEdit.show();
                }
            }
            if(!app.portal.originalSize) {
                app.portal.originalSize = app.portal.getSize();
                Ext.EventManager.onWindowResize(function() {
                    this.resize.call(this, [0, 0]);
                }, this);
                app.portal.el.setStyle({'z-index' : 1000});
                this.el.setStyle({'z-index' : 1050});
            }
            this.resize.call(this, [-8, 0]);
            this.mapPanel.addClass('full-mapview');
            btn.btnEl.removeClass('gxp-icon-fullScreen');
            btn.btnEl.addClass('gxp-icon-smallScreen');
            btn.setTooltip(this.smallSizeTooltip);
            Ext.getBody().setStyle({overflow:'hidden'});
        }
        else {
            if (mapviewer) {
                Ext.getCmp('timeline-container').hide();
                this.btnEdit.hide();
            }
            app.portal.setSize(app.portal.originalSize);
            app.portal.setPosition(0, 0);
            this.mapPanel.removeClass('full-mapview');
            btn.btnEl.removeClass('gxp-icon-smallScreen');
            btn.btnEl.addClass('gxp-icon-fullScreen');
            btn.setTooltip(this.fullSizeTooltip);
            Ext.getBody().setStyle({overflow:''});
        }
        btn.el.removeClass('x-btn-pressed');
        window.scrollTo(0,0);
    },
    
    toggleLegend:function(btn,pressed){
        if(!btn.layerPanel){
            btn.layerPanel = this.buildLayerPanel();
        }
        if(pressed){
            btn.layerPanel.setHeight(app.mapPanel.getHeight()-this.legendOffsetY);
            btn.layerPanel.show();
            btn.layerPanel.el.alignTo(app.mapPanel.el,'tr-tr',[-1,33]);
        }else{
            btn.layerPanel.hide();
        }
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
    
    buildLayerPanel: function(btn, pressed){
        var layerPanel = this.layerManager.output[0];
        layerPanel.el.anchorTo(app.mapPanel.el,'tr-tr',[-1,33]);
        return layerPanel;
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
