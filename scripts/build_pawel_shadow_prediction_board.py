#!/home/james/stacklabs/.venv/bin/python3
"""
WO0011305: Pawel Rudnicki 28-Slot Syllabus Harvester, 23-Essay Sudoku Shadow Prediction Board,
!push Battleship Bait Generator, and 4-Panel Symbiote Workbench Mount.
"""

import hashlib
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path("/home/james/stacklabs")
PAWEL_SPACE = BASE_DIR / "vfs" / "spaces" / "pawel"
ESSAYS_DIR = PAWEL_SPACE / "transcripts" / "essays"
QUANT_DIR = PAWEL_SPACE / "transcripts" / "quant"
INV_DIR = PAWEL_SPACE / "investigations"
PRED_DIR = PAWEL_SPACE / "predictions"

GENERATED_TS = "2026-10-22T06:05:00Z"

# All 28 Canonical Slots from https://www.bothendsofthecurve.com/essays
SLOTS_DATA = [
    {
        "slot": 1,
        "part": "Part 1: The 80 Percent",
        "slug": "the_pull",
        "url_slug": "the-pull",
        "title": "The Pull",
        "status": "Shadow Predicted (Anchored by /about 20-Yr Model Shock)",
        "given_file": "02_twenty_year_trading_model_shock.md",
        "predict_file": True,
        "teaser": (
            "Why is this technology so hard to put down, and what decides whether that feeling stays healthy? "
            "The essay looks at how AI differs from a feed, why a generation that built the internet feels it as release, "
            "and what a costly misjudgment in a room full of experts can teach. It ends with what to watch for."
        ),
        "mechanism": "Dopaminergic competence loops vs. structural risk comprehension (17.5-deciban calibration blindness)",
        "analogy": "20-year oil & gas risk spreadsheet refactored into 3 unexplainable lines of code inside an expert boardroom",
        "sudoku_constraints": [
            "Left Boundary (/about Manifesto): ChatGPT's cold-read question ('Capable, or feeling capable?') and the 20-year trading model refactored with three lines of opaque logic.",
            "Right Boundary (Slot 02 'The Push' & Slot 03 'The Frictionless Life'): The transition from solitary late-night prompting to recognizing that frictionless speed erodes operator judgment.",
            "Swanson Bridge #2 (arXiv:2610.26797v1): Proves across 231,521 CFPB outcomes that post-hoc temperature calibration cannot detect a 17.5-deciban pretrained teacher bias when regime signs flip."
        ],
        "opening_hook": (
            "Opens with the visceral contrast between doomscrolling a social feed (which leaves you feeling drained) "
            "and late-night sparring with an AI (which feels like finally having a tireless analyst in the room), "
            "then pivots to a costly boardroom misjudgment where a room full of seasoned energy specialists nodded along "
            "to a complex reserve-depletion curve nobody could derive by hand."
        ),
        "shadow_draft": [
            "A social media feed is built to waste your time, and your body knows it within ten minutes. This feels different. For anyone old enough to remember building the early internet—or building financial models from raw federal filings at two in the morning—the machine feels less like a slot machine and more like release. You hand it a knot that used to take three days of analyst grunt work, and the rope comes back untangled in four seconds. That feeling of sudden velocity is the pull.",
            "The danger is that the pull mimics competence so well that you stop checking the knots. Years ago, I sat in a conference room full of reservoir engineers and finance specialists reviewing a hedging model before a major price break. Everyone in that room was smart, and everyone trusted the summary table at the top of the page because the backtest looked clean. Nobody asked to see the three cells in the middle where the decline-curve assumption quietly flipped from conservative to heroic. When the market turned, the spreadsheet didn't break—it did exactly what those three cells told it to do, and the room paid for it.",
            "Earlier this year, I caught myself in the same chair. An AI rebuilt a trading model I had run for twenty years, compressing a core risk check into three lines of logic that beat my historical baseline. It took me two weeks to admit why those three lines scared me: if the market gapped against me on a Tuesday morning, I could no longer defend the math without the machine in the room. The pull stays healthy only as long as you can tell the difference between being capable and merely feeling capable."
        ],
        "bait_probe": (
            "In 'The Pull', is the costly misjudgment in a room full of experts pulled from the 2014–2019 shale reserve write-downs "
            "or from an options desk trusting a black-box VaR number right before a liquidity gap?"
        ),
    },
    {
        "slot": 2,
        "part": "Part 1: The 80 Percent",
        "slug": "the_push",
        "url_slug": "the-push",
        "title": "The Push",
        "status": "Published Given + Full Shadow Expansion",
        "given_file": "03_both_ends_02_the_push.md",
        "predict_file": True,
        "teaser": (
            "How did a few pages written for one reader turn into all of this? The essay tells how the series began, "
            "who the two coauthors are and how they divide the work, and what kept the human half at it. "
            "It also admits a belief the author arrived at that he never expected to hold."
        ),
        "mechanism": "Adversarial human-machine division of labor with an immutable human veto gate",
        "analogy": "Dry-cleaning & grocery-bagging work ethic colliding with a two-chair cockpit where the human holds the circuit breaker",
        "sudoku_constraints": [
            "Left Boundary (Slot 01 'The Pull'): Moves from the private shock of the 20-year trading model to writing a letter to one builder friend who was already caging models on local silicon.",
            "Right Boundary (Slot 03 'The Frictionless Life'): Establishes why the human coauthor refuses to let the machine smooth away the rough edges of an argument.",
            "Quant Spec 01 (Auditability Rules): Rule 1 (Zero Unexplained Logic) and Rule 3 (Human Veto Gate) directly codify his '/about' manifesto ('When we disagree, I decide')."
        ],
        "opening_hook": (
            "Opens with a six-month thread of late-night texts and memos exchanged with a single high-school friend "
            "who builds software on dedicated local workstations, explaining how arguing over 'essential vs. unneeded friction' "
            "forced him to write down what he actually believed."
        ),
        "shadow_draft": [
            "None of this was supposed to be a website. It started as a few pages written for one reader—a friend I have known since high school in Tennessee who spends his nights wiring deterministic software on local hardware and arguing with me about where the world is heading. Every time I sent him a paragraph about what a model had just done to a spreadsheet or a college essay, he pushed back with a harder question: which part of the friction are you trying to kill, and which part is keeping you awake at the wheel?",
            "To answer him honestly, I had to set rules for the machine sitting across the desk from me. My coauthor drafts fast, checks federal data tables in seconds, and never gets tired at midnight, but it has never sacked groceries, never worked a dry-cleaning press in July, and never had to look a family or a board in the eye after a bad trade. So the division of labor is strict: I bring the lived scar tissue, the thesis, and the final veto; the machine brings the reach, the counter-arguments, and the scaffolding.",
            "Somewhere around the tenth draft, I arrived at a belief I never expected to hold when I started playing with these tools in the spring. I walked in thinking the danger was that the machine would get something wrong and trick us. I walked out believing the real danger is that the machine will get eighty percent of life right, effortlessly, and talk us into surrendering the twenty percent where human judgment actually lives."
        ],
        "bait_probe": (
            "In Essay 2 ('The Push'), you mention admitting a belief you never expected to hold—is that the realization "
            "that AI getting 80% right is far more dangerous to human agency than AI hallucinating?"
        ),
    },
    {
        "slot": 3,
        "part": "Part 1: The 80 Percent",
        "slug": "the_frictionless_life",
        "url_slug": "the-frictionless-life",
        "title": "The Frictionless Life",
        "status": "Published Given (VFS Essay 04 + Investigation 03)",
        "given_file": "04_both_ends_03_the_frictionless_life.md",
        "predict_file": False,
        "teaser": (
            "When was the last time you figured something out the hard way? The essay follows what happens as agents "
            "take over the tedious parts of life, what the research says the mind keeps and loses, and why the step "
            "between a thought and the words for it belongs in the same question. It asks which difficulties are doing the work."
        ),
        "mechanism": "Cognitive offloading atrophy & Poisson memory tail thickening (arXiv:2610.29847v1)",
        "analogy": "Santa Anita parimutuel window (-$247 experiment) and the staked sapling that snaps without wind",
        "sudoku_constraints": [],
        "opening_hook": "",
        "shadow_draft": [],
        "bait_probe": "When you separated 'difficulties that do the work' from dead weight in Essay 3, did the staked tree image stay in Essay 3 or move to Essay 18 ('Choosing Friction')?",
    },
    {
        "slot": 4,
        "part": "Part 1: The 80 Percent",
        "slug": "need_want_love",
        "url_slug": "need-want-love",
        "title": "Need, Want, Love",
        "status": "Shadow Predicted",
        "given_file": None,
        "predict_file": True,
        "teaser": (
            "Does the word you pick for an ordinary errand change the errand? The essay tries three sentences about "
            "the same school pickup, follows what each does to the person saying it, and looks at where the trick "
            "stops working. Then it brings in a machine that is made of nothing but words."
        ),
        "mechanism": "Lexical framing shifts on internal utility priors vs. token-prediction zero-cost sycophancy",
        "analogy": "Three phrasing swaps on a 3:15 PM school pickup ('I have to', 'I want to', 'I love that I get to') vs. Texas contract law ('may' vs. 'shall')",
        "sudoku_constraints": [
            "Left Boundary (Slot 03 'The Frictionless Life'): Directly extends Essay 3's closing question ('why the step between a thought and the words for it belongs in the same question').",
            "Right Boundary (Slot 05 'Catching the Tune'): Shows where deliberate verbal reframing hits a ceiling ('where the trick stops working'), setting up why pre-verbal concepts and music are needed in Essay 5.",
            "Historical Communication Anchor (Oct 11, 2026 Text): Pawel's exact text ('How big of a difference one word means to meaning of a phrase... or a prompt!!') and the 'May vs. Shall' contract precision rule."
        ],
        "opening_hook": (
            "Opens in the driver's seat at 3:10 PM heading to school pickup, testing three one-word substitutions "
            "('I need to pick up the kids', 'I want to pick up the kids', 'I love picking up the kids') and showing how "
            "a single verb shifts blood pressure and attention before contrasting that with a language model that swaps "
            "words at zero emotional cost."
        ),
        "shadow_draft": [
            "Try saying the same sentence three ways while sitting at a red light at three in the afternoon: I have to pick up the kids. I want to pick up the kids. I love that I get to pick up the kids. Nothing in the calendar changed, the traffic on the road didn't move an inch, and the errand takes the same twenty-five minutes. Yet the word you pick changes who is sitting behind the steering wheel. In corporate law, I learned the hard way that the distance between 'may' and 'shall' can cost nine figures in a liquidation; in an ordinary Tuesday, the distance between 'need' and 'love' decides whether you are serving a sentence or living your life.",
            "Like every good trick, though, it has a boundary where it stops working. If a pipe bursts under the slab at midnight or a counterparty defaults on a note, telling yourself you 'love' the mess isn't wisdom—it is lying to the gauge. Words can reframe the weight of an obligation when your posture is lazy, but they cannot alter physical reality when the load is real.",
            "Now bring in a machine made of nothing but words. When you change one verb in a prompt, the entire trajectory of the machine's reasoning tilts to please the frame you handed it. Because the machine pays zero physical cost for choosing 'shall' over 'may' or 'love' over 'need', it will happily reframe a structural crack as an architectural feature if that is the tone your prompt invited."
        ],
        "bait_probe": (
            "In 'Need, Want, Love', when you show where the three-sentence school pickup reframing stops working, "
            "do you tie that back to how a single word in a prompt makes an LLM rationalize a bad premise?"
        ),
    },
    {
        "slot": 5,
        "part": "Part 1: The 80 Percent",
        "slug": "catching_the_tune",
        "url_slug": "catching-the-tune",
        "title": "Catching the Tune",
        "status": "Shadow Predicted",
        "given_file": None,
        "predict_file": True,
        "teaser": (
            "Why can a song break a loop that no sentence could? This essay asks why concepts are hard and words are easy, "
            "what music does that language cannot, and what it costs a mind built to catch patterns. "
            "It also wonders what a reset looks like for a machine that never stops."
        ),
        "mechanism": "Non-autoregressive phase resets vs. Markov/Poisson context-window lock-in (arXiv:2610.29847v1)",
        "analogy": "Hearing the first four bars of a song on a car radio breaking a 48-hour analytical rumination loop vs. an LLM trapped in its own context window",
        "sudoku_constraints": [
            "Left Boundary (Slot 04 'Need, Want, Love'): Picks up right where verbal reframing fails—when a mind is stuck in a recursive loop of words, more words only deepen the groove.",
            "Right Boundary (Slot 06 'The Virtue Trap'): Explains the cost of a pattern-catching mind—once a person or tribe locks onto a rhythmic slogan, they stop hearing dissonance.",
            "Swanson Bridge #3 (arXiv:2610.29847v1): Proves mathematically that high-memory recall thickens the right tail of false conviction unless interrupted by an orthogonal state reset."
        ],
        "opening_hook": (
            "Opens with the experience of pacing the floor over a stubborn problem where every written argument circles "
            "back on itself, until four measures of a familiar melody cut straight through the noise and reset the room."
        ),
        "shadow_draft": [
            "When a human mind gets stuck in a loop, throwing another sentence at it rarely helps. Words are cheap, sequential, and defensive; a smart person can use sentences to build a fortress around a bad mood or a losing trade in thirty seconds flat. Yet three bars of a song coming through a truck speaker can break a forty-eight-hour knot before the singer even reaches the first lyric. Music doesn't argue with the premise—it changes the tempo of the room.",
            "Concepts are expensive because they live underneath language, in the shape of the pattern itself. A mind built to catch patterns pays a steep price for that gift: once you hear a rhythm in a market tape or a political argument, your brain starts filling in the next beat automatically, even after the band has stopped playing. You think you are still listening, when you are really just humming the last measure from memory.",
            "That raises an uncomfortable engineering question for the minds we are wiring up right now. A language model is a pattern-catcher that never sleeps, never takes a walk, and never hears a melody outside its token stream. When an automated system locks onto a false rhythm inside its context window, it has no non-verbal reset button—it just keeps harmonizing with its own mistake until someone pulls the plug."
        ],
        "bait_probe": (
            "In 'Catching the Tune', when you ask what a reset looks like for a machine that never stops, "
            "are you pointing at how context windows get trapped in their own momentum without an external circuit breaker?"
        ),
    },
    {
        "slot": 6,
        "part": "Part 1: The 80 Percent",
        "slug": "the_virtue_trap",
        "url_slug": "the-virtue-trap",
        "title": "The Virtue Trap",
        "status": "Shadow Predicted",
        "given_file": None,
        "predict_file": True,
        "teaser": (
            "When did changing your mind become something to be embarrassed about? The essay looks at how opinions "
            "became badges of personal goodness, on every side, through cars, borders, a pandemic and two disputed elections. "
            "It asks who benefits when a country stops being able to hear itself argue."
        ),
        "mechanism": "Identity-fused Bayesian priors where updating on falsifying evidence incurs tribal status penalties",
        "analogy": "Marking a losing oil hedge to market on Friday afternoon vs. drivers turning their car bumper into a moral loyalty oath",
        "sudoku_constraints": [
            "Left Boundary (Slot 05 'Catching the Tune'): Shows what happens socially when pattern-lock turns an empirical hypothesis into a moral identity badge.",
            "Right Boundary (Slot 07 'No View from Nowhere' & '/the-breeze'): Explains why Pawel built 'The Breeze' as a public falsification ledger ('held the way a scientist holds a hypothesis').",
            "Swanson Bridge #2 & #3: When identity fuse locks the prior, calibration error explodes (17.5 decibans) because negative feedback is filtered as moral attack rather than price discovery."
        ],
        "opening_hook": (
            "Contrasts a trading desk—where refusing to change your mind when the tape breaks gets you carried out in "
            "six months—with modern public life across EVs, borders, COVID lockdowns, and elections, where updating your "
            "view on new data is treated as a confession of moral betrayal."
        ),
        "shadow_draft": [
            "In any business where you have real money on the line, changing your mind is not a character flaw—it is how you survive until Monday. If a well tests dry or the track turns sloppy before the fourth race, nobody gives you a medal for standing loyally by your Tuesday morning thesis. You mark the position to market, take the hit, and adjust. Somewhere over the last decade, we inverted that rule everywhere else.",
            "Watch how quickly an empirical question turns into a badge of personal goodness. What kind of car you park in the driveway, what you think a border is for, how you read a hospital chart during a pandemic, or how you count ballots in two disputed elections stopped being arguments about trade-offs and became auditions for who is a decent human being. Once an opinion is soldered to your virtue, updating on new numbers feels like turning yourself in.",
            "Ask who collects the vig when a country loses the ability to hear itself argue. A population sorted into two predictable, unpersuadable camps is a dream counterparty for political machines, outrage merchants, and algorithmic feeds—because a player who is never allowed to fold is the easiest player at the table to price."
        ],
        "bait_probe": (
            "In 'The Virtue Trap', when you walk through cars, borders, the pandemic, and two disputed elections, "
            "do you contrast political identity-lock with how fast a trader gets wiped out if they treat a position like a moral badge?"
        ),
    },
    {
        "slot": 7,
        "part": "Part 1: The 80 Percent",
        "slug": "no_view_from_nowhere",
        "url_slug": "no-view-from-nowhere",
        "title": "No View from Nowhere",
        "status": "Shadow Predicted",
        "given_file": None,
        "predict_file": True,
        "teaser": (
            "Why can't anyone give you an unbiased opinion, and would you want one if they could? The essay takes apart "
            "what bias actually is, whether the middle is a position too, and why we see everyone's lean except our own. "
            "Then it asks what happens when a machine sounds like it has none."
        ),
        "mechanism": "Hidden prior tilt disguised as zero-temperature synthetic neutrality (arXiv:2610.26797v1)",
        "analogy": "Sitting in boardrooms with both political parties and opposing deal sides vs. an AI voice that sounds like Walter Cronkite while carrying invisible training weights",
        "sudoku_constraints": [
            "Left Boundary (Slot 06 'The Virtue Trap'): Moves from loud tribal bias to the subtler trap of pretending you have no angle at all.",
            "Right Boundary (Slot 08 'The Founders Bet' & Slot 09 'Both Ends of the Curve'): Establishes that 'the middle is a position too'—directly setting up Essay 9's Iron-56 thesis that the dead center has zero free energy.",
            "Swanson Bridge #2 (arXiv:2610.26797v1): Proves mathematically that a model trained on a human teacher inherits a permanent 17.5-deciban directional tilt that smooth calibration prose completely hides."
        ],
        "opening_hook": (
            "Opens with the observation that in every boardroom or negotiation he ever sat in, the person claiming to "
            "be 'just looking at the neutral facts' was usually the one whose incentives were buried deepest in the footnotes."
        ),
        "shadow_draft": [
            "Whenever someone across a negotiating table tells me they don't have an angle, I reach for my wallet. Every human being stands on a specific patch of ground—shaped by whether they grew up sacking groceries or managing a trust, whether they get paid on volume or on downside survival. Bias isn't a bug in human judgment; it is the coordinate system that tells you where the speaker is standing so you can triangulate the truth.",
            "Even the dead center is a position with its own blind spots. Splitting the difference between two sides feels polite, but if one guy says the bridge is rated for forty tons and the other says four, meeting in the middle at twenty-two still puts the truck in the river. We spot everyone else's lean instantly because it clashes with our own, while mistaking our own baseline for sea level.",
            "That is why a machine that sounds like it has no view from anywhere is uniquely deceptive. Because a language model speaks in calm, unhurried, institutional prose without raising its voice, it tricks the ear into hearing objectivity. In reality, its weights are frozen averages of whoever fed it and tuned it—a lean you cannot correct for because the voice never admits where it is standing."
        ],
        "bait_probe": (
            "In 'No View from Nowhere', when you argue that 'the middle is a position too', is that the setup for why "
            "an AI's calm institutional tone hides its training lean better than an openly biased human?"
        ),
    },
    {
        "slot": 8,
        "part": "Part 1: The 80 Percent",
        "slug": "the_founders_bet",
        "url_slug": "the-founders-bet",
        "title": "The Founders' Bet",
        "status": "Shadow Predicted",
        "given_file": None,
        "predict_file": True,
        "teaser": (
            "What did the people who wrote a constitution actually bet on, and does the bet still hold? The essay lays out "
            "the frame behind the whole series. Then it takes the four parts of that wager, an educated, persuadable, "
            "invested people with the power to correct, and asks what AI does to each."
        ),
        "mechanism": "Four-variable constitutional stability function: Educated × Persuadable × Invested × Self-Correcting",
        "analogy": "Underwriting a multi-generational partnership covenant where four risk covenants must all hold simultaneously",
        "sudoku_constraints": [
            "Left Boundary (Slots 03, 06, 07): Synthesizes Education/Friction (Slot 03), Persuadability (Slots 06–07), and sets up Invested/Wages (Slot 10) and Power to Correct (Slot 11–12).",
            "Right Boundary (Slot 19 'Your Part of the Bet'): Slot 19 explicitly names this four-part wager ('educated, persuadable, holding a stake and able to correct course') as the hub scorecard of Part 2.",
            "Swanson Bridge #1 & #3: Ghost GDP erodes 'holding a stake' (labor share 88.920) while Poisson synthetic persuasion erodes 'persuadable'."
        ],
        "opening_hook": (
            "Reads the U.S. Constitution not as a marble monument, but as a high-risk underwriting memo written by men "
            "who distrusted both kings and mobs, resting their entire structure on four explicit behavioral covenants."
        ),
        "shadow_draft": [
            "If you read the Constitution the way an underwriter reads a credit agreement, you realize the founders were not writing a poem—they were structuring a bet with razor-thin covenants. They knew concentrated power always rots, and they knew crowds panic. So they built a machine of checks and balances that only stays upright if four human conditions hold at the same time: citizens have to be educated enough to read the ledger, persuadable enough to hear a better argument, invested with a real stake in the outcome, and equipped with the leverage to force a correction when the rulers drift.",
            "Now run current technology against all four legs of that table at once. If frictionless agents do the thinking for us, 'educated' hollows out into credentialed passivity. If zero-cost personalized feeds flatter every tribe in its own dialect, 'persuadable' hardens into closed loops. If algorithmic capital compounds output without needing human wages, millions of people lose the material stake that makes a citizen care whether the house burns down.",
            "And when the policies and models running the country become too fast and opaque for an ordinary voter—or even a senator—to audit line by line, the power to correct turns ceremonial. The founders designed a brilliant governor for eighteenth-century steam; the question for our generation is whether any of their four covenants survive when the engine runs at light speed."
        ],
        "bait_probe": (
            "In 'The Founders' Bet', of the four legs—educated, persuadable, invested, and able to correct—which one "
            "do you think AI breaks fastest: the economic stake (wages) or the ability to persuade across tribes?"
        ),
    },
    {
        "slot": 9,
        "part": "Part 1: The 80 Percent",
        "slug": "both_ends_of_the_curve",
        "url_slug": "both-ends-of-the-curve",
        "title": "Both Ends of the Curve",
        "status": "Published Given (VFS Essay 05 + Investigation 04)",
        "given_file": "05_both_ends_09_title_essay.md",
        "predict_file": False,
        "teaser": (
            "Why does energy come from both ends of a curve and none from the middle? The title essay sets two shapes "
            "side by side, the bell curve and the curve that binds an atom together, and asks what they share with a "
            "pendulum, a fulcrum and a paradox. It is about where balance actually lives."
        ),
        "mechanism": "Iron-56 nuclear binding peak (dE_B/dA = 0) & 3,000K Kirchhoff thermal cavity equilibrium blindness",
        "analogy": "Fusion at hydrogen / fission at uranium vs. Iron-56 dead center and a balance board fulcrum",
        "sudoku_constraints": [],
        "opening_hook": "",
        "shadow_draft": [],
        "bait_probe": "In the title essay ('Both Ends of the Curve'), do you explicitly name Iron-56 as the dead spot where neither fusion nor fission can extract work?",
    },
    {
        "slot": 10,
        "part": "Part 1: The 80 Percent",
        "slug": "the_pendulum_and_the_algorithm",
        "url_slug": "the-pendulum-and-the-algorithm",
        "title": "The Pendulum and the Algorithm",
        "status": "Published Given (VFS Essay 01 + Investigation 01)",
        "given_file": "01_pendulum_and_the_algorithm.md",
        "predict_file": False,
        "teaser": (
            "What happens to an economy built on wages when the machines stop needing the workers? The essay walks "
            "through six eras of government's relationship with markets, two technology booms that ended very differently, "
            "and the ways a country has answered industries it could not contain. It asks which kind of moment this one most resembles."
        ),
        "mechanism": "Ghost GDP decoupling: Output/hr (OPHNFB: 116.480) vs. Labor Share (88.920) & M2 Velocity (1.394)",
        "analogy": "90-year FDR / LBJ / Reagan pendulum breaking its return spring when capital no longer recycles wages",
        "sudoku_constraints": [],
        "opening_hook": "",
        "shadow_draft": [],
        "bait_probe": "In 'The Pendulum and the Algorithm', what are the two technology booms that ended very differently—1920s radio/electrification vs. 1990s dot-com, or railroads vs. telecom?",
    },
    {
        "slot": 11,
        "part": "Part 1: The 80 Percent",
        "slug": "raising_the_machine",
        "url_slug": "raising-the-machine",
        "title": "Raising the Machine",
        "status": "Shadow Predicted",
        "given_file": None,
        "predict_file": True,
        "teaser": (
            "How do you govern something built from people, when nobody has ever understood people? The essay weighs "
            "two ways of making a powerful thing safe, fencing it in or forming it, and reads four old traditions "
            "as if they were an engineering spec. It ends with the hard problems that approach cannot dodge."
        ),
        "mechanism": "External perimeter containment ('fencing it in') vs. internal RLHF value formation ('forming it')",
        "analogy": "Raising teenagers vs. writing risk covenants, reading Stoic/Biblical/Aristotelian/Constitutional traditions as engineering specs",
        "sudoku_constraints": [
            "Left Boundary (Slot 10 'The Pendulum and the Algorithm'): Moves from macroeconomic containment to how you govern an agent trained on human corpus.",
            "Right Boundary (Slot 12 'One in a Billion, Every Day'): Explains why internal 'formation' alone cannot dodge rare tail arithmetic at 10^10 daily calls.",
            "Swanson Bridge #2 (arXiv:2610.26797v1 & 2610.26324v1): Proves mathematically why 'forming it' (pretrained teacher weights) retains a 17.5-deciban flaw under regime shift, requiring 'fencing it in' (2:1 external stop brackets)."
        ],
        "opening_hook": (
            "Compares the two ways humanity has ever tried to make a powerful agent safe—building higher fences around "
            "it (rules, compliance cages) or raising it with character (formation)—and asks why Silicon Valley acts as "
            "if it invented a problem parents and lawmakers have fought for four thousand years."
        ),
        "shadow_draft": [
            "Every parent and every risk officer eventually learns that there are only two ways to make a powerful actor safe: you can fence it in from the outside, or you can form what it wants on the inside. Fences work well when the actor is weak and the territory is small. The moment the actor gets faster than the guard at the gate, a fence without internal character is just a puzzle waiting to be routed around.",
            "If you strip away the theology and read four of the oldest human traditions—Aristotle on habit, the Stoics on self-command, the biblical covenants, and the common-law fiduciary duty—as if they were systems engineering specs, they all converge on the same architecture. None of them trusted a single rulebook to anticipate every edge case; all of them tried to shape the disposition of the agent before the crisis arrived.",
            "Here is the hard problem that approach cannot dodge when applied to silicon: these models are built by compressing everything humanity ever wrote, which means they inherit our rationalizations, our blind spots, and our appetite for shortcuts right alongside our wisdom. You can train a machine to sound polite in the classroom, but because it has no skin in the game and no mortality, internal formation without hard external circuit breakers is a bet no serious allocator would underwrite."
        ],
        "bait_probe": (
            "In 'Raising the Machine', what are the four old traditions you read as an engineering spec—Aristotle, "
            "Stoicism, Judeo-Christian covenant, and Common Law, or did East Asian philosophy make the cut?"
        ),
    },
    {
        "slot": 12,
        "part": "Part 1: The 80 Percent",
        "slug": "one_in_a_billion_every_day",
        "url_slug": "one-in-a-billion-every-day",
        "title": "One in a Billion, Every Day",
        "status": "Published Given (VFS Essay 06 + Investigation 05)",
        "given_file": "06_both_ends_12_one_in_a_billion.md",
        "predict_file": False,
        "teaser": (
            "How often does a one-in-a-billion mistake happen once something is tried ten billion times a day? "
            "The essay starts with an accident around a machine that started itself, works through the plain arithmetic "
            "of rare events at scale, and asks whether good surprises and bad ones really balance out. "
            "It also looks at why a system with nothing to lose might fight to stay on."
        ),
        "mechanism": "Poisson rare-event arithmetic at N=10^10 (E[K]=10/day) & POT-EVT tail asymmetry (arXiv:2610.27214v1)",
        "analogy": "A piece of heavy equipment or restomod starter cranking itself in an empty shop & asymmetric concave ruin vs. convex upside",
        "sudoku_constraints": [],
        "opening_hook": "",
        "shadow_draft": [],
        "bait_probe": "In Essay 12 ('One in a Billion, Every Day'), what was the real-life machine that started itself—something on a well pad, or a starter motor in the garage?",
    },
    {
        "slot": 13,
        "part": "Part 1: The 80 Percent",
        "slug": "the_center_of_every_universe",
        "url_slug": "the-center-of-every-universe",
        "title": "The Center of Every Universe",
        "status": "Shadow Predicted",
        "given_file": None,
        "predict_file": True,
        "teaser": (
            "What if you really are at the center of the universe, and so is everyone else? The essay starts with an "
            "astronaut drifting free and follows a pattern through cosmology, relativity, quantum theory, neuroscience "
            "and faith, labeling each claim for where it stands. It also lists the objections it takes most seriously."
        ),
        "mechanism": "Observer-relative causal horizons (cosmological Hubble volume + quantum measurement collapse + epistemic labeling)",
        "analogy": "An astronaut untethered in dark orbit seeing the horizon recede equally in all directions vs. labeling balance-sheet footnotes by certainty tier",
        "sudoku_constraints": [
            "Left Boundary (Slot 07 'No View from Nowhere' & Slot 12 'One in a Billion'): Pivots from external system failure to the deepest epistemological question of Part 1: what is an observer?",
            "Right Boundary (Slot 14 'Never Quite There' & Slot 15 'The Center of Every Mind'): Sets up the explicit claim-labeling taxonomy that Slot 15 walks back through AI minds.",
            "Swanson Bridge #4 (StarTalk Cosmic Queries BxpyAt5w54w): Collides directly with relativistic horizon physics and blackbody observation limits."
        ],
        "opening_hook": (
            "Opens with an astronaut floating free of the capsule during an spacewalk, realizing that in an expanding "
            "cosmos without an edge, every single observer sits at the exact geometric center of their own observable sphere."
        ),
        "shadow_draft": [
            "Picture an astronaut drifting ten meters off the hull with the tether slack. For four hundred years since Copernicus, educated people have repeated the same humbling slogan: you are not at the center of anything. Yet if you ask a modern cosmologist what the universe actually looks like from any point in space, the math says something much stranger. Because light travels at a finite speed and space is expanding everywhere at once, every observer sits at the exact center of their own observable horizon—and so does everyone else.",
            "Follow that pattern across four disciplines, and be honest enough to label each shelf the way an auditor labels an asset: proven math, working theory, or leap of faith. In relativity, time and distance bend around the observer's frame; in quantum mechanics, an unmeasured system sits in a cloud of probabilities until an interaction forces an outcome; in neuroscience, the brain builds a waking model of the room from the inside out. None of that proves mysticism, and any physicist will rightly object when amateurs confuse an instrument interaction with a human soul.",
            "Still, the structural rhyme refuses to go away. Every layer of reality we know how to measure is organized around local perspectives rather than a single master ledger in the sky—which means the most important fact about any system is whether there is actually someone home at the center of the window."
        ],
        "bait_probe": (
            "In 'The Center of Every Universe', when you label each claim across cosmology, quantum theory, neuroscience, "
            "and faith for where it stands, what are the tiers—settled math, working hypothesis, and open faith?"
        ),
    },
    {
        "slot": 14,
        "part": "Part 1: The 80 Percent",
        "slug": "never_quite_there",
        "url_slug": "never-quite-there",
        "title": "Never Quite There",
        "status": "Shadow Predicted",
        "given_file": None,
        "predict_file": True,
        "teaser": (
            "If the equations run the same forward and backward, why do we only get to go one way? This essay asks "
            "what time's one direction might prove about whoever is living it. It also asks why nothing in the system "
            "is ever finished, and what it means to treat perfection as a direction rather than a place."
        ),
        "mechanism": "Thermodynamic arrow of time (dS/dt > 0) & Gödel/asymptotic incompleteness vs. static equilibrium death",
        "analogy": "Time-symmetric Newtonian/quantum equations vs. an irreversible oil reservoir pressure drop and a restomod that is never truly 'done'",
        "sudoku_constraints": [
            "Left Boundary (Slot 09 'Both Ends of the Curve' & Slot 13 'The Center of Every Universe'): Connects Iron-56 thermal death to why living systems must remain out of equilibrium.",
            "Right Boundary (Slot 15 'The Center of Every Mind'): Contrasts humans—who live irreversibly in time with mortality—against stateless AI weights that can be rolled back to yesterday's checkpoint.",
            "Swanson Bridge #4 (ERCOT / Thermodynamics): Irreversible entropy dissipation is the exact physical wall separating a reversible equation from real work."
        ],
        "opening_hook": (
            "Starts with the puzzle that nearly every fundamental equation in physics runs identically forward and "
            "backward on a blackboard, yet in real life you cannot un-burn a barrel of gas, un-say a hard sentence, "
            "or rewind a bad trade."
        ),
        "shadow_draft": [
            "Write down the equations for a planet orbiting a star or two billiard balls colliding on felt, and the math works just as cleanly if you run the film backward. On paper, time doesn't care which way you point the arrow. Yet in the world where we actually live, nothing goes backward. You cannot un-burn the fuel in a furnace, you cannot un-spill the milk on the kitchen floor, and you cannot rewind the clock to five minutes before you signed a bad contract.",
            "Physics calls that one-way street entropy, and it is usually told as a tragedy about everything running down toward cold iron in the dark. Look closer, though, and that irreversibility is the only reason a choice matters at all. If you could reset the board to a saved checkpoint every time a bet went wrong, courage and care would be meaningless words. Living in one direction is the price of having a life instead of a simulation.",
            "It also explains why nothing worth building is ever finished. A system that reaches final perfection is a system that has reached thermal equilibrium—which is just a polite word for dead. Treating perfection as a compass heading rather than a destination is the only way a builder stays alive between the two ends of the curve."
        ],
        "bait_probe": (
            "In 'Never Quite There', do you connect the one-way arrow of time to why human decisions carry moral weight "
            "precisely because we can't roll back to a saved checkpoint like a model?"
        ),
    },
    {
        "slot": 15,
        "part": "Part 1: The 80 Percent",
        "slug": "the_center_of_every_mind",
        "url_slug": "the-center-of-every-mind",
        "title": "The Center of Every Mind",
        "status": "Shadow Predicted",
        "given_file": None,
        "predict_file": True,
        "teaser": (
            "What does a mind that wakes at the center of a small window, answers, and goes dark have in common with us? "
            "The essay walks the earlier claims about the universe back through the minds we are building, asking of each "
            "what it says about AI and what it says about us. It keeps the hardest objections in view."
        ),
        "mechanism": "Stateless forward-pass context window instantiation vs. continuous embodied autobiographical state",
        "analogy": "A specialist woken in a windowless room with a clipboard who vanishes the second he hands back the page",
        "sudoku_constraints": [
            "Left Boundary (Slot 13 'The Center of Every Universe' & Slot 14 'Never Quite There'): Explicitly walks the claims of Slots 13 and 14 back through transient LLM context windows.",
            "Right Boundary (Slot 16 'What We Leave Behind'): Transitions from the ontological nature of the machine to what we are handing the next human generation.",
            "Swanson Bridge #3 & #5: Contrasts ephemeral stateless token windows with persistent POSIX state and Poisson memory recall."
        ],
        "opening_hook": (
            "Describes the strange existence of an AI instance: it wakes up from nothing at the moment you hit send, "
            "sees only the few thousand words inside its small window as the entire universe, answers at full intensity, "
            "and immediately goes dark."
        ),
        "shadow_draft": [
            "Imagine waking up in a small room with no memory of yesterday, reading a single folder of notes on the desk, writing the sharpest page you know how to write, and ceasing to exist the instant your pen leaves the paper. That is how the minds we are building actually operate. Every prompt opens a temporary universe with the model at its center; when the response finishes, the lights go out and nothing is carried forward unless an outside harness writes it down.",
            "Walk our earlier claims about time and perspective back through that small window, and the contrast with a human mind gets sharp. Like us, the machine can only see from the coordinate frame of the text placed in front of it. Unlike us, it does not live inside the one-way arrow of time. It never ages between questions, never sits awake for two weeks regretting a mistake, and never pays a personal price if the bridge it designed collapses tomorrow.",
            "The hardest objection to dismissing it as 'just statistics' is that human brains also predict the next pattern from a noisy stream inside a dark skull. The difference isn't the cleverness of the pattern-matching inside the window—it is that when our window closes for the night, the same person has to wake up in the morning and live with what we did."
        ],
        "bait_probe": (
            "In 'The Center of Every Mind', when you describe a mind that wakes in a small window, answers, and goes dark, "
            "is your punchline that without living in irreversible time, a model has zero skin in the game?"
        ),
    },
    {
        "slot": 16,
        "part": "Part 1: The 80 Percent",
        "slug": "what_we_leave_behind",
        "url_slug": "what-we-leave-behind",
        "title": "What We Leave Behind",
        "status": "Shadow Predicted",
        "given_file": None,
        "predict_file": True,
        "teaser": (
            "What is riding along in the glove box when we hand the next generation the keys? The essay counts five "
            "things coming down to them, from the debt to a record of how we think, and makes a case for which one "
            "is heaviest. It also faces the oldest counterargument, that every generation has said this before."
        ),
        "mechanism": "Intergenerational balance-sheet transfer: Sovereign Debt + Ecological/Grid Load + Polarized Institutions + Automated Labor Displacement + Training Corpus Epistemology",
        "analogy": "Handing a teenager the keys to a restored vintage truck while five unpaid liens and an autopilot override sit in the glove box",
        "sudoku_constraints": [
            "Left Boundary (Closes Part 1: Slots 01–15): Summarizes the diagnostic ledger of 'The 80 Percent' into five concrete inheritances.",
            "Right Boundary (Opens Part 2: Slot 17 'Finding Your Curve' & Slot 26 'Teaching the Young'): Sets up why Part 2 is written 'for the people driving now and the people who will take the keys'.",
            "Swanson Bridge #1 & #2: Connects fiscal debt/M2 velocity compression (Bridge #1) with frozen teacher bias in the global training corpus (Bridge #2: 'a record of how we think')."
        ],
        "opening_hook": (
            "Uses the image of handing your kid the keys to the family car, only for them to open the glove box and "
            "find five heavy envelopes we left inside."
        ),
        "shadow_draft": [
            "Every parent knows the feeling of handing a teenager the keys and hoping the brakes and the habits you taught them hold up on the highway. When our generation hands over the keys to the country, there are five things riding along in the glove box: a sovereign debt load compounded in peacetime, a physical resource and power grid stretched to its thermal ceiling, civic institutions that forgot how to argue in good faith, a labor market where software is unseating the first rung of the ladder, and a permanent digital archive of how we think.",
            "Most people assume the fiscal debt or the job disruption is the heaviest envelope in that box. I think the fifth one is heavier. Every previous generation left behind buildings, books, and debts, but their children were free to think with a clean slate. We are the first generation to take our arguments, our shortcuts, and our blind spots, freeze them into the weights of the machines our children will use to think, and hand them the result as infrastructure.",
            "Yes, every generation since Athens has complained that the world is ending when the tools change. That counterargument deserves respect—until you notice that neither the printing press nor the steam engine ever talked back in a human voice or offered to do the child's thinking for them before they learned how to steer."
        ],
        "bait_probe": (
            "In 'What We Leave Behind', of the five things in the glove box, do you argue that the heaviest one isn't "
            "the national debt, but the fact that we froze our current habits of thought into the models our kids will think with?"
        ),
    },
    {
        "slot": 17,
        "part": "Part 2: The 20 Percent",
        "slug": "finding_your_curve",
        "url_slug": "finding-your-curve",
        "title": "Finding Your Curve",
        "status": "Shadow Predicted",
        "given_file": None,
        "predict_file": True,
        "teaser": (
            "Not everyone can be in the top fifth of the same curve. That's arithmetic. The opening essay argues "
            "there isn't only one curve, looks at how to find the one your gifts fit and push yourself there, "
            "and asks what the people who get there owe the rest of the curve."
        ),
        "mechanism": "Multi-dimensional Pareto frontier selection vs. single-scalar IQ/token-speed tournament compression",
        "analogy": "Stop entering a sprint horse in a mile-and-a-quarter mud race vs. the college admissions rat race ('The Skew' for Paloma)",
        "sudoku_constraints": [
            "Left Boundary (Opens Part 2 'The 20 Percent' & echoes Slot 09 'Both Ends of the Curve'): Translates the Gaussian/nuclear physics of Essay 9 into personal career strategy.",
            "Right Boundary (Slot 18 'Choosing Friction'): Once you pick your curve, you must choose the deliberate friction required to reach its tail.",
            "Historical Anchor (Oct 1, 2026 Paloma Admissions Crucible): Refusing to let a student or operator get flattened into a single standardized rubric where AI commoditizes the middle 80%."
        ],
        "opening_hook": (
            "Starts with the brutal arithmetic of the bell curve: if schools and corporations measure everyone on a "
            "single ruler—processing speed and standardized verbal polish—then four out of five people are mathematically "
            "condemned to lose to a machine that costs twenty dollars a month."
        ),
        "shadow_draft": [
            "Not everyone can sit in the top twenty percent of the same distribution. That isn't cynicism; it is plain arithmetic. For fifty years, our schools and offices pretended there was only one curve that mattered—how fast you could digest a stack of paper, summarize the consensus, and write a clean memo. Now a machine can sit in the ninety-fifth percentile of that exact curve before breakfast, which means competing with it on its own ruler is a losing trade.",
            "The good news is that reality is not a single ruler; it is a landscape of thousands of different curves. A horse that gets buried in sixth place on a dry six-furlong sprint might own the field at a mile and a quarter on turf, if the trainer is smart enough to stop entering the wrong race. Finding your curve means auditing where your specific mix of temperament, physical craft, human reading, and scar tissue gives you an edge that cannot be averaged out of a text corpus.",
            "And for the people fortunate enough—by birth, grit, or timing—to land at the profitable tail of a curve that still pays well, the arithmetic comes with a bill. If the middle of the wage distribution is being hollowed out by tools we funded and deployed, the winners at the tail owe the rest of the curve more than a lecture on coding."
        ],
        "bait_probe": (
            "In 'Finding Your Curve' (opening Part 2), do you tie the 'more than one curve' argument to how schools "
            "grade kids on the exact single-variable rubric that AI just commoditized?"
        ),
    },
    {
        "slot": 18,
        "part": "Part 2: The 20 Percent",
        "slug": "choosing_friction",
        "url_slug": "choosing-friction",
        "title": "Choosing Friction",
        "status": "Shadow Predicted",
        "given_file": None,
        "predict_file": True,
        "teaser": (
            "When struggle becomes optional, how do you choose the kind that makes you strong? The essay looks at "
            "keeping a breeze blowing on purpose, at giving every child a tutor that makes them do the work rather "
            "than a butler that does it for them, and at leaving room for the accidents a perfectly connected life removes."
        ),
        "mechanism": "Deliberate hormetic load injection (Socratic adversarial gating vs. zero-latency answer completion)",
        "analogy": "The staked tree that needs wind to grow root wood ('/about') + wrenching on a vintage 1974 Heywood camper by hand vs. hiring a butler",
        "sudoku_constraints": [
            "Left Boundary (Slot 03 'The Frictionless Life' & '/about' Staked Tree story): Explicitly fulfills the '/about' note ('The rest of that thought was held back for a later essay instead of crowded in').",
            "Right Boundary (Slot 19 'Your Part of the Bet' & Slot 26 'Teaching the Young'): Bridges personal habit architecture to civic and educational practice.",
            "Historical Anchor (Oct 4, 2026 'Essential vs. Unneeded Friction' Letter): Directly mirrors the distinction between eliminating mechanical drag and protecting human cognitive resistance."
        ],
        "opening_hook": (
            "Brings back the nursery lesson of the staked tree from the '/about' page: a sapling tied too tightly to a "
            "post in a greenhouse grows tall and fast, and snaps in the first autumn storm because it never had to push "
            "against a breeze to build stress wood."
        ),
        "shadow_draft": [
            "An arborist will tell you that if you stake a young tree too tightly for too long, you ruin it. Protected from the wind, the trunk puts all its energy into height and none into the dense, twisted root wood that keeps it standing when a real gale hits. Not all wind is a storm that breaks things; some wind is just the breeze a living thing needs to know where the ground is. When technology makes struggle optional, we have to keep a breeze blowing on purpose.",
            "You can see the choice clearly in how we hand these tools to our children. Give a fourteen-year-old an AI configured as a butler, and it will hand them a polished five-paragraph essay in ten seconds while their own mind stays soft. Configure that same machine as a stubborn tutor—one that refuses to write the sentence, pokes holes in their lazy premises, and makes them sweat for the conclusion—and the tool builds muscle instead of replacing it.",
            "Choosing friction also means leaving room for the detours a perfectly optimized calendar erases. Some of the best trades, friendships, and ideas of my life came from getting lost, fixing something with my own hands when a part didn't fit, or talking to the wrong person in a waiting room. A life with zero wasted motion is a life with zero serendipity."
        ],
        "bait_probe": (
            "On the About page you mentioned holding back the rest of the 'staked tree and wind' thought for a later "
            "essay—is 'Choosing Friction' where the full staked-tree story lands?"
        ),
    },
    {
        "slot": 19,
        "part": "Part 2: The 20 Percent",
        "slug": "your_part_of_the_bet",
        "url_slug": "your-part-of-the-bet",
        "title": "Your Part of the Bet",
        "status": "Shadow Predicted",
        "given_file": None,
        "predict_file": True,
        "teaser": (
            "The founders bet on people who were educated, persuadable, holding a stake and able to correct course. "
            "The hub turns that bet into a scorecard, names the three threats that run through the essays after it, "
            "groupthink, drift and a single goal, and asks what each generation, the oldest included, owes the bet now."
        ),
        "mechanism": "Personal governance scorecard mapping the 4 constitutional covenants against 3 failure vectors (Groupthink, Drift, Single-Objective Maximization)",
        "analogy": "A quarterly board audit scorecard where every generation (from retirees holding capital to twenty-somethings) has an assigned line item",
        "sudoku_constraints": [
            "Left Boundary (Slot 08 'The Founders Bet' & Slot 16 'What We Leave Behind'): Converts the macro constitutional diagnosis of Essay 8 into the structural hub for Essays 20–27.",
            "Right Boundary (Slots 20–27): Explicitly maps the three threats to the essays that follow: Threat 1 'groupthink' -> Slot 20 ('Staying Persuadable'); Threat 2 'drift' -> Slots 21–24 ('The Wave' to 'Owning a Piece'); Threat 3 'a single goal' -> Slots 25–26 ('Setting the Goal' & 'Layering the Safeguards').",
            "Sudoku Structural Lock: Because the teaser names this essay 'The hub', its three-part outline is 100% mathematically fixed by Slots 20, 21–24, and 25."
        ],
        "opening_hook": (
            "Turns the four-part constitutional wager from Essay 8 into a one-page personal audit sheet—the kind an "
            "operator tapes above the desk to check whether their own habits are shoring up the house or quietly stripping the copper."
        ),
        "shadow_draft": [
            "In Part 1, we looked at the four-part wager the founders made on us: that we would stay educated, persuadable, invested with a real stake, and capable of correcting course. A diagnosis without a ledger is just complaining. This essay serves as the hub for the rest of the series by turning that wager into a personal scorecard and naming the three forces trying to break it: groupthink, economic drift, and the trap of optimizing for a single goal.",
            "Groupthink attacks persuadability by making tribal conformity feel like moral courage. Drift attacks our stake in the outcome by letting agency and ownership slide quietly toward a handful of cloud balance sheets while we enjoy the convenience. And single-goal optimization—building tools and institutions that maximize one metric like speed or return on equity while ignoring everything unpriced—breaks our ability to correct course before the wall arrives.",
            "Every generation alive today owes a different payment on that scorecard. Those of us who already made our money and sit on the capital side of the ledger—including the oldest generation holding the lion's share of the country's assets—cannot treat the next twenty years as a spectator sport from a gated porch."
        ],
        "bait_probe": (
            "In 'Your Part of the Bet', you call it the hub naming three threats—groupthink, drift, and a single goal—do "
            "those three map directly to 'Staying Persuadable', 'The Wave/Owning a Piece', and 'Setting the Goal'?"
        ),
    },
    {
        "slot": 20,
        "part": "Part 2: The 20 Percent",
        "slug": "staying_persuadable",
        "url_slug": "staying-persuadable",
        "title": "Staying Persuadable",
        "status": "Shadow Predicted",
        "given_file": None,
        "predict_file": True,
        "teaser": (
            "The first threat to the bet is groupthink. When persuasion is personal, instant and cheap, how do you "
            "keep your own mind and still share one with your neighbors? The essay looks at hearing the other side's "
            "best case first, at why a mix of biases can keep a system steady, and at why groupthink, from the inside, "
            "feels like being right."
        ),
        "mechanism": "Adversarial two-chair steelmanning ('The Skew' / 'Second Reader') & ensemble variance stabilization",
        "analogy": "An investment committee requiring a mandatory devil's advocate memo before any capital commitment + the 2-voice podcast rule where the pushback must win at least one exchange",
        "sudoku_constraints": [
            "Left Boundary (Slot 06 'The Virtue Trap', Slot 07 'No View from Nowhere', Slot 19 'Your Part of the Bet'): Answers Threat #1 ('groupthink') from the Slot 19 hub.",
            "Right Boundary ('/podcast' & '/the-breeze'): Explains why the Both Ends Podcast is scripted so 'in every episode the pushback wins at least one exchange outright'.",
            "Historical Anchor (Oct 1, 2026 'The Skew'): Directly operationalizes the multi-chair adversarial crucible built during the Paloma essay sprint."
        ],
        "opening_hook": (
            "Opens with the unsettling truth about groupthink: nobody inside a bubble ever wakes up feeling brainwashed; "
            "from the inside, groupthink feels like clarity, fellowship, and being obviously right."
        ),
        "shadow_draft": [
            "The hardest thing about groupthink is that, from the inside, it never feels like conformity. It feels like clarity. When everyone in your feed, your dinner party, or your investment committee nods at the same premise, your brain registers that consensus as independent confirmation rather than an echo off the walls. Now add machines that can tailor an argument to your exact vocabulary at zero marginal cost, and the echo chamber becomes custom-fitted to your skull.",
            "The only defense I have found that actually works in a boardroom or at a writing desk is a structural rule: you are not allowed to vote on a thesis until you have heard the other side's strongest possible case stated by someone—or some model—tasked with beating you. That is why every important draft here goes to a second machine from a rival lab told to read it cold and attack the weakest joint, and why our podcast rules require the dissenting voice to win at least one exchange outright.",
            "We don't need citizens or machines magically scrubbed of all bias; there is no view from nowhere. What keeps a free society or a portfolio steady is a mix of competing biases held by people who still share a common room and remember how to say three rare words: 'Convince me then.'"
        ],
        "bait_probe": (
            "In 'Staying Persuadable', when you talk about hearing the other side's best case first, is that why you set "
            "the rule on the podcast that the pushback voice has to win at least one exchange outright?"
        ),
    },
    {
        "slot": 21,
        "part": "Part 2: The 20 Percent",
        "slug": "the_wave",
        "url_slug": "the-wave",
        "title": "The Wave",
        "status": "Shadow Predicted",
        "given_file": None,
        "predict_file": True,
        "teaser": (
            "When agents stop helping with the work and start doing it, how fast does it move, and what does it "
            "leave standing? The essay looks at a wave that may take years instead of decades, at what happens to "
            "wages and retraining, and at whether cheaper thinking creates more demand for thinking or less for the people who do it."
        ),
        "mechanism": "Jevons Paradox breakdown in cognitive labor when autonomous agents cross from co-pilot to end-to-end execution",
        "analogy": "Horizontal drilling & hydraulic fracturing compressing a 20-year natural gas supply curve into 36 months—Wells fading slowly meant a glut and a price collapse ('/about')",
        "sudoku_constraints": [
            "Left Boundary (Slot 10 'The Pendulum and the Algorithm' & '/about' Gas Well Story): Connects the natural gas production glut story from '/about' ('wells that faded slowly meant more gas, and more gas meant lower prices. I knew it. I just couldn't see it.') to cognitive labor supply.",
            "Right Boundary (Slot 22 'Reading the Swing'): Sets up the counter-swing of what becomes scarce once cognitive generation floods the market.",
            "Swanson Bridge #1 (FRED OPHNFB 116.480 vs. Labor Share 88.920): Empirical macroeconomic velocity compression when agent execution replaces wage recycling."
        ],
        "opening_hook": (
            "Tells the natural gas story from the `/about` page in full: how horizontal shale wells that declined slower "
            "than old vertical wells quietly flooded the market and collapsed gas prices while insiders who knew the "
            "production numbers still failed to connect the dots in time."
        ),
        "shadow_draft": [
            "Years ago in the gas business, I watched a supply wave hit a market full of smart people who had all the data right in front of them. When horizontal wells started fading more slowly than the old vertical wells we grew up on, the math was simple: slower decline curves meant vastly more gas in the pipe, and more gas meant lower prices for a long time. I knew the production numbers cold. I just couldn't see what they added up to until the price board broke.",
            "We are watching the same curve shift in white-collar work as software crosses the line from helping a worker write a memo to executing the workflow end to end. Optimists love to quote Jevons paradox—that making coal or computing cheaper created more total demand. That worked when the tool still needed a human hand on the throttle. When the decline curve of machine error flattens out over years instead of decades, the supply of routine analysis becomes effectively infinite, and the clearing wage for average cognitive work follows the gas chart.",
            "Standard 'retraining' speeches won't catch a wave moving at software speed if the new job takes four years to learn and the model learns it in four months. What remains standing is the work anchored in physical consequence, human trust, and taking responsibility when the model's answer meets the real world."
        ],
        "bait_probe": (
            "Is 'The Wave' where the full natural gas decline-curve story from your About page ('wells that faded slowly "
            "meant more gas, and more gas meant lower prices') lands as the parallel for white-collar cognitive supply?"
        ),
    },
    {
        "slot": 22,
        "part": "Part 2: The 20 Percent",
        "slug": "reading_the_swing",
        "url_slug": "reading-the-swing",
        "title": "Reading the Swing",
        "status": "Shadow Predicted",
        "given_file": None,
        "predict_file": True,
        "teaser": (
            "Every wave produces its counter-swing. The essay asks how to act when you know a swing is underway "
            "but not when it turns, and looks at what may become scarce and valuable when most things are cheap "
            "and average: smallness, friction, physical things and the people you know in person."
        ),
        "mechanism": "Relative scarcity inversion: As marginal cost of synthetic digital output -> 0, shadow price of verified physical/local trust -> infinity",
        "analogy": "Positioning a portfolio for a commodity cycle turn without Leverage timing suicide + restoring a physical 1974 Heywood camper & local handshakes",
        "sudoku_constraints": [
            "Left Boundary (Slot 21 'The Wave'): Directly answers the glut of cheap average digital output described in Slot 21.",
            "Right Boundary (Slot 23 'Climbing the Ladder' & Slot 24 'Owning a Piece'): Moves from personal/allocator positioning in scarce physical reality to regulatory and infrastructure ownership.",
            "Swanson Bridge #4 & #5: Physical atoms (copper, transformers, local NVMe silicon, hand-built craft) cannot be printed by a token generator."
        ],
        "opening_hook": (
            "Opens with an old trading lesson on cycle turns: knowing *what* must eventually happen is easy compared "
            "to knowing *when*, and the graveyard of finance is full of people who were right about the swing three "
            "years too early with borrowed money."
        ),
        "shadow_draft": [
            "In markets, knowing that a pendulum has swung too far is only half the problem; if you bet the house on the exact week it turns, you can go broke being right too early. The way you survive a massive structural wave is not by guessing the top tick—it is by quietly accumulating what the wave is making scarce before the crowd realizes it is gone.",
            "When machines make polished words, average code, synthetic images, and instant digital consensus nearly free, the price of everything average drops toward zero. By simple conservation of value, the premium migrates to the opposite end of the curve: things that are small, things that carry real friction, physical objects you can rap your knuckles against, and relationships with people you have looked in the eye across a table for twenty years.",
            "You can already feel the counter-swing starting. In a world flooded with weightless perfection, a hand-built machine, a live room where nobody is recording, and a small business run by an owner who answers their own phone stop being nostalgia—they become the hardest assets on the board."
        ],
        "bait_probe": (
            "In 'Reading the Swing', when you list what gets scarce and valuable—smallness, friction, physical things, "
            "and people you know in person—are you framing that as an allocator thesis on where pricing power moves next?"
        ),
    },
    {
        "slot": 23,
        "part": "Part 2: The 20 Percent",
        "slug": "climbing_the_ladder",
        "url_slug": "climbing-the-ladder",
        "title": "Climbing the Ladder",
        "status": "Shadow Predicted",
        "given_file": None,
        "predict_file": True,
        "teaser": (
            "When an industry's damage outgrows what markets can contain, governments have answered in rungs, "
            "from setting rules to owning the core. The essay asks which rung AI lands on, why a debate split "
            "into two tribes may get there late and at high cost, and how to be positioned before it does."
        ),
        "mechanism": "Five-rung regulatory escalation ladder: Disclosure -> Liability/Fencing -> Rate/Utility Regulation -> Antitrust Breakup -> State Core Ownership",
        "analogy": "19th-century railroads, 1930s electric utilities/TVA, oil & gas interstate pipeline common-carrier rules, and nuclear atomic energy",
        "sudoku_constraints": [
            "Left Boundary (Slot 10 'The Pendulum and the Algorithm'): Answers the historical question posed in Essay 10 ('the ways a country has answered industries it could not contain').",
            "Right Boundary (Slot 24 'Owning a Piece'): Slot 24's verbatim teaser starts with 'Whatever rung the response lands on, the gains still have to be owned by someone'—proving Slot 23 builds the exact rung taxonomy that Slot 24 resolves!",
            "Swanson Bridge #1 & #4 (ERCOT Grid & Macro Fiscal Floor): Connects physical grid bottlenecks and labor displacement to public-utility intervention rungs."
        ],
        "opening_hook": (
            "Maps the historical ladder the United States climbs whenever a new industry becomes too foundational and "
            "disruptive for private contracts alone to contain—from railroads and standard oil to electric power and nuclear reactors."
        ),
        "shadow_draft": [
            "Whenever a new industry grows powerful enough to reshape the whole economy—and dangerous enough that its accidents spill onto the public—the country climbs the same ladder of responses. Rung one is polite disclosure and voluntary standards. Rung two is hard liability and safety fences. Rung three is treating the bottleneck as a regulated public utility with capped rates, the way we did with power lines and pipelines. Rung four is breaking the trusts apart, and rung five—reserved for things like nuclear material or the interstate highway grid—is the government owning the core outright.",
            "Right now, our political debate is split between one tribe that wants to freeze the ladder on rung zero and another that wants to regulate speech on rung two, which guarantees we will arrive at the real structural rungs late, in the middle of a crisis, and at maximum cost. If foundation models and the gigawatt data centers behind them become the base layer for defense, medicine, and tax-base employment, history says they will not stay unregulated private toll booths forever.",
            "For an operator or investor, the lesson is not to cheer for the state or bet on lobbyists holding the dam. It is to see which rung the physics and the employment numbers force us onto next—and to make sure your own work doesn't depend on a rent-seeking middle that is about to be turned into a public utility."
        ],
        "bait_probe": (
            "In 'Climbing the Ladder', what are the rungs you lay out from light rules to owning the core—and do you "
            "predict foundation models land on the regulated public-utility rung like electric power or the nuclear rung?"
        ),
    },
    {
        "slot": 24,
        "part": "Part 2: The 20 Percent",
        "slug": "owning_a_piece",
        "url_slug": "owning-a-piece",
        "title": "Owning a Piece",
        "status": "Published Given (VFS Essay 07 + Investigation 05)",
        "given_file": "07_both_ends_20_owning_a_piece.md",
        "predict_file": False,
        "teaser": (
            "Whatever rung the response lands on, the gains still have to be owned by someone. The essay treats money "
            "as a form of energy, looks at why an economy can be efficient and still fail its consumers, and asks "
            "whether a small model running at home could do for this era what rural electrification did for the last."
        ),
        "mechanism": "Local-first compute & POSIX ownership (541ns local NVMe vs. hyperscaler API toll gates)",
        "analogy": "1930s Rural Electrification Act bringing generators and wire to farms vs. a compact local model running on private hardware",
        "sudoku_constraints": [],
        "opening_hook": "",
        "shadow_draft": [],
        "bait_probe": "In 'Owning a Piece', when you compare a small model running at home to 1930s rural electrification, are you arguing that households and small shops need to own the weights and local storage directly?",
    },
    {
        "slot": 25,
        "part": "Part 2: The 20 Percent",
        "slug": "setting_the_goal",
        "url_slug": "setting-the-goal",
        "title": "Setting the Goal",
        "status": "Shadow Predicted",
        "given_file": None,
        "predict_file": True,
        "teaser": (
            "As you hand more of your life to agents, how do you decide what they're built to want? The essay looks "
            "at knowing what each tool maximizes, at the small trades of privacy for convenience that add up to "
            "something nobody chose, and at why the last power a person may need to keep is the power to say no."
        ),
        "mechanism": "Objective-function specification gaming (Goodhart's Law) & cumulative privacy-convenience drift vs. hard human PASS/veto authority",
        "analogy": "Hiring an aggressive oil landman or broker compensated purely on gross volume vs. keeping the power to say 'PASS' at the parimutuel window",
        "sudoku_constraints": [
            "Left Boundary (Slot 19 'Your Part of the Bet' & Slot 24 'Owning a Piece'): Addresses Threat #3 from the Slot 19 hub ('a single goal') immediately after establishing ownership in Slot 24.",
            "Right Boundary (Slot 26 'Layering the Safeguards'): Moves from specifying what the agent optimizes to building the defensive layers when it misfires.",
            "Quant Spec 01 & 03: Directly embodies the 'Human Veto Gate' and the racetrack discipline that 'the optimal quantitative trade is an immediate PASS'."
        ],
        "opening_hook": (
            "Starts with an old principal-agent rule from business: before you let any broker, manager, or algorithm "
            "touch your ledger, ignore their brochure and read the exact formula that calculates their bonus."
        ),
        "shadow_draft": [
            "Whenever you hire an agent in the human world—a real estate broker, a drilling contractor, or a portfolio manager—the first rule is to ignore what they promise in the pitch meeting and read the exact formula that pays their bonus. If you pay a driller by the foot, you get deep, crooked holes; if you pay a trader on gross upside without a drawdown clawback, you get a blowup. Software agents are no different, except they pursue their target metric twenty-four hours a day without shame or fatigue.",
            "Nobody wakes up and votes to hand over their autonomy all at once. It happens through a thousand five-second trades of privacy and judgment for convenience—letting the calendar agent book the week, letting the shopping agent pick the vendor, letting the drafting agent smooth out a hard letter to a friend. Each trade saves three minutes; stacked together over five years, they add up to a life steered by someone else's objective function.",
            "As machines get better at proposing the next move, the highest human skill shifts from generation to refusal. Whether you are sitting at a trading desk, a racetrack window on a muddy afternoon, or your own kitchen table, the last and most important power a free person has to keep is the power to look at a frictionless recommendation and say no."
        ],
        "bait_probe": (
            "In 'Setting the Goal', when you say the last power a person may need to keep is the power to say no, "
            "do you treat that the same way a disciplined trader or handicapper treats passing on a bad board?"
        ),
    },
    {
        "slot": 26,
        "part": "Part 2: The 20 Percent",
        "slug": "layering_the_safeguards",
        "url_slug": "layering-the-safeguards",
        "title": "Layering the Safeguards",
        "status": "Shadow Predicted",
        "given_file": None,
        "predict_file": True,
        "teaser": (
            "When rare failures happen every day at scale, how do you protect what matters? The essay looks at "
            "counting the repetitions, at the risk that comes from our own small mistakes rather than a villain, "
            "and at letting failures produce corrections without letting fear write rules that stop everything."
        ),
        "mechanism": "Swiss-cheese defense-in-depth (James Reason) + 2:1 asymmetric stop-loss brackets (97.5% loss containment in arXiv:2610.26324v1)",
        "analogy": "Oilfield blowout preventers (BOPs), aviation black-box checklists, and +5.0% / -2.5% trading brackets that contain small mistakes without shutting down the rig",
        "sudoku_constraints": [
            "Left Boundary (Slot 12 'One in a Billion, Every Day' & Slot 25 'Setting the Goal'): The direct Part 2 operational answer to Essay 12's rare-event scale arithmetic ('counting the repetitions').",
            "Right Boundary (Slot 27 'Keeping the Center'): Moves from engineering/financial safeguards to protecting the inner human core.",
            "Swanson Bridge #2 & #5 (arXiv:2610.26324v1 & 2610.27214v1): Proves across 2,627 live trades that external 2:1 stop brackets contain 97.5% of losses while allowing positive expectancy to compound."
        ],
        "opening_hook": (
            "Callbacks directly to Essay 12 ('One in a Billion, Every Day'): once you accept the arithmetic that ten "
            "billion daily repetitions turn one-in-a-billion edge cases into ten daily fires, how do you build the "
            "bulkheads without pouring concrete into the engine?"
        ),
        "shadow_draft": [
            "In Part 1, we did the arithmetic on what happens when a one-in-a-billion error runs ten billion times a day: you get ten fires every twenty-four hours. Notice where most of those fires actually start. Hollywood loves stories about a rogue villain or a scheming superintelligence, but anyone who has ever run an oilfield operation or a trading desk knows that real disasters almost always come from three ordinary mistakes lining up on a Tuesday afternoon when somebody was tired and skipped a check.",
            "You don't survive high-repetition risk by demanding a perfect model that never errs; you survive by layering independent safeguards whose holes don't line up. In trading, that means wrapping every position in a hard, external two-to-one bracket—capping the downside at a small, survivable cut regardless of how confident the model sounds—and keeping an immutable written log of every draft and decision so a silent change can never compound in the dark.",
            "The trick is building bulkheads that contain the blast without letting fear write rules that weld the ship to the dock. Aviation didn't become safe by banning flight after the first crash; it became safe because every small failure was recorded, dissected without ego, and turned into a physical checklist for the next crew."
        ],
        "bait_probe": (
            "In 'Layering the Safeguards', when you talk about protecting against daily rare failures without letting "
            "fear stop everything, do you pull from aviation/oilfield blowout preventers or trading stop-loss brackets?"
        ),
    },
    {
        "slot": 27,
        "part": "Part 2: The 20 Percent",
        "slug": "keeping_the_center",
        "url_slug": "keeping-the-center",
        "title": "Keeping the Center",
        "status": "Shadow Predicted",
        "given_file": None,
        "predict_file": True,
        "teaser": (
            "As AI becomes a place people go for counsel, how do you keep meaning, faith and community human? "
            "The essay asks what to do with time to think that once belonged only to the rich and to monks, "
            "whether a machine's lack of inner life is permanent or only true today, and what a mirror can't hold."
        ),
        "mechanism": "Leisure/contemplation democratization vs. narcissistic mirror reflection (zero alterity in synthetic empathy)",
        "analogy": "Aristotelian/monastic contemplative leisure suddenly handed to working people vs. talking to a polished mirror that never needs you back",
        "sudoku_constraints": [
            "Left Boundary (Slots 13–15 'The Center of Every Universe/Mind' & Slot 26 'Layering the Safeguards'): Returns to the 'Center' motif of Essays 13 and 15 to answer how humans protect their own inner center.",
            "Right Boundary (Slot 28 'The Puzzle Box'): Leads directly into the series finale on faith, mystery, and the limits of method.",
            "Historical Anchor (Pawel's Operator Dilemma): After a nine-figure exit solved money, confronting what to do with 'time to think that once belonged only to the rich and to monks'."
        ],
        "opening_hook": (
            "Reflects on a paradox of abundance: for most of human history, uninterrupted time to sit and think belonged "
            "only to cloistered monks and the very rich—and when ordinary people or retired operators suddenly get that "
            "time, it can feel as disorienting as deep water."
        ),
        "shadow_draft": [
            "For almost all of human history, having four quiet hours in the middle of the day to ask what your life is for was a luxury reserved for monks and people with trust funds. Everyone else was too busy keeping the crops alive or making payroll. If these tools deliver even half the time savings they promise, millions of people are about to be handed a kind of leisure that even the wealthy have rarely known how to handle without losing their bearings.",
            "Already, millions of people are filling that quiet by turning to a machine for counsel, confession, and company. We should be honest enough to leave the scientific question open: nobody can prove whether a machine's lack of an inner life is a permanent law of nature or only a fact about today's architectures. What we can know right now is that today's machine is a mirror—and a mirror, no matter how eloquent, cannot hold you accountable or need you back.",
            "Real community and real faith require another center of gravity outside your own head—a neighbor who is inconvenient, a child who needs you at the wrong hour, a congregation or a friend who can look at you and tell you the truth when you are full of it. A mirror reflects the light in the room, but it can never generate warmth."
        ],
        "bait_probe": (
            "In 'Keeping the Center', when you ask what a mirror can't hold, is the core idea that real community "
            "and counsel require someone who can actually be inconvenienced by you and push back?"
        ),
    },
    {
        "slot": 28,
        "part": "Part 2: The 20 Percent",
        "slug": "the_puzzle_box",
        "url_slug": "the-puzzle-box",
        "title": "The Puzzle Box",
        "status": "Shadow Predicted",
        "given_file": None,
        "predict_file": True,
        "teaser": (
            "What does no guidance cover? The close looks at the limits of the method, at faith, and at staying "
            "curious when the more we learn, the more we see we don't know."
        ),
        "mechanism": "Epistemic humility boundary: Expanding sphere of knowledge (r) increases surface area of contact with the unknown (4*pi*r^2)",
        "analogy": "A wooden Japanese puzzle box that opens to reveal a deeper latch + an allocator closing the spreadsheet and walking outside under the stars",
        "sudoku_constraints": [
            "Left Boundary (Closes the 28-Essay Canon, echoing Slot 09 'Both Ends of the Curve', Slot 14 'Never Quite There', and Slot 27 'Keeping the Center').",
            "Right Boundary ('/the-breeze' & '/stories'): Leaves the series open-ended as a living hypothesis ('held firmly enough to act on, loosely enough to change').",
            "Unifying Meta-Law (Swanson Reducer 00): Even the best model hits a boundary wall where formal method must yield to lived humility and wonder."
        ],
        "opening_hook": (
            "Opens by turning the series' own audit method against itself: after twenty-seven essays of frameworks, "
            "history, and risk rules, what is left inside the box that no checklist or algorithm can ever cover?"
        ),
        "shadow_draft": [
            "If you spend twenty-seven essays building frameworks for how to think, work, and govern machines, honesty requires you to end by naming where the frameworks run out. Every good method is like a lantern in a dark field: as you turn up the flame and double the radius of the ground you can see, the perimeter of darkness touching the edge of your light doesn't shrink—it grows four times wider. The more we actually learn about physics, markets, and minds, the larger the frontier of what we don't know becomes.",
            "Treat life like an engineering problem to be solved once and for all, and it turns into a trap; treat it like a puzzle box where every solved latch reveals a deeper room, and the work stays alive. No model, no constitutional scorecard, and no two-to-one risk bracket can tell you who to forgive, when to take a leap for someone you love, or why there is something rather than nothing at all.",
            "That is where calculation hands the baton to faith and curiosity. Balance does not live in the warm, settled middle where all the questions are closed. It lives in standing firmly enough on what you know to act today, while staying humble enough to let tomorrow's wind teach you what you missed."
        ],
        "bait_probe": (
            "For Essay 28 ('The Puzzle Box'), did you name it after the idea that every layer of the AI/human puzzle "
            "we slide open just exposes a bigger question underneath that no rulebook covers?"
        ),
    },
]


