/*global Ext, mapstory, gxp */

(function () {
    'use strict';

    Ext.ns('mapstory');


    mapstory.ToolBar = Ext.extend(gxp.plugins.Tool, {
        ptype: 'ms-tool-bar',
        saveText: 'UT: Save Map',
        publishText: 'UT: Publish Map',
        zoomText: 'UT: Number of zoom levels',
        wrapDateLineText: 'UT: Wrap dateline',
        colorText: 'UT: Background color',

        buildSaveForm: function () {
            var ge = this.target,
                baseLayer = this.target.mapPanel.map.baseLayer,
                container = Ext.get(this.target.mapPanel.map.getViewport()),
                updateMap = function (asCopy) {
                    var saveForm = Ext.getCmp('saveForm').getForm(),
                        values = saveForm.getValues();
                    this.about.title = values.mapTitle;
                    this.about['abstract'] = values.mapAbstract;
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
                    closeAction: 'hide', // make we just close the
                                         // window, not destory it
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
                                    value: ge.about['abstract']
                                },
                                {
                                    xtype: 'numberfield',
                                    allowNegative: false,
                                    allowDecimals: false,
                                    fieldLabel: this.zoomText,
                                    value: baseLayer.numZoomLevels,
                                    listeners: {
                                        change: function (fld, value) {
                                            baseLayer.addOptions({
                                                numZoomLevels: value
                                            });
                                            this.target.mapPanel.
                                                map.events.
                                                triggerEvent('changebaselayer', {
                                                    layer: baseLayer
                                                });
                                        },
                                        scope: this
                                    }
                                },
                                {
                                    xtype: 'checkbox',
                                    fieldLabel: this.wrapDateLineText,
                                    checked: baseLayer.wrapDateLine,
                                    listeners: {
                                        check: function (cb, value) {
                                            baseLayer.wrapDateLine = value;
                                        },
                                        scope: this
                                    }
                                },
                                {
                                    xtype: 'gxp_colorfield',
                                    fieldLabel: this.colorText,
                                    value: container.getColor('background-color'),
                                    listeners: {
                                        valid: function (field) {
                                            container.setStyle(
                                                'background-color',
                                                field.getValue()
                                            );
                                        },
                                        scope: this
                                    }
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
        getState: function () {
            var container = Ext.get(this.target.mapPanel.map.getViewport()),
                baseLayer = this.target.mapPanel.map.baseLayer;

            return {
                ptype: this.ptype,
                bgColor: container.getColor('background-color'),
                numZoomLevels: baseLayer.numZoomLevels,
                wrapDateLine: baseLayer.wrapDateLine
            };
        },
        addOutput: function () {
            var container = Ext.get(this.target.mapPanel.map.getViewport()),
                baseLayer = this.target.mapPanel.map.baseLayer,
                config = this.initialConfig;

            // why do we guard for these values
            if (config.bgColor) {
                container.setStyle(
                    'background-color',
                    this.initialConfig.bgColor
                );
            }

            if (config.numZoomLevels) {
                baseLayer.addOptions({
                    numZoomLevels: config.numZoomLevels
                });
                this.target.mapPanel.
                    map.events.
                    triggerEvent('changebaselayer', {layer: baseLayer});
            }

            if (config.wrapDateLine) {
                baseLayer.wrapDateLine = config.wrapDateLine;
            }


            return mapstory.ToolBar.superclass.addOutput.call(this, {
                xtype: 'toolbar',
                defaults: {
                    scale: 'medium'
                },
                items: [
                    {
                        xtype: 'button',
                        text: this.saveText,
                        scope: this,
                        width: 100,
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
