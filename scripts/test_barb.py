import sqlite3
import json

conn = sqlite3.connect("/home/james/stacklabs/dna/sovereign_now.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

def print_row(table, row):
    print(f"\n--- {table} ---")
    if row is None:
        print("None")
        return
    d = dict(row)
    for k, v in d.items():
        print(f"  {k}: {repr(v)}")

# Query warden_barb
cur.execute("SELECT * FROM persona WHERE user_name='warden_barb'")
print_row("persona - warden_barb", cur.fetchone())

cur.execute("SELECT * FROM sys_user WHERE user_name='warden_barb'")
print_row("sys_user - warden_barb", cur.fetchone())

cur.execute("SELECT * FROM cmdb_ci WHERE sys_id='8bea7fb1511f4c9f8181c0b152b87999'")
print_row("cmdb_ci - warden_barb", cur.fetchone())

cur.execute("SELECT * FROM cmdb_ci_ai_persona WHERE sys_id='8bea7fb1511f4c9f8181c0b152b87999'")
print_row("cmdb_ci_ai_persona - warden_barb", cur.fetchone())

# Query barb_the_founder
cur.execute("SELECT * FROM persona WHERE user_name='barb_the_founder'")
print_row("persona - barb_the_founder", cur.fetchone())

cur.execute("SELECT * FROM sys_user WHERE user_name='barb_the_founder'")
print_row("sys_user - barb_the_founder", cur.fetchone())

cur.execute("SELECT * FROM cmdb_ci WHERE sys_id='287a773da7f9446880eadc797d165a16'")
print_row("cmdb_ci - barb_the_founder", cur.fetchone())

cur.execute("SELECT * FROM cmdb_ci_ai_persona WHERE sys_id='287a773da7f9446880eadc797d165a16'")
print_row("cmdb_ci_ai_persona - barb_the_founder", cur.fetchone())

conn.close()
