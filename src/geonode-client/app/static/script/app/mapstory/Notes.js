/*jslint browser: true, nomen: true, indent: 4, maxlen: 80 */
/*global gxp, OpenLayers, Ext, mapstory */

(function () {
    'use strict';

    Ext.ns('mapstory.notes');


    mapstory.NotesManager = Ext.extend(gxp.plugins.Tool, {
        ptype: 'ms_notes_manager',
        menuText: 'Manage annotations',

        // save a reference to the openlayers map
        map: null,
        isNewMap: null,

        loadVectorLayer: function (target) {
            var layer = new OpenLayers.Layer.Vector('annotations', {
                strategies: [
                    new OpenLayers.Strategy.BBOX(),
                ],
                protocol: new mapstory.notes.Protocol({
                    mapConfig: {
                        id: target.id
                    }
                })
            });

            this.map.addLayer(layer);

        },

        init: function (target) {
            mapstory.NotesManager.superclass.init.apply(this, arguments);
            // save a reference to the ol map object
            this.map = target.mapPanel.map || null;
            // check if there is a target.id. if there is not that
            // means its a new map, we want to suppress the notes
            // manager
            this.isNewMap = !target.id;

            if (!this.isNewMap) {
                this.loadVectorLayer(target);
            }

        },

        buildMenu: function () {
            return [
                {
                    text: this.menuText,
                    handler: function () {
                        console.log(this.isNewMap);
                    },
                    scope: this
                }
            ];
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
