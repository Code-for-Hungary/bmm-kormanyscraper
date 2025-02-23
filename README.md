# bmm-kormanyscraper

Egy scraper a Figyusz-hoz, ami a kormany.hu-n megjelenő közadatokat monitorozza.

[kapcsolódó issue](https://github.com/Code-for-Hungary/bmm-frontend/issues/10)

Dropdown menüből kiválasztható szűrőket használ.

A szűrők beállításainak sémáját az `options_schema.json` fájlban találod, amit a db-ben `options_schema`-nak kell beállítani az `eventgenerators` táblában. (a konkrét json fájlt nem használja semmit, csak azért van itt, hogy ne csak az adatbázisban legyen meg)

A scraper a [kormany.hu publikus api](https://kormany.hu/publicapi/document-library)-ját figyeli. Amennyiben ennek a felépítése változik az itt található scrapert és a fent említett options_schema-t frissíteni kellhet.

TODO: kulcsszavas keresés a pdf-ekben

A forráskód a [Közlöny scraper](https://github.com/Code-for-Hungary/bmm-kozlonyscraper)-re alapszik.
