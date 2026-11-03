# CHECKPOINT (Rocket Hideout spinner arrows visible = ROM 0172; 2026-11-03)
Newest ROM: build/0172-hideout-arrows/s.nds = 0171 + tools/hideout_arrows.py (SHA-256 6671c12982b9...). Copy for the owner: downloads/"Pokemon Psyduck Yellow 0-1-6-8.nds" (not yet on the SD card; the published BETA 0.1.6.8 is still the 0170/0171 build).
Area: Rocket Hideout B2F/B3F spinner mazes. The slide triggers existed since 0099 but the floor under them was plain, so the owner could not see the arrows or their direction.
Now: every arrow tile (a 2x2 block) has a flat red pad with a white arrow pointing the way the slide starts (first move of pokeyellow's own list): 43 arrows on B2F (16 up, 6 down, 12 left, 9 right), 16 on B3F (5 up, 2 down, 1 left, 8 right). Four new textures/materials appended to the floors' texture banks; the stored floor models (with the stair pads) and the bank are regenerated and compared byte for byte before any change.
Tested (emulator fixture): screenshots of B2F and B3F show the arrows; stepping onto B2F's right arrow slid the player from (26,41) to (34,42).
To test on the 3DS: go down the Hideout to B2F/B3F: look for the red pads; step on one and check the push matches its arrow.
Known gaps: the Lift Key/elevator, the Hideout item balls and TM balls are still deferred; Game Corner slot machines hang when pressed (see the plan file: do not press A on them); not tried on real hardware.
Next: Silph Scope -> Tower; Game Corner machine stub; Cycling Road unchecked; polish list in the plan file.
