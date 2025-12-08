const chai = require('chai');
const Search = require('../search');
const Promise = require('bluebird');
const should = chai.should();
const sinon = require('sinon');


describe('async-search', () => {
    let search;

    beforeEach(() => {
        search = new Search();
    });

    afterEach(() => {
        search.removeAllListeners();
    });

    it('Should emit the event SEARCH_STARTED when the search starts', (done) => {
        var onStartSpy = sinon.spy();
        search.on('SEARCH_STARTED', onStartSpy);
        search.searchCount('test');

        setTimeout(() => {
            onStartSpy.callCount.should.eql(1);
            onStartSpy.getCall(0).args[0].should.eql('test');
            done();
        }, 20);

    });

    it('Should emit the event SEARCH_ERROR if term passed to the function is falsy', (done) => {
        var onErrorSpy = sinon.spy();
        var onStartSpy = sinon.spy();
        search.on('SEARCH_ERROR', onErrorSpy);
        search.on('SEARCH_STARTED', onStartSpy);
        search.searchCount();

        setTimeout(() => {
            onErrorSpy.callCount.should.eql(1);
            onStartSpy.callCount.should.eql(0);
            onErrorSpy.getCall(0).args[0].message.should.eql('INVALID_TERM');
            done();
        }, 150);

    });

    it('Should emit the event SEARCH_ERROR if the API service fails with an error', (done) => {
        var onStartSpy = sinon.spy();
        var onErrorSpy = sinon.spy();
        var onSuccessSpy = sinon.spy();
        search.on('SEARCH_STARTED', onStartSpy);
        search.on('SEARCH_ERROR', onErrorSpy);
        search.on('SEARCH_SUCCESS', onSuccessSpy);
        search.searchCount('error');

        setTimeout(() => {
            onStartSpy.callCount.should.eql(1);
            onErrorSpy.callCount.should.eql(1);
            onSuccessSpy.callCount.should.eql(0);
            onErrorSpy.getCall(0).args[0].message.should.eql('CONNECTION_ERROR');
            onErrorSpy.getCall(0).args[0].term.should.eql('error');
            done();
        }, 150);
    });

    it('Should emit the event SEARCH_SUCCESS with the result', (done) => {
        var onErrorSpy = sinon.spy();
        var onSuccessSpy = sinon.spy();
        search.on('SEARCH_ERROR', onErrorSpy);
        search.on('SEARCH_SUCCESS', onSuccessSpy);
        search.searchCount('term');

        setTimeout(() => {
            onErrorSpy.callCount.should.eql(0);
            onSuccessSpy.callCount.should.eql(1);
            onSuccessSpy.getCall(0).args[0].count.should.be.a('number');
            onSuccessSpy.getCall(0).args[0].term.should.eql('term');
            done();
        }, 150);
    });

});
