Ext.ns('mapstory.protocol');

mapstory.protocol.Notes = OpenLayers.Class(OpenLayers.Protocol, {

    initialize: function (options) {
        this.format = new OpenLayers.Format.GeoJSON();
        if (!options.mapId) {
            throw new Error('You must provide a mapId for mapstory.protocol.Notes');
        }
        this.baseUrl = '/maps/' + options.mapId + '/annotations';
        OpenLayers.Protocol.prototype.initialize.apply(this, arguments);
    },

    read: function (options) {
        OpenLayers.Protocol.prototype.read.apply(this, arguments);
        var resp = new OpenLayers.Protocol.Response({
            requestType: 'read'
        });
        resp.priv = OpenLayers.Request.GET({
            url: this.baseUrl,
            callback: this.createCallback(this.readFeatures, resp, options)
        });
        return resp;
    },

    readFeatures: function (resp, options) {
        resp.features = this.format.read(resp.priv.responseText);
        resp.code = OpenLayers.Protocol.Response.SUCCESS;
        options.callback.call(options.scope, resp);
    },

    create: function (feature) {
        var resp = OpenLayers.Request.POST({
            url: this.baseUrl,
            data: feature
        });
        return resp;
    },

    update: function (feature) {
        var resp = OpenLayers.Request.PUT({
            url: this.baseUrl + '/' + feature.id,
            data: feature
        });
        return resp;
    },

    'delete': function (feature) {
        var resp = OpenLayers.Request.DELETE({
            url: this.baseUrl + '/' + feature.id
        });
        return resp;
    },

    CLASS_NAME: 'mapstory.protocol.Notes'

});
