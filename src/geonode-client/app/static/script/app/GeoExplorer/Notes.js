Ext.namespace("GeoExplorer.plugins");

GeoExplorer.plugins.Notes = Ext.extend(gxp.plugins.Tool, {

    /** api: ptype = app_notes */
    ptype: "app_notes",

    errorTitle: "Error creating notes layer",

    iconCls: "gxp-icon-note",

    notesText: "Notes",

    showNotesText: "Show notes",

    featureEditor: null,

    layerNameTpl: null,

    layerName: null,

    createLayerUrl: null,

    params: null,

    workspacePrefix: null,

    onMapSave: function(id) {
        if (this.layerName === null) {
            this.layerName = this.getLayerName(id);
            Ext.Ajax.request({
                method: "POST",
                url: new Ext.Template(this.createLayerUrl).applyTemplate({mapID: id}),
                success: this.onLayerCreateSuccess,
                scope: this
            });
        }
    },

    setLayer: function(layerRecord) {
        var editor = this.target.tools[this.featureEditor];
        var featureManager = editor.getFeatureManager();
        featureManager.setLayer(layerRecord);
        this.actions[0].enable();
    },

    setupLayer: function() {
        var config = {
            source: "local",
            title: this.notesText,
            bbox: this.target.mapPanel.map.maxExtent.toArray(), 
            name: this.workspacePrefix + ":" + this.layerName
        };
        this.target.createLayerRecord(config, this.setLayer, this);
    },

    onLayerCreateSuccess: function(response) {
        var result = Ext.decode(response.responseText);
        if (result && result.success === true) {
            this.setupLayer();
        } else if (result.errors) {
            var msg = '';
            for (var i=0,ii=result.errors.length; i<ii; ++i) {
                var error = result.errors[i];
                msg += error + '<br/>';
            }
            Ext.Msg.show({
                title: this.errorTitle,
                msg: msg,
                icon: Ext.MessageBox.ERROR,
                buttons: Ext.Msg.OK
            });
        }
    },

    getLayerName: function(mapID) {
        return new Ext.Template(this.layerNameTpl).applyTemplate({mapID: mapID});
    },

    /** api: method[addActions]
     */
    addActions: function() {
        // in the composer it's mapID, in the viewer id!
        var id = this.target.mapID || this.target.id;
        if (id) {
            this.layerName = this.getLayerName(id);
            // we need to wait for the baseLayer to be there
            this.target.mapPanel.on("afterlayeradd", this.setupLayer, this, {single: true});
        } else {
            this.target.on({
                saved: this.onMapSave,
                scope: this
            });
        }
        var editor = this.target.tools[this.featureEditor];
        var featureManager = editor.getFeatureManager();
        featureManager.featureLayer.events.on({
            "visibilitychanged": function(evt) {
                Ext.getCmp(this.outputConfig.id).items.get(0).setChecked(evt.object.getVisibility());
            },
            scope: this
        });
        return GeoExplorer.plugins.Notes.superclass.addActions.apply(this, [{
            text: this.notesText,
            disabled: !id,
            id: 'notes-button',
            iconCls: this.iconCls,
            menu: new Ext.menu.Menu({
                id: this.outputConfig.id,
                items: [
                    new Ext.menu.CheckItem({
                        checked: featureManager.featureLayer.getVisibility(),
                        text: this.showNotesText,
                        listeners: {
                            checkchange: function(item, checked) {
                                if (checked === true) {
                                    featureManager.showLayer(
                                        editor.id, editor.showSelectedOnly && "selected"
                                    );
                                } else {
                                    featureManager.hideLayer(editor.id);
                                }
                            },
                            scope: this
                        }
                    })
                ]
            })
        }]);
    }

});

Ext.preg(GeoExplorer.plugins.Notes.prototype.ptype, GeoExplorer.plugins.Notes);
