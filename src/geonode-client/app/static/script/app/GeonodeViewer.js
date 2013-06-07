/**
 * Copyright (c) 2012 OpenGeo
 */
// http://www.sencha.com/forum/showthread.php?141254-Ext.Slider-not-working-properly-in-IE9
// TODO re-evaluate once we move to Ext 4
Ext.override(Ext.dd.DragTracker, {
    onMouseMove: function(e, target){
        if (this.active && Ext.isIE && !Ext.isIE9 && !e.browserEvent.button) {
            e.preventDefault();
            this.onMouseUp(e);
            return;
        }
        e.preventDefault();
        var xy = e.getXY(), s = this.startXY;
        this.lastXY = xy;
        if (!this.active) {
            if (Math.abs(s[0] - xy[0]) > this.tolerance || Math.abs(s[1] - xy[1]) > this.tolerance) {
                this.triggerStart(e);
            }
            else {
                return;
            }
        }
        this.fireEvent('mousemove', this, e);
        this.onDrag(e);
        this.fireEvent('drag', this, e);
    }
});
/**
 * Constructor: GeoNodeViewer
 * Create a new GeonodeViewer application.
 *
 * Parameters:
 * config - {Object} Optional application configuration properties.
 *
 * Valid config properties:
 * map - {Object} Map configuration object.
 * ows - {String} OWS URL
 *
 * Valid map config properties:
 * layers - {Array} A list of layer configuration objects.
 * center - {Array} A two item array with center coordinates.
 * zoom - {Number} An initial zoom level.
 *
 * Valid layer config properties:
 * name - {String} Required WMS layer name.
 * title - {String} Optional title to display for layer.
 */