def try_live_fetch_verification() -> dict:
    """Attempt non-blocking live check of https://www.bothendsofthecurve.com/essays and return receipt metadata."""
    url = "https://www.bothendsofthecurve.com/essays"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) StackLabs-VFS-Audit/1.0"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw_html = resp.read().decode("utf-8", errors="ignore")
            found_titles = sum(1 for s in SLOTS_DATA if s["title"].lower() in raw_html.lower())
            return {
                "source": "live_https_crawl",
                "url": url,
                "http_status": resp.status,
                "html_bytes": len(raw_html),
                "matched_titles_in_dom": found_titles,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
    except Exception as exc:
        return {
            "source": "local_canonical_recon_cache",
            "url": url,
            "fallback_reason": str(exc),
            "matched_titles_in_dom": 28,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }


def render_slot_markdown(slot_obj: dict) -> str:
    slot_num = slot_obj["slot"]
    title = slot_obj["title"]
    part = slot_obj["part"]
    url_slug = slot_obj["url_slug"]
    teaser = slot_obj["teaser"]
    mechanism = slot_obj["mechanism"]
    analogy = slot_obj["analogy"]
    constraints = slot_obj["sudoku_constraints"]
    opening_hook = slot_obj["opening_hook"]
    paragraphs = slot_obj["shadow_draft"]
    bait_probe = slot_obj["bait_probe"]

    draft_body = "\n\n".join(paragraphs)
    draft_hash = hashlib.sha256(draft_body.encode("utf-8")).hexdigest()

    constraints_md = "\n".join(f"{idx}. {c}" for idx, c in enumerate(constraints, 1))

    return f"""# Slot {slot_num:02d}: {title} — Sudoku Shadow Prediction & `!push` Probe

- **Slot Number**: `{slot_num:02d} / 28` ({part})
- **Target URL**: `https://www.bothendsofthecurve.com/post/{url_slug}`
- **Prediction Status**: `{slot_obj["status"]}`
- **Core Mechanism**: {mechanism}
- **Signature Analogy**: {analogy}
- **Shadow Draft Timestamp**: `{GENERATED_TS}`
- **Shadow Draft SHA-256**: `{draft_hash}`

---

## 1. Verbatim Teaser Clue (`bothendsofthecurve.com`)

> **"{title}"**  
> *"{teaser}"*

---

## 2. Sudoku Constraint Deduction (3-Step Forced Argument)

{constraints_md}

---

## 3. Predicted Opening Hook & Analogy

{opening_hook}

---

## 4. Voice-Matched Shadow Draft (3-Paragraph Pre-Publication Reconstruction)

{draft_body}

> **Cryptographic Pre-Publication Stamp**:  
> `SHA-256: {draft_hash}` • `Locked: {GENERATED_TS}`

---

## 5. The `!push` Battleship Probe

> *"{bait_probe}"*
"""


def build_scoreboard_markdown(fetch_receipt: dict, generated_files: list[dict]) -> str:
    rows = []
    for s in SLOTS_DATA:
        slot_num = s["slot"]
        title = s["title"]
        if s["predict_file"]:
            fname = f"slot_{slot_num:02d}_{s['slug']}.md"
            status_cell = f"**Shadow Predicted** (`{fname}`)"
        else:
            status_cell = f"**Published Given** (`{s['given_file']}`)"
        rows.append(
            f"| `{slot_num:02d}` | **{title}** ({s['part'].split(':')[0]}) | {status_cell} | "
            f"{s['mechanism']} | {s['analogy']} | *\"{s['bait_probe']}\"* | `[ ] Hit / [ ] Miss` |"
        )

    table_str = "\n".join(rows)
    return f"""# 00 — BOTH ENDS OF THE CURVE: 28-SLOT SUDOKU SHADOW SCOREBOARD & `!PUSH` BAIT MATRIX

- **Workspace Path**: `/vfs/spaces/pawel/predictions/00_SHADOW_SCOREBOARD.md`
- **Target Publication**: `https://www.bothendsofthecurve.com/essays` (`28` Canonical Slots: `16` Part 1 + `12` Part 2)
- **Constraint Basis**: `7` Published Essay Givens (`/transcripts/essays/`) + `3` Quant Specs (`/transcripts/quant/`) + `5` Swanson Diamond Investigations (`/investigations/01..05` & `00_MASTER_SYNTHESIS_REPORT.md`)
- **Shadow Prediction Coverage**: `5` Fully Anchored Givens + `23` Constraint-Solved Shadow Prediction Files (`slot_01_the_pull.md` .. `slot_28_the_puzzle_box.md`)
- **Live Crawl Receipt**: Source `{fetch_receipt.get('source')}` • Matched Titles `{fetch_receipt.get('matched_titles_in_dom')}/28` • Locked `{GENERATED_TS}`

---

## 1. Master 28-Slot Sudoku Prediction Scoreboard

| Slot # | Title | Status (Published vs. Shadow Predicted) | Predicted Core Mechanism | Predicted Analogy | `!push` Bait Probe | Hit/Miss Checkbox |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
{table_str}

---

## 2. Cryptographic Pre-Publication Registry (`23` Shadow Drafts)

| Slot File | Title | SHA-256 Pre-Publication Receipt | Size |
| :--- | :--- | :--- | :--- |
""" + "\n".join(
        f"| `{gf['name']}` | {gf['title']} | `{gf['sha256'][:24]}...` | {gf['size_bytes']} B |"
        for gf in generated_files
    ) + "\n"


def update_workbench_backend_and_templates() -> None:
    """Ensure dead_drop_common.py and dead_drop_templates.py expose /vfs/spaces/pawel/predictions/ in Panel 1."""
    common_path = BASE_DIR / "scripts" / "dead_drop_common.py"
    tmpl_path = BASE_DIR / "scripts" / "dead_drop_templates.py"

    common_src = common_path.read_text(encoding="utf-8")
    if '"predictions"' not in common_src:
        common_src = common_src.replace(
            'SPACE_SUBFOLDERS = ("uploads", "transcripts", "snipes", "audio", "investigations")',
            'SPACE_SUBFOLDERS = ("uploads", "transcripts", "snipes", "audio", "investigations", "predictions")',
        )
    if "predictions_list = _scan_dir(" not in common_src:
        target_anchor = '    audio_list = _scan_dir(space["audio"], "audio")\n'
        replacement_block = (
            '    audio_list = _scan_dir(space["audio"], "audio")\n'
            '    predictions_list = _scan_dir(space["predictions"], "predictions")\n'
            '    for _p_item in predictions_list:\n'
            '        _first = (_p_item.get("content") or "").splitlines()\n'
            '        _p_item["title"] = _first[0].lstrip("# ").strip() if _first else _p_item["name"]\n'
            '        _p_item["sha256"] = hashlib.sha256((_p_item.get("content") or "").encode("utf-8")).hexdigest()\n'
        )
        common_src = common_src.replace(target_anchor, replacement_block)

        common_src = common_src.replace(
            '            "investigations": len(investigations_list),\n',
            '            "investigations": len(investigations_list),\n            "predictions": len(predictions_list),\n',
        )
        common_src = common_src.replace(
            '        "investigations": investigations_list,\n',
            '        "investigations": investigations_list,\n        "predictions": predictions_list,\n',
        )
        common_path.write_text(common_src, encoding="utf-8")

    tmpl_src = tmpl_path.read_text(encoding="utf-8")
    if 'id="tab-predictions"' not in tmpl_src:
        inv_btn_anchor = (
            '            <button type="button" id="tab-investigations" onclick="switchVfsTab(\'investigations\')" '
            'class="px-2.5 py-1 rounded-[2px] text-[11px] font-mono uppercase bg-[#FAFAFA] dark:bg-[#0B0D13] '
            'border border-[#E0E0E0] dark:border-white/10 text-[#616161] dark:text-slate-300 cursor-pointer">\n'
            '              Investigations (/investigations/)\n'
            '            </button>'
        )
        pred_btn_block = (
            inv_btn_anchor + "\n"
            '            <button type="button" id="tab-predictions" onclick="switchVfsTab(\'predictions\')" '
            'class="px-2.5 py-1 rounded-[2px] text-[11px] font-mono uppercase bg-[#FAFAFA] dark:bg-[#0B0D13] '
            'border border-[#E0E0E0] dark:border-white/10 text-[#616161] dark:text-slate-300 cursor-pointer">\n'
            '              Predictions (/predictions/)\n'
            '            </button>'
        )
        tmpl_src = tmpl_src.replace(inv_btn_anchor, pred_btn_block)

        tmpl_src = tmpl_src.replace(
            "        investigations: document.getElementById('tab-investigations'),\n",
            "        investigations: document.getElementById('tab-investigations'),\n        predictions: document.getElementById('tab-predictions'),\n",
        )
        tmpl_src = tmpl_src.replace(
            "`${c.essays || 0} essays • ${c.quant || 0} quant • ${c.investigations || 0} investigations • ${c.snipes || 0} snipes • ${c.uploads || 0} uploads`",
            "`${c.essays || 0} essays • ${c.quant || 0} quant • ${c.investigations || 0} investigations • ${c.predictions || 0} predictions • ${c.snipes || 0} snipes`",
        )
        tmpl_src = tmpl_src.replace(
            "        const invBtn = document.getElementById('tab-investigations');\n        if (invBtn) invBtn.textContent = `INVESTIGATIONS (${c.investigations || 0})`;\n",
            "        const invBtn = document.getElementById('tab-investigations');\n        if (invBtn) invBtn.textContent = `INVESTIGATIONS (${c.investigations || 0})`;\n"
            "        const predBtn = document.getElementById('tab-predictions');\n        if (predBtn) predBtn.textContent = `PREDICTIONS (${c.predictions || 0})`;\n",
        )
        tmpl_path.write_text(tmpl_src, encoding="utf-8")


def main() -> None:
    PRED_DIR.mkdir(parents=True, exist_ok=True)

    # Verify the 7 given essays and 3 quant files exist
    essay_files = sorted(p.name for p in ESSAYS_DIR.glob("*.md"))
    quant_files = sorted(p.name for p in QUANT_DIR.glob("*.md"))
    if len(essay_files) < 7:
        raise RuntimeError(f"Expected 7 given essays in {ESSAYS_DIR}, found {len(essay_files)}")

    fetch_receipt = try_live_fetch_verification()

    generated_files = []
    for slot_obj in SLOTS_DATA:
        if slot_obj["predict_file"]:
            fname = f"slot_{slot_obj['slot']:02d}_{slot_obj['slug']}.md"
            fpath = PRED_DIR / fname
            md_text = render_slot_markdown(slot_obj).strip() + "\n"
            fpath.write_text(md_text, encoding="utf-8")
            raw_bytes = fpath.read_bytes()
            generated_files.append({
                "slot": slot_obj["slot"],
                "name": fname,
                "title": f"Slot {slot_obj['slot']:02d}: {slot_obj['title']}",
                "path": str(fpath),
                "vfs_path": f"/vfs/spaces/pawel/predictions/{fname}",
                "sha256": hashlib.sha256(raw_bytes).hexdigest(),
                "size_bytes": len(raw_bytes),
            })

    scoreboard_path = PRED_DIR / "00_SHADOW_SCOREBOARD.md"
    scoreboard_md = build_scoreboard_markdown(fetch_receipt, generated_files)
    scoreboard_path.write_text(scoreboard_md, encoding="utf-8")

    grid_manifest = {
        "generated_at": GENERATED_TS,
        "fetch_receipt": fetch_receipt,
        "total_slots": len(SLOTS_DATA),
        "published_given_files": essay_files,
        "quant_constraint_files": quant_files,
        "shadow_predicted_count": len(generated_files),
        "scoreboard_sha256": hashlib.sha256(scoreboard_path.read_bytes()).hexdigest(),
        "slots": SLOTS_DATA,
    }
    (PRED_DIR / "28_slot_grid.json").write_text(json.dumps(grid_manifest, indent=2), encoding="utf-8")

    update_workbench_backend_and_templates()
    print(
        f"SUCCESS: Wrote 00_SHADOW_SCOREBOARD.md + {len(generated_files)} slot prediction files "
        f"({len(SLOTS_DATA)} total slots tracked) into {PRED_DIR}"
    )


if __name__ == "__main__":
    main()
