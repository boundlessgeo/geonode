Ext.ns('mapstory.protocol');

mapstory.protocol.Notes = OpenLayers.Class(OpenLayers.Protocol, {

    initialize: function (options) {
        if (!options.baseUrl) {
            throw new Error('You must provide a baseUrl for mapstory.protocol.Notes');
        }
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

    commit: function(features, options) {
        var response;
        // if delete, all features will be delete
        if (features.length > 0 && features[0].state === OpenLayers.State.DELETE) {
            var obj = {action: 'delete', ids: []};
            for (var i = 0, ii = features.length; i<ii; ++i) {
                obj.ids.push(features[i].fid);
            }
            response = new OpenLayers.Protocol.Response({
                requestType: "delete",
                reqFeatures: features
            });
            response.priv = OpenLayers.Request.POST({
                url: this.baseUrl,
                headers: options.headers,
                data: new OpenLayers.Format.JSON().write(obj),
                callback: this.createCallback(this.handleCommit, response, options)
            });
            return response;
        }
        // insert
        if (features.length > 0 && features[0].state === OpenLayers.State.INSERT) {
            response = new OpenLayers.Protocol.Response({
                requestType: "create",
                reqFeatures: features
            });
            response.priv = OpenLayers.Request.POST({
                url: this.baseUrl,
                headers: options.headers,
                data: this.format.write(features, options),
                callback: this.createCallback(this.handleCommit, response, options)
            });
            return response; 
        }
        // update
        response = new OpenLayers.Protocol.Response({
            requestType: "update",
            reqFeatures: features
        });
        response.priv = OpenLayers.Request.POST({
            url: this.baseUrl,
            headers: options.headers,
            data: this.format.write(features, options),
            callback: this.createCallback(this.handleCommit, response, options)
        });
        return response;
    },

    handleCommit: function(response, options) {
        if (options.callback) {
            var request = response.priv;
            var data = Ext.decode(request.responseText);
            response.code = (data.success) ? OpenLayers.Protocol.Response.SUCCESS : 
                OpenLayers.Protocol.Response.FAILURE;
            if (response.requestType === "create") {
                response.insertIds = data.ids;
            }
            if (!data.success) {
                response.error = data;
            }
            options.callback.call(options.scope, response);
        }
    },

    CLASS_NAME: 'mapstory.protocol.Notes'

});
