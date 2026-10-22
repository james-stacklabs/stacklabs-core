# Stopping this from happening again

The root cause wasn't carelessness — it's that a 7,800-line file is too big for any agent
(or person) to hold in working context, so duplication and dead code creep in without anyone
noticing. The fix is structural, not "be more careful":

1. **Never let a router file grow past ~500-600 lines.** When one does, that's the signal to
   split it again by sub-domain (e.g. if cmdb.py grows, split CMDB hardware/software/persona
   tables into separate files). brand.py is already at 1,388 lines because onboard_brand_stack
   is a single 1,170-line function — that's the next thing worth decomposing, but do it as its
   own deliberate pass, not while doing something else.

2. **Before adding a new route, grep for the path first.** One line, costs nothing:
   `grep -rn '"/api/your/new/path"' routers/`
   This is literally what would have caught the duplicate `/api/teams` and the double
   `voice_heal_service` inclusion before they shipped.

3. **Run `pyflakes .` after every edit, before calling a task done.** It would have caught the
   `LOG_FILE` bug (undefined name, used in a route, never defined — would crash on every call)
   the moment it was introduced, instead of it sitting silent for however long it's been there.
   It's a 2-second check: `pip install pyflakes && python3 -m pyflakes .`

4. **New DB code uses `core.db.get_db()`, not raw `sqlite3.connect(DB_PATH)`.** The pattern's
   already there now — using it going forward costs nothing and stops the 93-copies problem
   from recurring.

5. **One router per file, by domain, in `routers/`.** Don't add new top-level routes to
   `sovereign_core_api.py` itself — it's app wiring now, not business logic. A new feature gets
   a new file in `routers/` or gets added to the existing domain file it belongs to.

None of this requires more discipline from Antigravity on any single task — it requires the
codebase to make the right thing the easy thing, which is what the file split above does.
