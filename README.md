# ETD catalog viewer

A single static page that reads a repository catalog item from
[archive.org/details/etd-catalogs](https://archive.org/details/etd-catalogs)
entirely in your browser (the items serve CORS) and renders every thesis with
links to the live site and the Wayback Machine.

Usage: `https://internetarchivecanada.github.io/etd-viewer/?item=<identifier>`

Example:
[?item=etd-catalog-cardinalscholar-bsu-edu](https://internetarchivecanada.github.io/etd-viewer/?item=etd-catalog-cardinalscholar-bsu-edu)

Part of the Internet Archive Europe ETD project
(contact beatrice@internetarchive.eu). No server, no build: the page streams
the item's `records.jsonl` and renders client-side.
