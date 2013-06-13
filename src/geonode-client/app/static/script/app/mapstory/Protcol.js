/*jslint browser: true, nomen: true, indent: 4, */
/*global Ext, jQuery, OpenLayers,mapstory */

/**
 * @requires OpenLayers.Protocol
 * 
 */

(function (window) {
    'use strict';

    // requires ie 8 and up
    // uses JSON.parse and JSON.stringify which are currently
    // supported in ie 8
    // see http://caniuse.com/#search=JSON for more details

    Ext.ns('mapstory.notes');
    var notes = mapstory.notes;

    /**
     * @constructor
     * @param {String} message
     */
    notes.ParseError = function (message) {
        this.message = message;
    };

    /**
     * @return {String} message.
     */
    notes.ParseError.prototype.toString = function () {
        return this.message;
    };

    /** Handles the low level reading and writing of mapstory's
     *  annotations features
     * @constructor
     */
    notes.Format = function (options) {
        if (!options) { options = {}; }
        this.geometryColumn = options.geometryColumn || 'the_geom';
    };

    /** Provides a method that returns a point object from an array
     *  @param {array} coordinates
     *  @return {OpenLayers.Geometry.Point}
     */
    notes.Format.prototype.parsePoint = function (coordinates) {
        return new OpenLayers.Geometry.Point(coordinates[0], coordinates[1]);
    };

    /** Converts an array into a line type.
     *  @param {array} coordinates
     *  @param {OpenLayer.Class} Cls
     *  @return {OpenLayers.Geometry}
     */
    notes.Format.prototype.parseLine = function (coordinates, Cls) {
        var points = [];
        coordinates.forEach(function (element) {
            points.push(this.parsePoint(element));
        }, this);

        if (!Cls) {
            Cls = OpenLayers.Geometry.LineString;
        }

        return new Cls(points);
    };

    /**
     * @param {Array} coordinates
     * @return {OpenLayers.Geometry.LineString}
     */
    notes.Format.prototype.parseLineString = function (coordinates) {
        return this.parseLine(coordinates);
    };

    /**
     * @param {Array} coordinates
     * @return {OpenLayers.Geometry.LinearRing} ring.
     */
    notes.Format.prototype.parseLinearRing = function (coordinates) {
        return this.parseLine(coordinates, OpenLayers.Geometry.LinearRing);
    };

    /**
     * @param {Array} coordinates
     * @return {OpenLayers.Geometry.Polygon}
     */
    notes.Format.prototype.parsePolgyon = function (coordinates) {
        var outerRing = this.parseLinearRing(coordinates[0]);
        return new OpenLayers.Geometry.Polygon([outerRing]);
    };

    /**
     * @param {Object} geometry
     * @return {OpenLayers.Geometry}
     */
    notes.Format.prototype.parseJSON = function (geometry) {

        if (typeof geometry === 'string') {
            geometry = JSON.parse(geometry);
        }

        switch (geometry.type.toLowerCase()) {
        case 'point':
            return this.parsePoint(geometry.coordinates);
        case 'linestring':
            return this.parseLineString(geometry.coordinates);
        case 'polgyon':
            return this.parsePolgyon(geometry.coordinates);
        default:
            throw new notes.ParseError();
        }
    };

    /**
     * @param {String} str
     * @return {OpenLayers.Feature.Vector}
     */
    notes.Format.prototype.read = function (str) {
        var geom, geomColumn;

        if (typeof str === 'string') {
            str = JSON.parse(str);
        }

        geomColumn = str[this.geometryColumn];
        geom = this.parseJSON(geomColumn);

        // this is hard coded, figure out why the protocol
        geom.transform(
            'EPSG:4326',
            'EPSG:900913'
        );

        return new OpenLayers.Feature.Vector(
            geom,
            str
        );
    };

    /**
     * @param {String} array_str
     * @return {Array}
     */
    notes.Format.prototype.readArray = function (array_str) {
        var array = JSON.parse(array_str),
            features = [];

        array.forEach(function (thing) {
            features.push(this.read(thing));
        }, this);

        return features;
    };

    notes.Format.prototype.write = function (features) {
        return {
            the_geom: {
                type: 'Point',
                coordinates: [
                    -74.00
                ]
            }
        };
    };

    notes.Protocol = OpenLayers.Class(OpenLayers.Protocol, {
        /**
         * @constructor
         */
        initialize: function (options) {
            this.http = options.http || OpenLayers.Request;
            this.response = options.response || OpenLayers.Protocol.Response;
            this.format   = new notes.Format();

            if (!options.mapConfig) {
                throw {
                    'name': 'MapstoryError',
                    'message': 'You must provide an map config object'
                };
            }

            this.mapConfig = options.mapConfig;
            this.baseUrl = '/maps/' + this.mapConfig.id + '/annotations';
            OpenLayers.Protocol.prototype.initialize.apply(this, arguments);

        },

        destory: function () {
            OpenLayers.Protocol.prototype.destory.apply(this);
        },

        read: function (options) {
            OpenLayers.Protocol.prototype.read.apply(this, arguments);
            var resp = new this.response({
                requestType: 'read'
            });

            resp.priv = this.http.GET({
                url: this.baseUrl,
                callback: this.createCallback(this.readFeatures, resp, options)
            });

            return resp;

        },

        readFeatures: function (resp, options) {
            resp.features = this.format.readArray(
                resp.priv.responseText
            );
            options.callback.call(options.scope, resp);

        },

        create: function (feature) {
            var resp = this.http.POST({
                url: this.baseUrl,
                data: feature
            });
            return resp;
        },

        update: function (feature) {
            var resp = this.http.PUT({
                url: this.baseUrl + '/' + feature.id,
                data: feature
            });
            return resp;
        },

        'delete': function (feature) {
            var resp = this.http.DELETE({
                url: this.baseUrl + '/' + feature.id
            });
            return resp;
        },

        CLASS_NAME: 'mapstory.notes.Protocol'

    });


}(window));
