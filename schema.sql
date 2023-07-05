DROP TABLE IF EXISTS filters;

CREATE TABLE filters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    primary_filter TEXT NOT NULL,
    secondary_filter TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    img_path TEXT NOT NULL
);