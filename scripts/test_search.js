"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

assert(
    Number.parseInt(process.versions.node.split(".")[0], 10) >= 18,
    "Node.js 18 or newer is required"
);

const projectRoot = path.resolve(__dirname, "..");
const browserScript = fs.readFileSync(
    path.join(projectRoot, "static/js/collection-search.js"),
    "utf8"
);
const browserProgram = new vm.Script(browserScript, {
    filename: "collection-search.js",
});

const elasticContext = { console: console };
vm.createContext(elasticContext);
vm.runInContext(
    fs.readFileSync(
        path.join(projectRoot, "static/search/elasticlunr.min.js"),
        "utf8"
    ),
    elasticContext
);

const searchCore = require(
    path.join(projectRoot, "static/js/collection-search-core.js")
);
const payload = JSON.parse(
    fs.readFileSync(
        path.join(projectRoot, "static/search/collection-records.json"),
        "utf8"
    )
);
assert.equal(payload.records.length, 151);

const index = searchCore.buildIndex(payload.records, elasticContext.elasticlunr);
assert.deepEqual(Array.from(index.getFields()), ["artist", "title", "nationality"]);

for (const query of ["landscape", "utch", "portrait of", "Rubens"]) {
    const expectedDirect = payload.records.filter(function (record) {
        return [record.artist, record.title, record.nationality].some(function (value) {
            return searchCore.normalize(value).includes(searchCore.normalize(query));
        });
    });
    const actual = searchCore.find(payload.records, index, query);
    const actualIds = new Set(actual.map((record) => record.item_id));

    assert.equal(actualIds.size, actual.length, `duplicate results for ${query}`);
    expectedDirect.forEach(function (record) {
        assert(actualIds.has(record.item_id), `missing substring result for ${query}`);
    });
    for (let position = 1; position < actual.length; position += 1) {
        const previous = actual[position - 1];
        const current = actual[position];
        const comparison =
            previous.artist.localeCompare(current.artist, undefined, {
                sensitivity: "base",
            }) ||
            previous.title.localeCompare(current.title, undefined, {
                sensitivity: "base",
            });
        assert(comparison <= 0, `results are not artist-sorted for ${query}`);
    }
}

assert.deepEqual(searchCore.find(payload.records, index, "   "), []);

async function testBrowserInitialization() {
    const input = { disabled: true, value: "" };
    const submitButton = { disabled: true };
    const status = { textContent: "" };
    const results = {
        replaceChildren: function () {},
    };
    const form = {
        dataset: {
            collectionUrl: "https://example.test/collection/",
            recordsUrl: "https://example.test/search/collection-records.json",
            siteUrl: "https://example.test/",
        },
        addEventListener: function () {},
    };
    const elements = {
        "collection-search-form": form,
        "collection-search-query": input,
        "collection-search-submit": submitButton,
        "collection-search-status": status,
        "collection-search-results": results,
    };
    const browserContext = {
        AMBCollectionSearch: searchCore,
        URL: URL,
        console: console,
        document: {
            getElementById: function (id) {
                return elements[id] || null;
            },
        },
        elasticlunr: elasticContext.elasticlunr,
        fetch: function (url) {
            assert.equal(url, form.dataset.recordsUrl);
            return Promise.resolve({
                ok: true,
                json: function () {
                    return Promise.resolve(payload);
                },
            });
        },
        window: {
            history: {
                replaceState: function () {},
            },
            location: {
                href: "https://example.test/search/",
            },
        },
    };
    vm.createContext(browserContext);
    browserProgram.runInContext(browserContext);
    await new Promise((resolve) => setImmediate(resolve));

    assert.equal(input.disabled, false, "search input was not enabled");
    assert.equal(submitButton.disabled, false, "search button was not enabled");
    assert.equal(
        status.textContent,
        "Enter a word or phrase to search the collection."
    );
}

testBrowserInitialization()
    .then(function () {
        console.log("Collection search checks passed");
    })
    .catch(function (error) {
        console.error(error);
        process.exitCode = 1;
    });
