(function (root, factory) {
    "use strict";
    const api = factory();
    if (typeof module === "object" && module.exports) {
        module.exports = api;
    } else {
        root.AMBCollectionSearch = api;
    }
})(typeof self !== "undefined" ? self : this, function () {
    "use strict";

    function normalize(value) {
        return String(value || "").toLocaleLowerCase().trim();
    }

    function buildIndex(records, elasticlunrLibrary) {
        const index = elasticlunrLibrary(function () {
            this.setRef("item_id");
            this.addField("artist");
            this.addField("title");
            this.addField("nationality");
            this.saveDocument(false);
        });
        records.forEach(function (record) {
            index.addDoc(record);
        });
        return index;
    }

    function find(records, index, query) {
        const normalizedQuery = normalize(query);
        if (!normalizedQuery) {
            return [];
        }

        const matchingIds = new Set();
        index
            .search(query, {
                fields: {
                    artist: { boost: 3 },
                    title: { boost: 2 },
                    nationality: { boost: 1 },
                },
                expand: true,
            })
            .forEach(function (result) {
                matchingIds.add(result.ref);
            });

        records.forEach(function (record) {
            const directMatch = [record.artist, record.title, record.nationality].some(
                function (value) {
                    return normalize(value).includes(normalizedQuery);
                }
            );
            if (directMatch) {
                matchingIds.add(record.item_id);
            }
        });

        return records
            .filter(function (record) {
                return matchingIds.has(record.item_id);
            })
            .sort(function (left, right) {
                return (
                    left.artist.localeCompare(right.artist, undefined, {
                        sensitivity: "base",
                    }) ||
                    left.title.localeCompare(right.title, undefined, {
                        sensitivity: "base",
                    })
                );
            });
    }

    return {
        buildIndex: buildIndex,
        find: find,
        normalize: normalize,
    };
});
