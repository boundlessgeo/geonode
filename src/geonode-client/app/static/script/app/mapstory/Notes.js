Ext.ns('mapstory.plugins');

mapstory.plugins.NotesManager = Ext.extend(gxp.plugins.Tool, {
    ptype: 'ms_notes_manager',
    menuText: 'Manage annotations',
    gridTitle: 'Mapstory Annotations',
    insertText: 'Insert',
    deleteText: 'Delete',
    isNewMap: null,
    outputAction: 0,

    createStore: function () {
        this.store = new GeoExt.data.FeatureStore({
            writer: new Ext.data.DataWriter({
                write: Ext.emptyFn
            }),
            fields: [
                {name: 'geometry'},
                {name: 'title', type: 'string'},
                {name: 'in_map', type: 'boolean'},
                {name: 'in_timeline', type: 'boolean'}
            ],
            proxy: new gxp.data.WFSProtocolProxy({
                protocol: new mapstory.protocol.Notes({
                    format: new OpenLayers.Format.GeoJSON(),
                    baseUrl: '/maps/' + this.target.id + '/annotations'
                })
            }),
            autoLoad: true
        });
        // this is needed to get inserts to work
        // otherwise we run into realize error of Ext.data.DataReader
        this.store.reader.getId = function(rec) {
            return Ext.isObject(rec) && rec.id;
        };
    },

    init: function (target) {
        this.outputConfig = {width: 350, height: 300};
        mapstory.plugins.NotesManager.superclass.init.apply(this, arguments);
        if (this.target.id >= 0) {
            this.createStore();
        }
    },

    addOutput: function () {
        return mapstory.plugins.NotesManager.superclass.addOutput.call(this, {
            xtype: 'gxp_featuregrid',
            tbar: [{
                text: this.deleteText,
                handler: function() {
                    var sm = this.output[0].getSelectionModel();
                    var record = sm.getSelected();
                    var feature = record.getFeature();
                    feature.state = OpenLayers.State.DELETE;
                    this.store.remove(record);
                    this.store.save();
                },
                scope: this
            }, {
                text: this.insertText,
                handler: function() {
                    var editor = this.output[0].plugins[0];
                    editor.stopEditing();
                    var recordType = GeoExt.data.FeatureRecord.create([{name: 'title'}, {name: 'in_map'}, {name: 'in_timeline'}]);
                    var feature = new OpenLayers.Feature.Vector();
                    feature.state = OpenLayers.State.INSERT;
                    this.store.insert(0, new recordType({feature: feature, 'in_map': true}));
                    this.output[0].getView().refresh();
                    this.output[0].getSelectionModel().selectRow(0);
                    editor.startEditing(0);
                },
                scope: this
            }],
            ignoreFields: ['geometry'],
            plugins: [{
                ptype: 'gxp_georoweditor'
            }],
            customEditors: {
                'in_map': {xtype: 'checkbox'},
                'in_timeline': {xtype: 'checkbox'}
            },
            title: this.gridTitle,
            store: this.store,
            map:  this.target.mapPanel.map,
            height: 300,
            width: 350
        });
    },

    addActions: function () {
        return mapstory.plugins.NotesManager.superclass.addActions.apply(
            this, [{disabled: !(this.target.id >= 0), text: this.menuText}]);
    }

});

Ext.preg(mapstory.plugins.NotesManager.prototype.ptype, mapstory.plugins.NotesManager);
