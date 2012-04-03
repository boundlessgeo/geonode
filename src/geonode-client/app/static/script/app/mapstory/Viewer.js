/** 
 * @requires GeonodeViewer.js
 */
Ext.ns('mapstory');
/**
 * Constructor: mapstory.Viewer
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
mapstory.Viewer = Ext.extend(GeonodeViewer, {
    
    getDefaultTools: function(config, toggleGroup){
        var tools = [{
                ptype: "gxp_wmsgetfeatureinfo",
                format: "grid",
                actionTarget: 'map',
                layerParams: ['TIME'],
                outputConfig: {width: 400, height: 300}
            }, {
                ptype: "gxp_playback",
                id: "playback-tool",
                width: 580,
                outputTarget: "map-bbar",
                looped: true,
                outputConfig:{
                    xtype: 'app_playbacktoolbar'
                }
        }];
        return tools;
    },
    initMapPanel: function(){
        this.initialConfig.map = Ext.applyIf(this.initialConfig.map ||
            {}, {
                region: 'center',
                ref: "../main",
                bbar: {
                    id: 'map-bbar',
                    height:55,
                    items: []
                }
            });
        mapstory.Viewer.superclass.initMapPanel.call(this);
    },
    initPortal: function(){
        this.portalConfig = {
            height: 450, //512 + 55 bbar - 100 -> rounded
            renderTo: "embedded_map"
        };
        mapstory.Viewer.superclass.initPortal.call(this);        
    }
});

Ext.reg('ms_viewer',mapstory.Viewer);
