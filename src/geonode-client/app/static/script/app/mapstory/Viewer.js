/** 
 * @requires mapstory/LayerViewer.js
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
mapstory.Viewer = Ext.extend(mapstory.LayerViewer, {
    
    getDefaultTools: function(config, toggleGroup){
        var tools = [{
                ptype: "gxp_playback",
                id: "playback-tool",
                outputTarget: "map",
                looped: true,
                outputConfig:{
                    xtype: 'app_playbacktoolbar',
                    width: 570,
                    defaults:{scale:'medium'}
                }
            }, {
                ptype: "gxp_timeline",
                id: "timeline-tool",
                outputConfig: {
                    title: null
                },
                outputTarget: "timeline-container",
                playbackTool: "playback-tool"
            }, {
                ptype: 'ms_notes_manager',
                timeline: "timeline-tool"
            }];
        return tools;
    },
    initMapPanel: function(){
        mapstory.Viewer.superclass.initMapPanel.call(this);
    },
    initPortal: function(){
        mapstory.Viewer.superclass.initPortal.call(this);        
    }
});

Ext.reg('ms_viewer',mapstory.Viewer);