var GeonodeViewer = Ext.extend(gxp.Viewer, {
    
    /**
     * api: config[localGeoServerBaseUrl]
     * ``String`` url of the local GeoServer instance
     */
    localGeoServerBaseUrl: "",

    /**
     * api: config[cachedSourceMatch]
     * ``RegExp`` pattern to match the layer url to for adding extra subdomains
     */
    cachedSourceMatch: /mapstory\.dev|mapstory\.org/,

    /**
     * api: config[cachedSubdomains]
     * @type {Array} extra subdomains to be tacked onto existing url
     */
    cachedSubdomains: ['t1', 't2', 't3', 't4'],

    /**
     * api: config[useMapOverlay]
     * ``Boolean`` Should we add a scale overlay to the map? Set to false
     * to not add a scale overlay.
     */
    useMapOverlay: null,

    /**
     * private: property[toggleGroup]
     * ``String``
     */
    toggleGroup: "map",
    
    /**
     * private: property[mapPanel]
     * the :class:`GeoExt.MapPanel` instance for the main viewport
     */
    mapPanel: null,
    
    /**
     * Property: modified
     * ``Number``
     */
    modified: 0,

    /**
     * Property: popupCache
     * {Object} An object containing references to visible popups so that 
     *     we can insert responses from multiple requests.
     */
    popupCache: null,
    
    /** private: property[urlPortRegEx]
     *  ``RegExp``
     */
    urlPortRegEx: /^(http[s]?:\/\/[^:]*)(:80|:443)?\//,

    /** private: property[fullScreen]
     *  Boolean
     */
    fullScreen: false,


    //public variables for string literals needed for localization
    backgroundContainerText: "UT:Background",
    connErrorTitleText: "Communication error",
    connErrorText: "The mapping server did not respond properly. It is likely temporarily down, but should be up soon. If this problem persists please let the administrators know.",
    connErrorDetailsText: "UT:Details...",
    layerContainerText: "UT:Map Layers",
    saveFailMessage: "UT: Sorry, your map could not be saved.",
    saveFailTitle: "UT: Error While Saving",
    saveMapText: "UT: Save Map",
    saveMapAsText: "UT: Save Map As",
    saveNotAuthorizedMessage: "UT: You Must be logged in to save this map.",
    sourceLoadFailureMessage: 'UT: Error contacting server.\n Please check the url and try again.',
    unknownMapMessage: 'UT: The map that you are trying to load does not exist.  Creating a new map instead.',
    unknownMapTitle: 'UT: Unknown Map',

    constructor: function(config){
        config = config || {};
        this.popupCache = {};
        // add any custom application events
        this.addEvents(        
            /**
             * api: event[saved]
             * Fires when the map has been saved.
             *  Listener arguments:
             *  ``String`` the map id
             */
            "saved",        
            /**
             * api: event[beforeunload]
             * Fires before the page unloads. Return false to stop the page
             * from unloading.
             */
            "beforeunload",
            /** api: event[toggleSize]
             * an event that is fired before the map portal is resized
             */
            "togglesize"
        );

        //Add special connection handlers
        this.addConnectionHandlers();

        //Globally register the color manager for any field
        this.registerColorManager();

        this.on('portalready', function () {
            // save a reference to the class object
            // for later use

            if (this.embed !== true) {
                this.toggleMapSizeViaUrl();
            }

            if (this.embed === true) {
                Ext.getCmp('timeline-container').show();
                // after we add the time container to the map, we need
                // to refresh the layout in order for the map to make
                // room for it
                this.portal.doLayout();
            }

            // check to make sure that the browser supports the
            // onhashchange event
            if (window.onhashchange !== undefined) {
                // register the toggleMapSize with the onhashchange
                // event
                if (this.embed !== true) { // check to see if we are in the embed mode
                    window.onhashchange = Ext.createDelegate(
                        this.toggleMapSizeViaUrl,
                        this
                    );
                }
            }

            Ext.EventManager.onWindowResize(function () {
                // if the map is fullscreen we need to adjust the size
                // of the map window when an user resizes the browser
                // however, if we are not in full screen mode, then we
                // don't care
                if ((this.fullScreen) && (this.embed !== true)) {
                    this.expandMap();
                }
            }, this);
        });

        // limit combo boxes to the window they belong to - fixes issues with
        // list shadow covering list items
        Ext.form.ComboBox.prototype.getListParent = function(){
            return this.el.up(".x-window") || document.body;
        };

        // don't draw window shadows - allows us to use autoHeight: true
        // without using syncShadow on the window
        Ext.Window.prototype.shadow = false;

        GeonodeViewer.superclass.constructor.apply(this, [config]);
    },

    /**
     * Method: toggleMapSizeViaUrl
     * Checks the value of the hash url and switches the
     *  state of the map portal
     */
    toggleMapSizeViaUrl: function () {
        // we have access to the mapPanel and the portal, both of
        // which we need
        var hash = window.location.hash;
        if (hash === '#full') {
            this.setMaxMapSize();
        } else {
            this.setMinMapSize();
        }
    },
    /**
     * Method: setHashUrl
     * Safely sets the value of the hash url. First checks to make sure
     * that hash url is not already set to that value.
     */
    setHashUrl: function (newValue) {
        if (window.location.hash !== newValue) {
            window.location.hash = newValue;
        }
    },
    /**
     * Method: expandMap 
     *
     * Expands the map portal to what we consider an full screen used
     * by the setMaxMapSize and also attached to the window.onresize
     * event
     */
    expandMap: function () {
        var headerHeight =
            Ext.get('header').getHeight() +
            Ext.get('top-crossbar').getHeight() +
            Ext.get('crossbar').getHeight(),
            main = Ext.get('main'),
            newWidth = window.innerWidth,
            newHeight = window.innerHeight - headerHeight + 2; // why ?

        if (!this.portal.originalSize) {
            this.portal.originalSize = this.portal.getSize();
        }

        this.portal.setSize(newWidth, newHeight);
        this.portal.el.alignTo(main, 'tl-tl', [0, 0]);
    },

    /**
     * Method: setMaxMapSize
     * Sets the map portal to the full size of the window,
     * minus the height of the header elements
     * call the toggleSize function after the elements are adjusted
     */
    setMaxMapSize: function () {
        this.expandMap();
        // prevent the thumb nail images from showing through in full
        // screen mode
        this.portal.el.setStyle({'z-index' : 1000});
        Ext.getBody().setStyle({
            overflow: 'hidden'
        });

        // if our geonodeview object has an id, we know that we are
        // current on the map view page, otherwise its a layer view
        // page which does not have a timeline
        if (this.id) {
            Ext.getCmp('timeline-container').show();
        }

        window.scrollTo(0, 0);
        this.setHashUrl("#full");
        this.fullScreen = true;
        this.fireEvent('togglesize', this.fullScreen, this.isAuthorized());
    },

    /**
     * Method: setMinMapSize
     * Sets the map portal to the min or default size.
     * Calls the toggleSize event at the end
     */
    setMinMapSize: function () {

        this.portal.setSize(this.portal.originalSize);
        this.portal.setPosition(0, 0);

        this.mapPanel.removeClass('full-mapview');
        Ext.getBody().setStyle({
            overflow: ''
        });

        // same check as above
        if (this.id) {
            Ext.getCmp('timeline-container').hide();
        }

        // we need to set the value of the hash url to be empty
        this.setHashUrl("");
        this.fullScreen = false;
        this.fireEvent('togglesize', this.fullScreen, this.isAuthorized());

    },

    loadConfig: function(config, callback){
        var hasConfig = config && (config.tools || config.sources || config.map);
        config = Ext.apply(config ||
        {}, {
            proxy: "/proxy/?url=",
            rest: "/maps/"
        });
        if (hasConfig) {
            callback.call(this, config);
        }
        else {
        
            Ext.Ajax.request({
                url: window.location.href.split("?")[0].replace(/\/view|\/embed|(\/new)|([0-9])$/, "$1$2/data"),
                success: function(response){
                    var loadedConfig = Ext.decode(response.responseText, true);
                    Ext.apply(config, loadedConfig);
                    this.mapID = config.id;
                    callback.call(this, config);
                },
                scope: this
            });
        }
    },
    applyConfig: function(config){
        var defaultTools = this.getDefaultTools(config, this.toggleGroup);
        var origTools = config.tools || [];
        var ptypes = Ext.pluck(config.tools, 'ptype');
        config.tools = [];
        Ext.each(defaultTools, function(cfg){
            var toolIndex = ptypes.indexOf(cfg.ptype);
            if (toolIndex == -1) {
                //default tool was not included in the original config
                config.tools.push(cfg);
            } else {
                //default tool was included in the original config
                var savedConfig = origTools[toolIndex];
                //always get outputTarget from default tool
                delete savedConfig.outputTarget;
                var appliedConfig = Ext.apply(cfg,savedConfig);
                config.tools.push(appliedConfig);
            }
        });
        GeonodeViewer.superclass.applyConfig.call(this, config);
    },
    getDefaultTools: function(config, toggleGroup){
        return config.tools || [];
    },
    /**
     * Method: initMapPanel
     * Create the various mapItems & mapPlugins used by the viewer.
     */
    initMapPanel: function() {
        var defaultControls = [new OpenLayers.Control.Zoom(),new OpenLayers.Control.Navigation()];
        if(!this.initialConfig.map){
            this.initialConfig.map = {controls:defaultControls};
        } else {
            this.initialConfig.map.controls = (this.initialConfig.map.controls || []).concat(defaultControls);
        }
        //call parent function
        GeonodeViewer.superclass.initMapPanel.call(this);
        
        //add listeners to layer store (doesn't exist until after the superclass's function is called)
        this.mapPanel.layers.on({
            "add": function(store, records) {
                var layer;
                //if the map starts out with more than 5 temporal wms-ish layers, then they will all be
                //single tile layers. If layers are added to exceed the 5 layer limit, then only layers
                //6+ will be single tile layers. dynamically changing all the layers when adding or removing
                //layers introduced all kinds of potential error and issues
                var forceSingleTile = store.queryBy(function(rec){
                    var lyr = rec.getLayer();
                    return lyr.dimensions && lyr.dimensions.time && (lyr instanceof OpenLayers.Layer.Grid);
                }).getCount()>5;
                for(var i = records.length - 1; i >= 0; i--) {
                    layer = records[i].getLayer();
                    if(!layer.isBaseLayer && (layer instanceof OpenLayers.Layer.Grid)) {
                        layer.addOptions({
                            singleTile: forceSingleTile,
                            transitionEffect: 'resize'
                        });
                        var url = layer.url;
                        if (Ext.isString(url)) {
                            if (url.charAt(0) === '/' && url.indexOf('geoserver') !== -1) {
                                url = this.localGeoServerBaseUrl + 'wms';
                            }
                            if (url.search(this.cachedSourceMatch)>-1 && this.cachedSubdomains){
                                var uparts = url.split('://');
                                var urls = [];
                                for(var j=0, h=uparts.slice(-1)[0], len=this.cachedSubdomains.length; j<len; j++){
                                    urls.push(
                                        (uparts.length>1 ? uparts[0] + '://' : '') + this.cachedSubdomains[j] + '.' + h
                                    );
                                }
                                layer.url = urls.concat([url]);
                            }
                        }
                        if(layer.params) {
                            layer.params.TILED = true;
                        }
                    }
                }
            },
            scope: this
        });
    },
    /**
     * Method: initPortal
     * Create the various parts that compose the layout.
     */
    initPortal: function(){
        /** Define the portal items in subclasses **/
        this.on("ready", function(){
            this.mapPanel.map.events.on({
                'changelayer': function(evt) {
                    var layer = evt.layer;
                    if (evt.property === 'params' && layer.params.TILED === true) {
                        Ext.get(layer.div).addClass('fade-all');
                        layer.events.register('loadend', this, function loadend() {
                            layer.events.unregister('loadend', this, loadend);
                            Ext.get(layer.div).removeClass('fade-all');
                        });
                    }
                }
            });
            this.mapPanel.layers.on({
                "update": function(){
                    this.modified |= 1;
                },
                "add": function(){
                    this.modified |= 1;
                },
                "remove": function(store, rec){
                    this.modified |= 1;
                },
                scope: this
            });
        });
        this.on("ready", this.loadLayerSources, this);
        Lang.registerLinks();
        GeonodeViewer.superclass.initPortal.call(this);
    },
    updateURL: function(){
        /* PUT to this url to update an existing map */
        return this.rest + this.mapID + '/data';
    },
    
    /** api: method[save]
     *  :arg as: ''Boolean'' True if map should be "Saved as..."
     *
     *  Subclasses that load config asynchronously can override this to load
     *  any configuration before applyConfig is called.
     */
    save: function(as){
        var config = this.getState();
        
        if (!this.mapID || as) {
            /* create a new map */
            Ext.Ajax.request({
                url: this.rest,
                method: 'POST',
                jsonData: config,
                success: function(response, options){
                    var id = response.getResponseHeader("Location");
                    // trim whitespace to avoid Safari issue where the trailing newline is included
                    id = id.replace(/^\s*/, '');
                    id = id.replace(/\s*$/, '');
                    id = id.match(/[\d]*$/)[0];
                    this.mapID = id; //id is url, not mapID
                    this.fireEvent("saved", id);
                },
                scope: this
            });
        }
        else {
            /* save an existing map */
            Ext.Ajax.request({
                url: this.updateURL(),
                method: 'PUT',
                jsonData: config,
                success: function(response, options){
                    /* nothing for now */
                    this.fireEvent("saved", this.mapID);
                },
                scope: this
            });
        }
    },
    addConnectionHandlers: function(){
        // global request proxy and error handling
        Ext.util.Observable.observeClass(Ext.data.Connection);
        Ext.data.Connection.on({
            "beforerequest": function(conn, options){
                // use django's /geoserver endpoint when talking to the local
                // GeoServer's RESTconfig API
                var urls = (options.url instanceof Array) ? options.url.slice() : [options.url];
                options.url = [];
                for (var i = urls.length - 1; i >= 0; i--) {
                    var url = urls[i].replace(this.urlPortRegEx, "$1/");
                    if (this.localGeoServerBaseUrl) {
                        if (url.indexOf(this.localGeoServerBaseUrl) == 0) {
                            // replace local GeoServer url with /geoserver/
                            options.url.push(url.replace(
                                new RegExp("^" + this.localGeoServerBaseUrl),
                                "/geoserver/"
                            ));
                            return;
                        }
                        var localUrl = this.localGeoServerBaseUrl.replace(
                            this.urlPortRegEx, "$1/");
                        if(url.indexOf(localUrl + "rest/") === 0) {
                            options.url.push(url.replace(new RegExp("^" +
                                localUrl), "/geoserver/"));
                            return;
                        }
                    }
                    // use the proxy for all non-local requests
                    if(this.proxy && url.indexOf(this.proxy) !== 0 &&
                            url.indexOf(window.location.protocol) === 0) {
                        var parts = url.replace(/&$/, "").split("?");
                        var params = Ext.apply(parts[1] && Ext.urlDecode(
                            parts[1]) || {}, options.params);
                        url = Ext.urlAppend(parts[0], Ext.urlEncode(params));
                        delete options.params;
                        options.url.push(this.proxy + encodeURIComponent(url));
                    }
                }
                if(!options.url.length){
                    options.url = (urls.length == 1) ? urls[0] : urls;
                }
            },
            "requestexception": function(conn, response, options){
                if (options.failure) {
                    // exceptions are handled elsewhere
                }
                else {
                    var url = options.url;
                    if (response.status == 401 && url.indexOf("http" != 0) &&
                    url.indexOf(this.proxy) === -1) {
                        var csrfToken, csrfMatch = document.cookie.match(/csrftoken=(\w+);/);
                        if (csrfMatch && csrfMatch.length > 0) {
                            csrfToken = csrfMatch[1];
                        }
                        this.showLoginForm(csrfToken);
                    }
                    else 
                        if (response.status != 405 && url != "/geoserver/rest/styles") {
                            // 405 from /rest/styles is ok because we use it to
                            // test whether we're authenticated or not
                            this.displayXHRTrouble(response);
                        }
                }
            },
            scope: this
        });
    },
    registerColorManager: function(){
        // register the color manager with every color field, for Styler
        Ext.util.Observable.observeClass(gxp.form.ColorField);
        gxp.form.ColorField.on({
            render: function(field){
                var manager = new Styler.ColorManager();
                manager.register(field);
            }
        });
    },
    showLoginForm: function(csrfToken){
        var submit = function(){
            form.getForm().submit({
                waitMsg: "Logging in...",
                success: function(form, action){
                    this.setAuthorizedRoles(["ROLE_ADMINISTRATOR"]);
                    win.close();
                    document.cookie = action.response.getResponseHeader("Set-Cookie");
                    // resend the original request
                    Ext.Ajax.request(options);
                },
                failure: function(form, action){
                    var username = form.items.get(0);
                    var password = form.items.get(1);
                    username.markInvalid();
                    password.markInvalid();
                    username.focus(true);
                },
                scope: this
            });
        }.createDelegate(this);
        
        var win = new Ext.Window({
            title: "GeoNode Login",
            modal: true,
            width: 230,
            autoHeight: true,
            layout: "fit",
            items: [{
                xtype: "form",
                autoHeight: true,
                labelWidth: 55,
                border: false,
                bodyStyle: "padding: 10px;",
                url: "/accounts/ajax_login",
                waitMsgTarget: true,
                errorReader: {
                    // teach ExtJS a bit of RESTfulness
                    read: function(response){
                        return {
                            success: response.status == 200,
                            records: []
                        };
                    }
                },
                defaults: {
                    anchor: "100%"
                },
                items: [{
                    xtype: "textfield",
                    name: "username",
                    fieldLabel: "Username"
                }, {
                    xtype: "textfield",
                    name: "password",
                    fieldLabel: "Password",
                    inputType: "password"
                }, {
                    xtype: "hidden",
                    name: "csrfmiddlewaretoken",
                    value: csrfToken
                }, {
                    xtype: "button",
                    text: "Login",
                    inputType: "submit",
                    handler: submit
                }]
            }],
            keys: {
                "key": Ext.EventObject.ENTER,
                "fn": submit
            }
        });
        win.show();
        var form = win.items.get(0);
        form.items.get(0).focus(false, 100);
    },
    displayXHRTrouble: function(response) {
        response.status && Ext.Msg.show({
            title: this.connErrorTitleText,
            msg: this.connErrorText,
            icon: Ext.MessageBox.ERROR,
            buttons: {ok: this.connErrorDetailsText, cancel: true},
            fn: function(result) {
                if(result == "ok") {
                    var details = new Ext.Window({
                        title: response.status + " " + response.statusText,
                        width: 400,
                        height: 300,
                        items: {
                            xtype: "container",
                            cls: "error-details",
                            html: response.responseText
                        },
                        autoScroll: true,
                        buttons: [{
                            text: "OK",
                            handler: function() { details.close(); }
                        }]
                    });
                    details.show();
                }
            }
        });
    },
    loadLayerSources:function(){
            var startSourceId = null;
            for (var id in this.layerSources) {
                source = this.layerSources[id];
                if (source.store && source instanceof gxp.plugins.WMSSource &&
                                source.url.indexOf("/geoserver/wms" === 0)) {
                    startSourceId = id;
                    source.store.on("load", function() {
                        source.store.filterBy(function(rec) {
                            var name = rec.get('name');
                            return !(new RegExp("geonode:_map_[0-9]+_annotations").test(name) ||
                                new RegExp("geonode:annotations_[0-9]+").test(name));
                        }, this);
                    }, this);
                }
            }
            // find the add layers plugin
            var addLayers = null;
            for (var key in this.tools) {
                var tool = this.tools[key];
                if (tool.ptype === "gxp_addlayers") {
                    addLayers = tool;
                    addLayers.startSourceId = startSourceId;
                }
            }
            var urlParts = window.location.href.split("?"), fromLayer;
            if (urlParts.length > 1) {
                fromLayer = Ext.urlDecode(urlParts[1]).layer;
                if (fromLayer) {
                    //if the startSource is lazy then
                    //change the url to use virtual services
                    var source = this.layerSources[startSourceId];
                    if(source.lazy){
                        lyrParts = fromLayer.split(':');
                        //fix layer name since Geoserver 2.2+ returns only local names when using virtual services
                        fromLayer = lyrParts[1];
                        source.store.url = 
                            source.store.url.replace(/(geoserver)(\/.*?)(wms)/,
                                function(str,gs,mid,srv){return [gs].concat(lyrParts,srv).join('/');}
                            );
                        source.store.proxy.setUrl(source.store.url);
                    }
                    this.createLayerRecord({
                        source: startSourceId,
                        name: fromLayer
                    }, function(record) {
                        this.mapPanel.layers.add([record]);
                        this.mapPanel.map.zoomToExtent(record.getLayer().maxExtent);
                    }, this);
                }
            }
            if (!fromLayer && !this.mapID) {
                if (addLayers !== null) {
                    addLayers.showCapabilitiesGrid();
                }
            }

        }
});

Ext.reg('gn_viewer',GeonodeViewer);

// add old ptypes
Ext.preg("gx_wmssource", gxp.plugins.WMSSource);
Ext.preg("gx_olsource", gxp.plugins.OLSource);
Ext.preg("gx_googlesource", gxp.plugins.GoogleSource);
