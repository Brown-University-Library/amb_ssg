(function () {
    "use strict";

    const form = document.getElementById("collection-search-form");
    if (!form) {
        return;
    }

    const input = document.getElementById("collection-search-query");
    const submitButton = document.getElementById("collection-search-submit");
    const status = document.getElementById("collection-search-status");
    const resultsContainer = document.getElementById("collection-search-results");
    const batchSize = 24;
    let records = [];
    let index = null;

    function collectionUrl(record) {
        return form.dataset.collectionUrl + record.slug + "/";
    }

    function imageUrl(record) {
        return record.image ? new URL(record.image, form.dataset.siteUrl).href : null;
    }

    function createResult(record) {
        const article = document.createElement("article");
        article.className = "search-result";

        const imageLink = document.createElement("a");
        imageLink.className = "search-result__image-link";
        imageLink.href = collectionUrl(record);

        const source = imageUrl(record);
        if (source) {
            const image = document.createElement("img");
            image.className = "search-result__image";
            image.src = source;
            image.alt = record.title + ", by " + record.artist;
            image.loading = "lazy";
            image.decoding = "async";
            imageLink.appendChild(image);
        } else {
            const placeholder = document.createElement("span");
            placeholder.className = "search-result__placeholder";
            placeholder.textContent = "Image unavailable";
            imageLink.appendChild(placeholder);
        }

        const body = document.createElement("div");
        body.className = "search-result__body";

        const identifier = document.createElement("p");
        identifier.className = "search-result__id";
        identifier.textContent = record.item_id;

        const heading = document.createElement("h2");
        heading.className = "search-result__title";
        const link = document.createElement("a");
        link.href = collectionUrl(record);
        link.textContent = record.title;
        heading.appendChild(link);

        const artist = document.createElement("p");
        artist.className = "search-result__artist";
        artist.textContent = record.artist;

        body.append(identifier, heading, artist);
        if (record.artist_dates) {
            const dates = document.createElement("p");
            dates.className = "search-result__dates";
            dates.textContent = record.artist_dates;
            body.appendChild(dates);
        }
        if (record.nationality) {
            const nationality = document.createElement("p");
            nationality.className = "search-result__nationality";
            nationality.textContent = record.nationality;
            body.appendChild(nationality);
        }

        article.append(imageLink, body);
        return article;
    }

    function appendBatch(matches, start) {
        const end = Math.min(start + batchSize, matches.length);
        const fragment = document.createDocumentFragment();
        matches.slice(start, end).forEach(function (record) {
            fragment.appendChild(createResult(record));
        });
        resultsContainer.appendChild(fragment);

        if (end < matches.length) {
            const more = document.createElement("button");
            more.className = "search-results__more";
            more.type = "button";
            more.textContent =
                "Show " + Math.min(batchSize, matches.length - end) + " more";
            more.addEventListener("click", function () {
                more.remove();
                appendBatch(matches, end);
            });
            resultsContainer.appendChild(more);
        }
    }

    function render(matches, query) {
        resultsContainer.replaceChildren();
        if (!matches.length) {
            status.textContent = 'No works found for “' + query + '.”';
            return;
        }

        status.textContent =
            matches.length === 1
                ? '1 work found for “' + query + '.”'
                : matches.length + ' works found for “' + query + '.”';
        appendBatch(matches, 0);
    }

    function search(query) {
        if (!index) {
            status.textContent = "Collection search is still loading.";
            return;
        }
        if (!AMBCollectionSearch.normalize(query)) {
            resultsContainer.replaceChildren();
            status.textContent = "Enter a word or phrase to search the collection.";
            return;
        }

        const matches = AMBCollectionSearch.find(records, index, query);
        render(matches, query.trim());
    }

    function updateAddress(query) {
        const url = new URL(window.location.href);
        if (query.trim()) {
            url.searchParams.set("q", query.trim());
        } else {
            url.searchParams.delete("q");
        }
        window.history.replaceState({}, "", url);
    }

    form.addEventListener("submit", function (event) {
        event.preventDefault();
        updateAddress(input.value);
        search(input.value);
    });

    status.textContent = "Loading collection search…";
    fetch(form.dataset.recordsUrl)
        .then(function (response) {
            if (!response.ok) {
                throw new Error("Could not load collection records");
            }
            return response.json();
        })
        .then(function (payload) {
            records = payload.records;
            index = AMBCollectionSearch.buildIndex(records, elasticlunr);

            input.disabled = false;
            submitButton.disabled = false;
            const query = new URL(window.location.href).searchParams.get("q") || "";
            input.value = query;
            search(query);
        })
        .catch(function (error) {
            console.error("Collection search initialization failed:", error);
            status.textContent =
                "Collection search could not be loaded. Please use an alphabetical browse page.";
        });
})();
