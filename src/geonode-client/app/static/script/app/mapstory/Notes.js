Ext.ns('mapstory.plugins');

// make sure row editor is visible on the last row
Ext.override(Ext.grid.GridView, {
    getEditorParent: function() {
        return document.body;
    }
});

mapstory.plugins.NotesManager = Ext.extend(gxp.plugins.Tool, {
    ptype: 'ms_notes_manager',
    timeline: null,
    menuText: 'Manage annotations',
    gridTitle: 'Mapstory Annotations',
    insertText: 'Insert',
    insertMsg: 'Another insert is in progress already',
    deleteText: 'Delete',
    deleteMsg: 'Are you sure you want to delete the currently selected annotation?',
    promptDeleteLabel: "Prompt on delete",
    layerTitle: 'Annotations',
    ruleTitle: 'Annotations',
    isNewMap: null,
    outputAction: 0,
    outputConfig: {closeAction: 'hide'},
    createStore: function (id) {
        this.store = new GeoExt.data.FeatureStore({
            autoSave: false,
            writer: new Ext.data.DataWriter({
                write: Ext.emptyFn
            }),
            fields: [
                {name: 'geometry'},
                {name: 'title', type: 'string'},
                {name: 'content', type: 'string'},
                {name: 'start_time', type: 'integer', useNull: true},
                {name: 'end_time', type: 'integer', useNull: true},
                {name: 'in_map', type: 'boolean'},
                {name: 'in_timeline', type: 'boolean'},
                {name: 'appearance', type: 'string'}
            ],
            proxy: new gxp.data.WFSProtocolProxy({
                protocol: new mapstory.protocol.Notes({
                    format: new OpenLayers.Format.GeoJSON(),
                    baseUrl: '/maps/' + id + '/annotations'
                })
            }),
            autoLoad: true
        });
        // this is needed to get inserts to work
        // otherwise we run into realize error of Ext.data.DataReader
        this.store.reader.getId = function(rec) {
            return Ext.isObject(rec) && rec.id;
        };
        if (this.timelineTool) {
            this.timelineTool.on('click', function(fid) {
                if (this.output[0]) {
                    this.output[0].ownerCt.ownerCt.show();
                } else {
                    this.addOutput();
                }
                var idx = this.store.findBy(function(record) {
                    return record.getFeature().fid === fid;
                });
                var record = this.store.getAt(idx);
                var me = this; window.setTimeout(function() {
                  me.output[0].getSelectionModel().selectRecords([record]);
                }, 250);
            }, this);
            this.timelineTool.setAnnotationsStore(this.store);
        }
    },

    init: function (target) {
        this.timelineTool = target.tools[this.timeline];
        this.playback = target.tools[this.timelineTool.playbackTool];
        mapstory.plugins.NotesManager.superclass.init.apply(this, arguments);
        if (this.target.id !== null) {
            this.createStore(this.target.id);
        } else {
            this.target.on('saved', function(id) {
                this.createStore(id);
                this.actions[0].enable();
            }, this, {single: true});
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
        var me = this;
        // override to get date time picker to use current time in playback
        gxp.form.ExtendedDateField.prototype.getPickerDate = function() {
            return new Date(me.playback.playbackToolbar.control.currentValue);
        };
        var output = mapstory.plugins.NotesManager.superclass.addOutput.call(this, {
            xtype: 'gxp_featuregrid',
            viewConfig: {
                forceFit: true
            },
            propertyNames: {
                'in_map': 'Map',
                'in_timeline': 'Timeline',
                'start_time': 'Start time',
                'end_time': 'End time',
                'title': 'Title',
                'content': 'Content'
            },
            tbar: [{
                text: this.deleteText,
                iconCls: 'gxp-icon-removelayers',
                handler: function() {
                    var sm = this.output[0].getSelectionModel();
                    var record = sm.getSelected();
                    if (record) {
                        var save = function() {
                            var feature = record.getFeature();
                            feature.state = OpenLayers.State.DELETE;
                            this.store.remove(record);
                            this.store.save();
                        };
                        if (this.output[0].promptOnDelete.getValue()) {
                            Ext.Msg.show({
                                title: this.deleteText,
                                msg: this.deleteMsg,
                                buttons: Ext.Msg.YESNOCANCEL,
                                fn: function(btn) {
                                    if (btn === 'yes') {
                                        save.call(this);
                                    }
                                },
                                scope: this
                            });
                        } else {
                            save.call(this);
                        }
                    }
                },
                scope: this
            }, {
                text: this.insertText,
                iconCls: 'gxp-icon-addlayers',
                handler: function() {
                    var hasInsert = false;
                    this.store.each(function(record) {
                        if (record.getFeature().state === OpenLayers.State.INSERT) {
                            hasInsert = true;
                            return false;
                        }
                    });
                    if (hasInsert === true) {
                        Ext.Msg.show({
                            title: this.insertText,
                            msg: this.insertMsg,
                            buttons: Ext.Msg.OK
                        });
                        return;
                    }
                    var editor = this.output[0].plugins[0];
                    editor.stopEditing();
                    var recordType = GeoExt.data.FeatureRecord.create([
                        {name: 'title'},
                        {name: 'content'},
                        {name: 'in_map'}, 
                        {name: 'in_timeline'},
                        {name: 'start_time'},
                        {name: 'end_time'},
                        {name: 'appearance'}
                    ]);
                    var feature = new OpenLayers.Feature.Vector();
                    feature.state = OpenLayers.State.INSERT;
                    this.store.insert(0, new recordType({feature: feature, 'in_map': true}));
                    this.output[0].getView().refresh();
                    this.output[0].getSelectionModel().selectRow(0);
                    editor.startEditing(0);
                    editor.on('canceledit', function() {
                        this.store.removeAt(0);
                    }, this, {single: true});
                },
                scope: this
            }, {
                xtype: 'checkbox',
                ref: '../promptOnDelete',
                boxLabel: this.promptDeleteLabel,
                checked: true
            }],
            ignoreFields: ['geometry'],
            plugins: [new gxp.plugins.GeoRowEditor({monitorValid: false, listeners: {'beforeedit': function(editor, rowIndex) {
                var record = this.grid.store.getAt(rowIndex);
                if (!Ext.getCmp('start-time').rendered) {
                    Ext.getCmp('start-time').value = record.get('start_time');
                } else {
                    Ext.getCmp('start-time').setValue(record.get('start_time'));
                }
                if (!Ext.getCmp('end-time').rendered) {
                    Ext.getCmp('end-time').value = record.get('end_time');
                } else {
                    Ext.getCmp('end-time').setValue(record.get('end_time'));
                }
            }}, scope: this})],
            columnConfig: {
                'in_timeline': {width: 75},
                'in_map': {width: 50},
                'start_time': {width: 200},
                'end_time': {width: 200}
            },
            customEditors: {
                'in_map': {xtype: 'checkbox'},
                'in_timeline': {xtype: 'checkbox'},
                'start_time': {id: 'start-time', xtype: 'gxp_datetimefield'},
                'end_time': {id: 'end-time', xtype: 'gxp_datetimefield'},
                'content': {xtype: 'textarea'},
                'appearance': {xtype: 'combo', mode: 'local', triggerAction: 'all', store: [
                    ['tl-tl?', 'Top left'],
                    ['t-t?', 'Top center'],
                    ['tr-tr?', 'Top right'],
                    ['l-l?', 'Center left'],
                    ['c-c?', 'Center'],
                    ['r-r?', 'Center right'],
                    ['bl-bl?', 'Bottom left'],
                    ['b-b?', 'Bottom center'],
                    ['br-br?', 'Bottom right']
                ]}
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
        this.pos_ = output.ownerCt.ownerCt.getPosition();
        output.ownerCt.ownerCt.on('hide', function() {
            output.getSelectionModel().clearSelections();
            var editor = output.plugins[0];
            editor.stopEditing();
        }, this);
        output.ownerCt.ownerCt.on('move', function(cmp, x, y) {
            var editor = output.plugins[0];
            if (editor && editor.rendered) {
                var pos = editor.getPosition();
                var deltaX = this.pos_[0] - x;
                var deltaY = this.pos_[1] - y;
                editor.setPosition([pos[0] - deltaX, pos[1] - deltaY]);
            }
            this.pos_ = [x, y];
        }, this);
        return output;
    },

    addActions: function () {
        return mapstory.plugins.NotesManager.superclass.addActions.apply(
            this, [{disabled: (this.target.id === null), iconCls: 'gxp-icon-note', tooltip: this.menuText}]);
    }

});

Ext.preg(mapstory.plugins.NotesManager.prototype.ptype, mapstory.plugins.NotesManager);
