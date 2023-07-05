import sqlite3

connection = sqlite3.connect('database.db')


with open('schema.sql') as f:
    connection.executescript(f.read())

cur = connection.cursor()

cur.execute("INSERT INTO filters (primary_filter, secondary_filter, name, description, img_path) VALUES (?, ?, ?, ?, ?)",
            ('PREPARATION;REGRADING', 'the;door', "Super filter", "Super filter filters some values", "static/css/images/1.png")
            )

cur.execute("INSERT INTO filters (primary_filter, secondary_filter, name, description, img_path) VALUES (?, ?, ?, ?, ?)",
            ('ACTION SUBMITTALS', 'plans;sections,',"Mega Filter", "Mega filter filters some values", "static/css/images/1.png")
            )

connection.commit()
connection.close()