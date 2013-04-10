/*global Ext, mapstory, gxp */

(function () {
    'use strict';

    Ext.ns('mapstory');


    mapstory.ToolBar = Ext.extend(gxp.plugins.Tool, {
        ptype: 'ms-tool-bar',
        saveText: 'UT: Save Map',
        publishText: 'UT: Publish Map',
        zoomText: 'UT: Number of zoom levels',

        buildSaveForm: function () {
            var ge = this.target,
                updateMap = function (asCopy) {
                    var saveForm = Ext.getCmp('saveForm').getForm(),
                        values = saveForm.getValues();
                    this.about.title = values.mapTitle;
                    this.about.abstract = values.mapAbstract;
                    if (asCopy) {
                        this.save(true);
                    } else { this.save(); }
                    this.metadataForm.hide();
                },
                saveButton = new Ext.Button({
                    text: ge.metadataFormSaveText,
                    handler: function (e) {
                        updateMap.call(this, false);
                    },
                    scope: ge
                }),
                saveAsButton = new Ext.Button({
                    text: ge.metadataFormSaveAsCopyText,
                    handler: function (e) {
                        updateMap.call(this, true);
                    },
                    scope: ge
                }),
                saveWindow = new Ext.Window({
                    title: ge.metaDataHeader,
                    width: 400, // if we don't set a min value chrome miss
                    // rendered the window
                    items: [
                        {
                            xtype: 'form',
                            labelAlign: 'top',
                            bodyStyle: {
                                padding: '5px'
                            },
                            id: 'saveForm',
                            items: [
                                {
                                    xtype: 'textfield',
                                    id: 'mapTitle',
                                    width: '95%',
                                    fieldLabel: ge.metaDataMapTitle,
                                    allowBlank: false,
                                    value: ge.about.title
                                },
                                {
                                    xtype: 'textarea',
                                    id: 'mapAbstract',
                                    width: '95%',
                                    height: 200,
                                    fieldLabel: ge.metaDataMapAbstract,
                                    value: ge.about.abstract
                                },
                                {
                                    xtype: 'numberfield',
                                    allowNegative: false,
                                    allowDecimals: false,
                                    fieldLabel: this.zoomText
                                }
                            ]
                        }
                    ],
                    bbar: [
                        "->",
                        saveButton,
                        saveAsButton
                    ]
                });

            return saveWindow;
        },

        addOutput: function () {
            return mapstory.ToolBar.superclass.addOutput.call(this, {
                xtype: 'toolbar',
                items: [
                    {
                        xtype: 'button',
                        text: this.saveText,
                        scope: this,
                        handler: function () {
                            if (!this.target.metadataForm) {
                                this.target.metadataForm = this.buildSaveForm();
                            }
                            this.target.metadataForm.show();
                        }
                    }
                ]
            });
        }
    });

    Ext.preg(mapstory.ToolBar.prototype.ptype, mapstory.ToolBar);

}());
