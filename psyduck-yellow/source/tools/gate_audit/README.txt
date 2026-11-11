TEST-ONLY static gate audit (2026-11-08, ROM 0192). Run from yellow-heartgold with PYTHONPATH=tools and .venv/bin/python:
  load.py <rom> maps.pkl      -> pickles every Kanto-flagged map (actors, warps, bg events, triggers); reach.py is the BFS library (tile collision from the land NARC a/0/6/5, matrix header layer picks the map id per chunk, warps jump to the anchor warp of the destination, water 0x10/0x15 needs Surf)
  layers.py <rom> maps.pkl    -> layered gates: all actors are walls; every actor whose removal alone opens new maps is a GATE, then that layer is opened and the search repeats
  orph.py <rom> maps.pkl      -> maps unreachable even with every actor removed, with their incoming warps
Limits: scripts, trigger tiles and hide flags are NOT evaluated (hidden-by-default actors still count as walls), Cut/Strength/ledges/waterfalls are not modelled, Fly is not modelled. Results are in CAMPAIGN-FIRST-PLAN.md (2026-11-08 GATE AUDIT).
