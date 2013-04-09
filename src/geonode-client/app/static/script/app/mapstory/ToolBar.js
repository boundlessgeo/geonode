/*global Ext, mapstory, gxp */

(function () {
    'use strict';

    Ext.ns('mapstory');


    mapstory.ToolBar = Ext.extend(gxp.plugins.Tool, {
        ptype: 'ms-tool-bar',
        saveText: 'UT: Save Map',
        publishText: 'UT: Publish Map',
        addOutput: function () {
            return mapstory.ToolBar.superclass.addOutput.call(this, {
                xtype: 'toolbar',
                items: [
                    {
                        xtype: 'button',
                        text: this.saveText,
                        scope: this,
                        handler: function () {
                            this.target.showMetadataForm();
                        }
                    },
                ]
            });
        }
    });

    Ext.preg(mapstory.ToolBar.prototype.ptype, mapstory.ToolBar);

}());
