/*global Ext, mapstory, gxp, window*/

(function () {
    'use strict';

    Ext.ns('mapstory.plugins');

    mapstory.plugins.AddLayers = Ext.extend(gxp.plugins.Tool, {
        ptype: 'ms_add_layer',
        addActions: function () {
            return mapstory.plugins.AddLayers.superclass.addActions.apply(this, [
                {
                    iconCls: 'gxp-icon-addlayers',
                    scope: this,
                    handler: function () {
                        var search = new window.LayerSearch({
                            geoExplorer: this.target,
                            searchUrl: '/search/api'
                        }).render();
                    }
                }
            ]);
        }
    });

    Ext.preg(mapstory.plugins.AddLayers.prototype.ptype, mapstory.plugins.AddLayers);
}());


