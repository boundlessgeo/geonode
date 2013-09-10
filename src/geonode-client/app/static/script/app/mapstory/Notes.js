Ext.ns('mapstory.plugins');

Ext.Tip.prototype.defaultAlign = 'tr-tr?';

// see http://stackoverflow.com/questions/13601124/downloading-image-text-file-using-iframe
Ext.ns('Ext.ux.util');
Ext.ux.util.HiddenForm = function(url,fields){
    if (!Ext.isArray(fields))
        return;
    var body = Ext.getBody(),
        frame = body.createChild({
            tag:'iframe',
            cls:'x-hidden',
            id:'hiddenform-iframe',
            name:'iframe'
        }),
        form = body.createChild({
            tag:'form',
            cls:'x-hidden',
            method: 'GET',
            id:'hiddenform-form',
            action: url,
            target:'iframe'
        });
    Ext.each(fields, function(el,i){
        if (!Ext.isArray(el))
            return false;
        form.createChild({
            tag:'input',
            type:'text',
            cls:'x-hidden',
            id: 'hiddenform-' + el[0],
            name: el[0],
            value: el[1]
        });
    });

    form.dom.submit();

    return frame;
};

mapstory.plugins.NotesManager = Ext.extend(gxp.plugins.Tool, {
    ptype: 'ms_notes_manager',
    timeline: null,
    menuText: 'Manage annotations',
    gridTitle: 'Mapstory Annotations',
    insertText: 'Insert',
    insertMsg: 'Another insert is in progress already',
    deleteText: 'Delete',
    deleteMsg: 'Are you sure you want to delete the currently selected annotation(s)?',
    promptDeleteLabel: "Prompt on delete",
    layerTitle: 'Annotations',
    ruleTitle: 'Annotations',
    saveTitle: 'Annotations',
    saveMsg: 'In order to add annotations, please save your map first by clicking the "Save Map" button:<div class="x-btn"><div class="ms-icon-save msgbox-button"></div></div>',
    downloadText: 'Download',
    uploadText: 'Upload',
    uploadWaitMsg: 'Uploading ...',
    uploadEmptyText: 'Select a CSV file',
    uploadFieldLabel: 'CSV',
    failureTitle: 'Upload Error',
    mediaHtml: 'Use <a href="/mapstory/manual/#using-media-in-annotations" target="_blank">media</a> in your annotations',
    isNewMap: null,
    outputAction: 0,
    /* dummy outputTarget is needed so that action->click in gxp.plugins.Tool does the right thing */
    outputTarget: 'foo',
    outputConfig: {layout: 'fit', height: 200, constrain: true, closeAction: 'hide'},
    createStore: function (id) {
        this.annotationsEndPoint = '/maps/' + id + '/annotations';
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
                {name: 'in_map', type: 'boolean', defaultValue: true},
                {name: 'in_timeline', type: 'boolean', defaultValue: true},
                {name: 'appearance', type: 'string'}
            ],
            proxy: new gxp.data.WFSProtocolProxy({
                protocol: new mapstory.protocol.Notes({
                    format: new OpenLayers.Format.GeoJSON(),
                    baseUrl: this.annotationsEndPoint
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
                    this.output[0].ownerCt.show();
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
        this.appearanceData = [
            ['tl-tl?', 'Top left'],
            ['t-t?', 'Top center'],
            ['tr-tr?', 'Top right'],
            ['l-l?', 'Center left'],
            ['c-c?', 'Center'],
            ['r-r?', 'Center right'],
            ['bl-bl?', 'Bottom left'],
            ['b-b?', 'Bottom center'],
            ['br-br?', 'Bottom right'],
            ['geom', 'Next to geometry']
        ];
        mapstory.plugins.NotesManager.superclass.init.apply(this, arguments);
        if (this.target.id !== null) {
            this.createStore(this.target.id);
        } else {
            this.target.on('saved', function(id) {
                this.createStore(id);
            }, this, {single: true});
        }
    },

    addOutput: function () {
        if (this.target.id === null && this.target.mapID === null) {
            Ext.Msg.show({
                icon: Ext.Msg.WARNING,
                title: this.saveTitle,
                msg: this.saveMsg,
                width: 350,
                buttons: Ext.Msg.OK
            });
            return;
        }
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
            var d = new Date(me.playback.playbackToolbar.control.currentValue);
            d.setTime( d.getTime() + d.getTimezoneOffset()*60*1000 );
            return d;
        };
        var outputConfig = Ext.apply({}, this.outputConfig);
        outputConfig.x = this.target.mapPanel.body.getLeft() + 20;
        outputConfig.items = [{
            xtype: 'gxp_featuregrid',
            viewConfig: {
                forceFit: true
            },
            propertyNames: {
                'in_map': 'Map',
                'in_timeline': 'Timeline',
                'start_time': 'Start Time',
                'end_time': 'End Time',
                'title': 'Title',
                'content': 'Content',
                'appearance': 'Annotation Location'
            },
            tbar: [{
                text: this.deleteText,
                iconCls: 'gxp-icon-removelayers',
                handler: function() {
                    var sm = this.output[0].getSelectionModel();
                    var records = sm.getSelections();
                    if (records && records.length > 0) {
                        var save = function(records) {
                            for (var i = 0, ii = records.length; i<ii; ++i) {
                                var record = records[i];
                                var feature = record.getFeature();
                                feature.state = OpenLayers.State.DELETE;
                                this.store.remove(record);
                            }
                            this.store.save();
                        };
                        if (this.output[0].promptOnDelete.getValue()) {
                            Ext.Msg.show({
                                title: this.deleteText,
                                msg: this.deleteMsg,
                                buttons: Ext.Msg.YESNOCANCEL,
                                fn: function(btn) {
                                    if (btn === 'yes') {
                                        save.call(this, records);
                                    }
                                },
                                scope: this
                            });
                        } else {
                            save.call(this, records);
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
                            cls: 'row-editor-msg-box',
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
                    this.store.insert(0, new recordType({feature: feature, 'in_map': true, 'in_timeline': true}));
                    this.output[0].getView().refresh();
                    this.output[0].getSelectionModel().selectRow(0);
                    editor.startEditing(0);
                    editor.on('canceledit', function() {
                        if (this.store.getAt(0).getFeature().state === OpenLayers.State.INSERT) {
                            this.store.removeAt(0);
                        }
                    }, this, {single: true});
                },
                scope: this
            }, {
                text: this.uploadText,
                handler: function() {
                    var fp = new Ext.FormPanel({
                        width: 400,
                        title: this.uploadText,
                        bodyStyle: 'padding: 10px 10px 0 10px;',
                        labelWidth: 50,
                        defaults: {
                            anchor: '95%',
                            allowBlank: false,
                            msgTarget: 'side'
                        },
                        fileUpload: true,
                        items: [{
                            xtype: "hidden",
                            name: "csrfmiddlewaretoken",
                            value: Ext.util.Cookies.get('csrftoken')
                        }, {
                            xtype: 'fileuploadfield',
                            emptyText: this.uploadEmptyText,
                            fieldLabel: this.uploadFieldLabel
                        }],
                        footerCfg : {
                            tag: 'div',
                            children : [
                                {
                                    tag: 'div',
                                    style: 'position:absolute; margin: 5px 0 0 10px;',
                                    children : [
                                        { html: '<a href="/mapstory/manual/#bulk-upload-of-annotations" target="_blank">Learn More</a>' }
                                    ]
                                }
                            ]
                        },
                        buttons: [{
                            text: this.uploadText,
                            handler: function() {
                                var showUploadError = function(fp, o) {
                                    Ext.Msg.show({
                                        icon: Ext.Msg.ERROR,
                                        title: this.failureTitle,
                                        msg: o.response.responseText,
                                        width: 350,
                                        buttons: Ext.Msg.OK 
                                    });
                                };
                                if (fp.getForm().isValid()){
	                                fp.getForm().submit({
	                                    url: this.annotationsEndPoint,
	                                    waitMsg: this.uploadWaitMsg,
	                                    success: function(fp, o) {
                                            var result = Ext.decode(o.response.responseText);
                                            if (result.success) {
                                                this.uploadWindow.close();
                                                delete this.uploadWindow;
                                                this.store.load();
                                            } else {
                                                showUploadError.call(this, fp, o);
                                            }
	                                    },
                                        failure: showUploadError,
                                        scope: this
                                    });
                                }
                            },
                            scope: this
                        }]
                    });
                    this.uploadWindow = new Ext.Window({items: [fp]}).show();
                },
                scope: this
            }, {
                text: this.downloadText,
                handler: function() {
                    Ext.ux.util.HiddenForm(this.annotationsEndPoint, [['csv', '']]);
                },
                scope: this
            }, '->', {                
                xtype: 'checkbox',
                ref: '../promptOnDelete',
                boxLabel: this.promptDeleteLabel,
                checked: true
            }],
            ignoreFields: ['geometry'],
            plugins: [new gxp.plugins.GeoRowEditor({monitorValid: false, listeners: {
                'buttonrender': function(editor, buttons) {
                    buttons.width += 350;
                    buttons.add({xtype: 'box', width: 350, style: 'text-align:right', html: me.mediaHtml});
                    buttons.doLayout();
                },
                'beforeedit': function(editor, rowIndex) {
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
                },
                'afteredit': function(editor, changes, r, rowIndex) {
                    if (r.getFeature().geometry !== null && Ext.isEmpty(r.get('appearance'))) {
                        r.set('appearance', 'geom');
                    }
                    if (r.getFeature().geometry === null && r.get('appearance') === 'geom') {
                        r.set('appearance', '');
                    }
                }
            }, scope: this})],
            columnConfig: {
                'in_timeline': {width: 75},
                'in_map': {width: 50},
                'start_time': {width: 200},
                'end_time': {width: 200},
                'appearance': {width: 115}
            },
            customEditors: {
                'in_map': {xtype: 'checkbox'},
                'in_timeline': {xtype: 'checkbox'},
                'start_time': {id: 'start-time', xtype: 'gxp_datetimefield', todayText: 'Now', selectToday: function() {
                    var d = new Date(me.playback.playbackToolbar.control.currentValue);
                    d.setTime( d.getTime() + d.getTimezoneOffset()*60*1000 );
                    this.setValue(d);
                    this.fireEvent('select', this, this.value);
                }},
                'end_time': {id: 'end-time', xtype: 'gxp_datetimefield', todayText: 'Now', selectToday: function() {
                    var d = new Date(me.playback.playbackToolbar.control.currentValue);
                    d.setTime( d.getTime() + d.getTimezoneOffset()*60*1000 );
                    this.setValue(d);
                    this.fireEvent('select', this, this.value);
                }},
                'content': {xtype: 'textarea'},
                'appearance': {xtype: 'combo', mode: 'local', triggerAction: 'all', store: this.appearanceData}
            },
            customRenderers: {
                'content': 'htmlEncode',
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
                },
                'appearance': function(value) {
                    if (Ext.isEmpty(value)) {
                        value = Ext.Tip.prototype.defaultAlign;
                    }
                    for (var i = 0, ii = me.appearanceData.length; i<ii; ++i) {
                        if (me.appearanceData[i][0] === value) {
                            return me.appearanceData[i][1];
                        }
                    }
                }
            },
            store: this.store,
            map:  this.target.mapPanel.map
        }];
        var win = new Ext.Window(outputConfig).show();
        var output = win.items.get(0);
        this.output = [output];
        win.on('hide', function() {
            output.getSelectionModel().clearSelections();
            var editor = output.plugins[0];
            editor.stopEditing();
            var hasInsert = false;
            this.store.each(function(record) {
                if (record.getFeature().state === OpenLayers.State.INSERT) {
                    hasInsert = true;
                    return false;
                }
            });
            if (hasInsert === true && this.store.getAt(0).getFeature().state === OpenLayers.State.INSERT) {
                this.store.removeAt(0);
            }
        }, this);
        return win;
    },

    addActions: function () {
        return mapstory.plugins.NotesManager.superclass.addActions.apply(
            this, [{hidden: !this.target.isAuthorized(), iconCls: 'gxp-icon-note', tooltip: this.menuText}]);
    }

});

Ext.preg(mapstory.plugins.NotesManager.prototype.ptype, mapstory.plugins.NotesManager);
