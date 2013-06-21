Ext.ns('mapstory.plugins');

mapstory.plugins.NotesManager = Ext.extend(gxp.plugins.Tool, {
    ptype: 'ms_notes_manager',
    menuText: 'Manage annotations',
    gridTitle: 'Mapstory Annotations',
    insertText: 'Insert',
    deleteText: 'Delete',
    layerTitle: 'Annotations',
    ruleTitle: 'Annotations',
    isNewMap: null,
    outputAction: 0,

    createStore: function () {
        this.store = new GeoExt.data.FeatureStore({
            autoSave: false,
            writer: new Ext.data.DataWriter({
                write: Ext.emptyFn
            }),
            fields: [
                {name: 'geometry'},
                {name: 'title', type: 'string'},
                {name: 'start_time', type: 'integer'},
                {name: 'end_time', type: 'integer'},
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
        mapstory.plugins.NotesManager.superclass.init.apply(this, arguments);
        if (this.target.id >= 0) {
            this.createStore();
        }
    },

    addOutput: function () {
        this.target.mapPanel.map.events.on({
            'preaddlayer': function(evt) {
                evt.layer.name = this.layerTitle;
                evt.layer.styleMap.styles["default"].title = this.ruleTitle;
                this.target.mapPanel.map.events.un({
                    'preaddlayer': arguments.callee, scope: this
                });
            },
            scope: this
        });
        return mapstory.plugins.NotesManager.superclass.addOutput.call(this, {
            xtype: 'gxp_featuregrid',
            viewConfig: {
                forceFit: true
            },
            propertyNames: {
                'in_map': 'Show in map',
                'in_timeline': 'Show in timeline',
                'start_time': 'Start time',
                'end_time': 'End time',
                'title': 'Title'
            },
            tbar: [{
                text: this.deleteText,
                iconCls: 'gxp-icon-removelayers',
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
                iconCls: 'gxp-icon-addlayers',
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
                'in_timeline': {xtype: 'checkbox'},
                'start_time': {xtype: 'gxp_datefield'},
                'end_time': {xtype: 'gxp_datefield'}
            },
            customRenderers: {
                'start_time': function(value) {
                    return gxp.form.ExtendedDateField.prototype.setValue(value).value;
                },
                'end_time': function(value) {
                    return gxp.form.ExtendedDateField.prototype.setValue(value).value;
                },
                'in_map': function(value) {
                    return "<input disabled='true' type='checkbox'" + (value ? "checked='checked'" : "") + ">";
                },
                'in_timeline': function(value) {
                    return "<input disabled='true' type='checkbox'" + (value ? "checked='checked'" : "") + ">";
                }
            },
            store: this.store,
            map:  this.target.mapPanel.map
        });
    },

    addActions: function () {
        return mapstory.plugins.NotesManager.superclass.addActions.apply(
            this, [{disabled: !(this.target.id >= 0), text: this.menuText}]);
    }

});

Ext.preg(mapstory.plugins.NotesManager.prototype.ptype, mapstory.plugins.NotesManager);
