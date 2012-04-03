Ext.ns('mapstory');
/**
 * Constructor: mapstory.LayerViewer
 * Create a new MapStory LayerViewer application.
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
    
});

Ext.reg('ms_layerviewer',mapstory.LayerViewer);