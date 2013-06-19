/*jslint browser: true, nomen: true, indent: 4, maxlen: 80 */
/*global gxp, OpenLayers, Ext, GeoExt, mapstory */

(function () {
    'use strict';

    Ext.ns('mapstory');

    mapstory.NotesManager = Ext.extend(gxp.plugins.Tool, {
        ptype: 'ms_notes_manager',
        menuText: 'Manage annotations',
        layerName: 'annotations',
        // save a reference to the openlayers map
        map: null,
        layer: null,
        isNewMap: null,

        createStore: function (target) {
            this.store = new GeoExt.data.FeatureStore({
                fields: [
                    {name: 'geometry'},
                    {name: 'title', type: 'string'}
                ],
                proxy: new GeoExt.data.ProtocolProxy({
                    format: new OpenLayers.Format.GeoJSON(),
                    protocol: new mapstory.protocol.Notes({
                        mapId: target.id
                    })
                }),
                autoLoad: true
            });
        },

        constructor: function (config) {
            mapstory.NotesManager.superclass.constructor.apply(
                this,
                arguments
            );
        },

        init: function (target) {
            // check if there is a target.id. if there is not that
            // means its a new map, we want to suppress the notes
            // manager
            this.isNewMap = !target.id;

            if (!this.isNewMap) {
                this.createStore(target);
            }

            // save a reference to the ol map object
            this.map = target.mapPanel.map || null;

            // if we give gxp this property, it will automatically call
            // our addOutput method
            this.outputAction = 0;
            this.outputConfig = {width: 350, height: 300};
            mapstory.NotesManager.superclass.init.apply(this, arguments);

        },
        buildMenu: function () {
            return [
                {
                    text: this.menuText,
                    scope: this
                }
            ];
        },
        addOutput: function () {
            return mapstory.NotesManager.superclass.addOutput.call(this, {
                xtype: 'gxp_featuregrid',
                title: 'Mapstory Annotations',
                store: this.store,
                map:  this.map,
                height: 300,
                width: 350
            });
        },

        addActions: function () {
            // if the map is a saved map, turn on the menu
            // otherwise do nothing
            // check with bart about this
            if (!this.isNewMap) {
                return mapstory.NotesManager.superclass.addActions.apply(
                    this,
                    this.buildMenu()
                );
            }
        }

    });

    Ext.preg(mapstory.NotesManager.prototype.ptype, mapstory.NotesManager);

}());
