# galaxy-integration-geforcenow
GoG Galaxy integration for the Geforce Now platform

**Warning: This is an early alpha level version and you shouldn't use it unless you are ok to accept any fallout.  Worst case, it could require a reinstall of GoG Galaxy.**

I'll start off with the problems:

* Uses the "Testing Platform" as there isn't an actual "Geforce Now" platform available.  I've raised a request but wouldn't hold my breath.
* GoG doesn't seem to detect all the games I add properly.  Think this is on their side as other plugin authors complain too.  But also could well be a bug with my code.
* It is Windows only (no Mac support) and assumes that everything is where it expects (i.e. the DB)
* Some supported games may be missed due to differences in how they are named (e.g. Super Duper Edition vs Max Stuff Edition)

My library has 125 games that are compatible with GFNow as far as I can tell.  7 needed a bit of a hint (see `gfn_mappings.csv`), 6 didn't detect properly in Galaxy but do run, 3 have detected as another game with the same name in Galaxy but again do run (The Forest, Portal and Tomb Raider). The rest worked without incident.

Now the features:

* Goes through your game library and adds a Geforce Now platform (well, "Testing Platform" for now) to any games supported in Geforce Now
* No config required, doesn't need your Geforce Now details
* Launch the game within Geforce Now directly from GoG Galaxy (even for the games misidentified)

# Installation

* Download the release
* Unzip into your plugins folder, usually `%LOCALAPPDATA%\GOG.com\Galaxy\plugins\installed`
* Restart GOG Galaxy
* Go to Setting and connect the Testing integration
* Cross fingers

# Plans

- Get GOG to add an actual platform for this
- Sort out the name detection issues
- Improve the detection of compatible games
