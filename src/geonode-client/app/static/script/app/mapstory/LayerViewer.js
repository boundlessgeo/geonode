/** 
 * @requires GeonodeViewer.js
 */
Ext.ns('mapstory');
/**
 * Constructor: mapstory.LayerViewer
 * Create a new MapStory Viewer application.
 *
 * Parameters:
 * config - {Object} Optional application configuration properties.
 *
 * Valid config properties:
 * map - {Object} Map configuration object.
 * ows - {String} OWS URL
 *
 * Valid map config properties:
 * layers - {Array} A list of layer configuration objects.
 * center - {Array} A two item array with center coordinates.
 * zoom - {Number} An initial zoom level.
 *
 * Valid layer config properties:
 * name - {String} Required WMS layer name.
 * title - {String} Optional title to display for layer.
 */
mapstory.LayerViewer = Ext.extend(GeonodeViewer, {
    
    getDefaultTools: function(config, toggleGroup){
        var tools = [{
                ptype: "gxp_playback",
                id: "playback-tool",
                //outputTarget: "map-bbar",
                outputTarget: "map",
                looped: true,
                outputConfig:{
                    xtype: 'app_playbacktoolbar',
                    width: 570,
                    defaults:{scale:'medium'},
                    playbackActions: [
                        "play","slider","loop","fastforward","prev","next",
                        {xtype: "tbspacer"},"legend",{xtype:"tbfill"},
                        "settings",{xtype: "tbspacer"},"togglesize"]
                }
            }];
        return tools;
    },
    initMapPanel: function(){
        this.initialConfig.map = Ext.applyIf(this.initialConfig.map || {}, {
            region: 'center',
            ref: "../main"
        });
        this.initialConfig.map.id = 'msmap';
        mapstory.LayerViewer.superclass.initMapPanel.call(this);
        //add in the tile manager for internal img element caching
        var tileManager = new OpenLayers.TileManager({cacheSize: 512, tilesPerFrame: 24});
        this.mapPanel.map.tileManager = tileManager;
        tileManager.addMap(this.mapPanel.map);
    },
    initPortal: function(){
        var portalConfig = {
            height: 450//, //512 + 55 bbar - 100 -> rounded
            //renderTo: "embedded_map"
        };
        this.portalConfig = (this.portalConfig) ? Ext.applyIf(this.portalConfig,portalConfig) : portalConfig;
        this.portalItems = [{
            xtype: 'panel', 
            region: 'south', 
            hidden: true, 
            layout: 'fit',
            tbar: ['->'], 
            id: 'timeline-container', 
            collapsible: true,
            collapseMode: 'mini',
            header: false, 
            collapsed: true, 
            height: 150
          }, 'msmap'];
        mapstory.LayerViewer.superclass.initPortal.call(this);        
    }
});

Ext.reg('ms_layerviewer',mapstory.LayerViewer);
