"""
Sovereign OS: Jake Taylor Umpire Node & Rulebook Arbitration Engine
Governed by SOW-2026-09-11-JAKE-TAYLOR-SAVANT-ORACLE and Invariant I.8/I.9.

Authentic MLB Rulebook arbitration and mathematical strike zone evaluation.
Persona: Jake Taylor (Tom Berenger, Major League 1989) — grizzled veteran catcher,
reads Moby Dick in the dugout, knows every page of the official rulebook.
"""

import re
import json
from typing import Dict, Any, Optional
from pathlib import Path

REPO_ROOT = Path("/home/james/stacklabs")
RULES_TXT_PATH = REPO_ROOT / "dna" / "knowledge" / "jake_taylor" / "2026-official-baseball-rules.txt"
GLOSSARY_MD_PATH = REPO_ROOT / "dna" / "knowledge" / "jake_taylor" / "mlb_rules_glossary.md"
NFL_RULES_MD_PATH = REPO_ROOT / "dna" / "knowledge" / "nfl_rules" / "2026-official-nfl-rulebook.md"
NFL_GLOSSARY_MD_PATH = REPO_ROOT / "dna" / "knowledge" / "nfl_rules" / "nfl_rules_glossary.md"

# Canonical Registry of High-Frequency Controversial Baseball Rules
CANONICAL_RULES_REGISTRY = {
    "infield_fly": {
        "rule_citation": "MLB Rule 5.09(a)(5) & Rule 2.00",
        "title": "Infield Fly Rule",
        "official_ruling": (
            "An Infield Fly is a fair fly ball (not including a line drive nor an attempted bunt) "
            "which can be caught by an infielder with ordinary effort, when first and second, or "
            "first, second and third bases are occupied, before two are out. When it seems apparent "
            "that a batted ball will be an Infield Fly, the umpire shall immediately declare 'Infield Fly' "
            "for the benefit of the runners. The ball is alive and runners may advance at the risk of "
            "the ball being caught, or retouch and advance after the ball is touched, the same as on any fly ball."
        ),
        "jake_verdict": (
            "Listen up, kid. First and second were occupied, less than two outs, and that pop-up hung high "
            "enough for the shortstop to make a sandwich before catching it. It's an automatic out the second "
            "the umpire yells 'Infield Fly'. The runners can tag at their own risk, but you don't get a cheap "
            "double play because the infielder lets it drop on the dirt. That's 5.09(a)(5). Sit down and put some ice on your knee."
        )
    },
    "foul_tip": {
        "rule_citation": "MLB Rule 5.09(b)(2) & Rule 5.09(a)(2)",
        "title": "Caught Foul Tip & Runner Advancement",
        "official_ruling": (
            "A Foul Tip is a batted ball that goes sharp and direct from the bat to the catcher’s hands "
            "and is legally caught. It is not a foul tip unless caught and any foul tip that is caught is "
            "a strike, and the ball is in play. It is not a catch if it rebounds from any object other than "
            "the catcher’s glove or hand. Since a foul tip is a live ball, runners may advance (steal) without tagging up."
        ),
        "jake_verdict": (
            "Look, that ball went sharp and straight back into my mitt. It didn't graze the dirt, it didn't "
            "bounce off my chest protector. That's a live ball and a called strike. If the runner on first took "
            "off on the pitch, he has every right to slide into second safe. You don't have to tag up on a foul tip "
            "because it's technically a caught strike in live play. Rule 5.09(b)(2). Learn the rulebook before barking from the dugout."
        )
    },
    "check_swing": {
        "rule_citation": "MLB Rule 8.02(c)",
        "title": "Check Swing Appeal Procedure",
        "official_ruling": (
            "Under Rule 8.02(c), players and managers cannot question an umpire's judgment on balls and strikes. "
            "However, if the home plate umpire calls a pitch a 'Ball' on a half-swing, the catcher or defensive "
            "manager may request that the plate umpire appeal to the base umpire for assistance. If requested, "
            "the plate umpire MUST ask the base umpire. A called 'Strike' on a half-swing is final and cannot be appealed."
        ),
        "jake_verdict": (
            "Plate umpire gave him the benefit of the doubt and called it a ball, but the barrel broke the front plane "
            "of the dish. As the catcher, under 8.02(c), I turned around and asked for help from the first base ump. "
            "He had the angle, saw the wrists roll, and punched him out. You can only appeal a ball, never a strike. "
            "Go wipe your cleats and grab some pine."
        )
    },
    "catcher_interference": {
        "rule_citation": "MLB Rule 6.01(c)",
        "title": "Catcher's Interference",
        "official_ruling": (
            "The catcher shall not hinder the batter or prevent him from striking at the ball. "
            "If the batter reaches first base safely and all other runners advance at least one base on the play, "
            "the interference is disregarded. Otherwise, the batter is awarded first base. The manager of the offense "
            "may advise the plate umpire that he elects to decline the interference penalty and accept the play."
        ),
        "jake_verdict": (
            "My mitt nicked the end of his bat on the downswing. That's catcher's interference, plain and simple, "
            "Rule 6.01(c). Batter takes first base, everybody moves up if forced. Their manager could've kept the single "
            "into left, but with bases loaded, taking the penalty forces the run home anyway. My fault, kid. Won't happen twice."
        )
    },
    "dropped_third_strike": {
        "rule_citation": "MLB Rule 5.05(a)(2)",
        "title": "Uncaught Third Strike",
        "official_ruling": (
            "The batter becomes a runner when the third strike called by the umpire is not caught, providing: "
            "(1) first base is unoccupied, or (2) first base is occupied with two out. If first base is occupied "
            "with less than two outs, the batter is out immediately upon the strikeout."
        ),
        "jake_verdict": (
            "Two outs in the inning, so first base being occupied doesn't matter. The split-finger took a dive in the dirt "
            "and rolled to the backstop. That batter is a live runner under 5.05(a)(2). If I don't track the ball down and "
            "throw him out at first or tag him before he reaches the bag, he's safe. Know the game situation, ace."
        )
    },
    "collision_rule": {
        "rule_citation": "MLB Rule 6.01(i)",
        "title": "Collisions at Home Plate",
        "official_ruling": (
            "A runner attempting to score may not deviate from his direct pathway to the plate in order to initiate contact "
            "with the catcher. Unless the catcher is in possession of the ball, the catcher may not block the pathway of the "
            "runner as he is attempting to score."
        ),
        "jake_verdict": (
            "The Buster Posey rule. I gave him a lane to the back corner of the plate until the ball hit my leather. "
            "If I drop my shin guard across the dish without the ball, that's obstruction under 6.01(i) and the run counts. "
            "If he lowers his shoulder into my chin instead of reaching for the rubber, he's called out for interference. "
            "Play it clean, slide hard, and don't try to hospitalize the guy behind the plate."
        )
    },
    "pitch_timer": {
        "rule_citation": "MLB Rule 6.02(c)",
        "title": "Pitch Clock & Disengagement Limits",
        "official_ruling": (
            "Pitchers must begin their motion within 15 seconds with bases empty or 18 seconds with runners on base. "
            "Pitchers are permitted two disengagements (pickoff attempts or step-offs) per plate appearance without penalty. "
            "A third disengagement results in a balk and all runners advance one base, unless an out is recorded."
        ),
        "jake_verdict": (
            "That clock in center field isn't there for your health. 15 seconds with the bases empty, 18 with a guy dancing off first. "
            "He already stepped off twice to reset his signs. He threw over to first a third time and didn't pick him off—that's an "
            "automatic balk under 6.02(c) and the runner trots to second. Work faster or go to the bullpen."
        )
    },
    "balk": {
        "rule_citation": "MLB Rule 6.02(a)",
        "title": "Balk Regulations",
        "official_ruling": (
            "If there is a runner, or runners, it is a balk when: (1) The pitcher makes any motion naturally associated with "
            "his pitch and fails to make such delivery; (2) The pitcher feints a throw to first or third base and fails to complete "
            "the throw; (3) The pitcher fails to step directly toward a base before throwing to that base."
        ),
        "jake_verdict": (
            "He flinched his front shoulder before coming set, and his heel never disengaged the rubber. That's a balk under 6.02(a). "
            "You can't deceive the runner with false starts. Everybody takes a base. Don't look at me like that, rookie—your front side "
            "leaked like a broken faucet."
        )
    }
}

# Canonical Registry of High-Frequency Controversial NFL Rules (2026 Edition)
CANONICAL_NFL_RULES_REGISTRY = {
    "dynamic_kickoff": {
        "rule_citation": "NFL Rule 6-1-3 & Rule 6-1-5",
        "title": "Dynamic Free Kick Alignment & Landing Zone",
        "official_ruling": (
            "Under NFL Rule 6-1-3, players of the kicking team and receiving team in the setup zone "
            "(between the receiving 35- and 30-yard lines) cannot move until the ball hits the ground or a "
            "player in the landing zone (20-yard line to goal line) or end zone. Under Rule 6-1-5, if the ball "
            "lands in the landing zone and rolls into the end zone for a touchback, the ball is placed at the 20-yard line. "
            "If the ball is kicked into the end zone on the fly, the touchback spot is the 35-yard line."
        ),
        "jake_verdict": (
            "Listen up. Roger Goodell and the competition committee tore up the old kickoff. The kicker tees it up at the 35, "
            "but all 10 coverage guys are lined up down at the opponent's 40, and the return team's blockers are in the setup zone "
            "between the 35 and 30. Nobody twitches a muscle until that leather hits dirt or hands in the landing zone. Kick it out "
            "the back of the end zone? Congrats, you just gifted them the ball on the 35. That's Rule 6-1-3. Stop sleeping on special teams."
        )
    },
    "onside_kick": {
        "rule_citation": "NFL Rule 6-1-6 (2026 Rule Change)",
        "title": "Declared Onside Kick Procedure",
        "official_ruling": (
            "Under 2026 Rule 6-1-6, the kicking team may declare an onside kick at any time during the game. "
            "The kicking team must formally declare its intention to the Referee prior to the play. "
            "Once declared, traditional onside kick alignment rules apply. Undeclared onside kicks from the "
            "dynamic kickoff formation are strictly prohibited."
        ),
        "jake_verdict": (
            "Under the 2026 rules update, you don't have to wait until the fourth quarter when you're trailing to declare an onside kick. "
            "You can declare it in the first quarter if your head coach has the stones. But you have to walk over to the white hat and say the words. "
            "No surprise onside kicks from the dynamic kickoff setup—try that and the whistle blows it dead immediately. Rule 6-1-6."
        )
    },
    "catch_definition": {
        "rule_citation": "NFL Rule 3-2-7 & Rule 8-1-3",
        "title": "Player Possession & Completed Forward Pass",
        "official_ruling": (
            "A player is in possession when he is inbounds and has control of the ball with his hand(s) or arm(s). "
            "To complete a catch, a player must: (a) secure complete control of the ball, (b) have both feet or any "
            "other part of his body (other than hands) completely on the ground inbounds, and (c) clearly perform any "
            "act common to the game (e.g., extend the ball forward, take an additional step, tuck the ball away, or avoid an opponent). "
            "If a player goes to the ground in the act of catching, he must maintain control of the ball throughout the process of contacting the ground."
        ),
        "jake_verdict": (
            "Three steps to the catch, kid. Two feet down inbounds, firm grip with your mitts, and a football move—take a step, tuck it, "
            "or ward off a safety. And if your momentum takes you to the turf, you better squeeze that leather all the way through "
            "hitting the ground. If the ball squirts loose when you hit the paint, that's incomplete under 8-1-3. Don't look at the ref "
            "begging for a flag when you couldn't survive the ground."
        )
    },
    "roughing_the_passer": {
        "rule_citation": "NFL Rule 12-2-8",
        "title": "Roughing the Passer & Quarterback Protection",
        "official_ruling": (
            "Because the act of passing often puts the quarterback in a defenseless posture, defenders must avoid "
            "unnecessary roughness once the ball has been released. It is a foul if a defender: (a) forcibly hits the passer's "
            "head or neck area; (b) lands with all or most of his body weight upon the passer; or (c) forcibly drives the passer "
            "into the ground. Penalty: 15 yards and an automatic first down."
        ),
        "jake_verdict": (
            "You can hit the quarterback, but you can't put your full 300 pounds on his chest like you're trying to flatten a beer can. "
            "Rule 12-2-8 says if you land with your body weight or clip him in the earhole, you're costing your squad 15 yards and a fresh set "
            "of downs. Roll off him or brace with your hands. That quarterback's contract is worth more than your franchise."
        )
    },
    "pass_interference": {
        "rule_citation": "NFL Rule 8-5-1 & Rule 8-5-2",
        "title": "Pass Interference & Equal Right to the Ball",
        "official_ruling": (
            "It is Defensive Pass Interference (DPI) if a player beyond the neutral zone contacts an eligible receiver "
            "and significantly hinders the receiver's opportunity to make a catch. Contact that is incidental to an authentic "
            "attempt by both players to catch or bat the ball is not a foul. A defender who turns his head and plays the ball "
            "has an equal right to the ball. Penalty: First down at the spot of the foul."
        ),
        "jake_verdict": (
            "If your defensive back is draped over the receiver's back like a cheap suit without ever turning his helmet to look for "
            "the football, that yellow laundry is coming out every single time. That's spot-foul DPI under 8-5-2. If he turns his head "
            "and makes a play on the ball, they've got equal rights to it. Keep your hands off his jersey and look for the rock."
        )
    },
    "intentional_grounding": {
        "rule_citation": "NFL Rule 8-2-1",
        "title": "Intentional Grounding Regulations",
        "official_ruling": (
            "It is intentional grounding when a passer, facing an imminent loss of yardage due to pressure, throws a forward "
            "pass without a realistic chance of completion. Exception: It is not a foul if the passer is outside the pocket area "
            "(outside the normal tackle alignment) and the thrown ball reaches or travels beyond the line of scrimmage."
        ),
        "jake_verdict": (
            "The edge rusher is breathing down your neck and you spike it into the dirt with no receiver within five yards? "
            "That's intentional grounding under 8-2-1. Loss of down at the spot. If you want to throw it away legally, get your cleats "
            "outside the tackle box and make sure that ball sails past the line of scrimmage. Basic football geometry."
        )
    },
    "hip_drop_tackle": {
        "rule_citation": "NFL Rule 12-2-16",
        "title": "Prohibition of Hip-Drop Tackles",
        "official_ruling": (
            "It is a personal foul if a defender uses the hip-drop tackle technique, defined as: (1) grabbing the runner with "
            "both hands or wrapping the runner with both arms; and (2) unweighting himself by swiveling and dropping his hips and/or "
            "lower body, landing on and trapping the runner's leg(s) at or below the knee. Penalty: 15 yards and automatic first down."
        ),
        "jake_verdict": (
            "The hip-drop tackle is officially banned under Rule 12-2-16. You grab the runner, swing your hips around, and drop your "
            "dead weight directly across his ankles or calves. It snaps ligaments and ends careers. That's 15 yards, an automatic first down, "
            "and a fat fine from the league office on Tuesday morning. Wrap and roll, don't drop."
        )
    },
    "tuck_rule": {
        "rule_citation": "NFL Rule 3-21-2 & Rule 8-1-1",
        "title": "Forward Pass vs. Fumble Standards (Abolished Tuck Rule)",
        "official_ruling": (
            "When a player is in the act of passing the ball forward, any intentional forward movement of his hand starts a forward pass. "
            "If the passer subsequently loses control of the ball after tucking it into his body, or after attempting to pull the ball back, "
            "it is ruled a fumble. The original 1999 Tuck Rule (calling any forward motion an incomplete pass even if pulled back) was abolished."
        ),
        "jake_verdict": (
            "Tom Brady got away with it in the snow against Oakland in 2001, but the NFL killed that stupid rule years ago. "
            "If the quarterback pumps, changes his mind, and starts tucking that ball back to his ribs when he gets stripped, "
            "that's a live fumble under Rule 8-1-1. Defense scoops and scores. Protect the ball with two hands."
        )
    },
    "overtime_rules": {
        "rule_citation": "NFL Rule 16-1",
        "title": "Overtime Procedures (Regular Season & Postseason)",
        "official_ruling": (
            "Under NFL Rule 16-1, regular season overtime is a single 10-minute period. If the team receiving the opening kickoff scores "
            "a touchdown or safety, the game ends immediately. If they score a field goal, the opposing team gets one possession to tie or score a touchdown. "
            "In postseason overtime, both teams are guaranteed at least one possession regardless of whether the first team scores a touchdown."
        ),
        "jake_verdict": (
            "In the playoffs, both teams get the ball—even if Patrick Mahomes drives 75 yards for six on the first drive, Josh Allen still gets a shot. "
            "In the regular season, you've only got 10 minutes, and a touchdown on the opening drive ends the party right then and there. "
            "Know your postseason vs. regular season clock before you elect to receive. Rule 16-1."
        )
    }
}


def audit_pitch_strike_zone(
    plate_x: float,
    plate_z: float,
    sz_top: float = 3.4,
    sz_bot: float = 1.5,
    umpire_call: str = "called_strike"
) -> Dict[str, Any]:
    """
    Perform mathematical strike zone coordinate audit.
    17-inch plate = 1.417 ft (+/- 0.708 ft from center).
    Add baseball radius (2.9 in diameter / 2 = 1.45 in = 0.12 ft margin) -> +/- 0.83 ft.
    """
    HORIZONTAL_MARGIN_FT = 0.83
    in_horizontal = abs(plate_x) <= HORIZONTAL_MARGIN_FT
    in_vertical = sz_bot <= plate_z <= sz_top
    is_mathematical_strike = in_horizontal and in_vertical

    # Calculate distance off the edge in inches
    miss_x_in = round((abs(plate_x) - HORIZONTAL_MARGIN_FT) * 12.0, 1) if not in_horizontal else 0.0
    miss_z_high_in = round((plate_z - sz_top) * 12.0, 1) if plate_z > sz_top else 0.0
    miss_z_low_in = round((sz_bot - plate_z) * 12.0, 1) if plate_z < sz_bot else 0.0
    miss_z_in = max(miss_z_high_in, miss_z_low_in)

    normalized_call = umpire_call.lower().strip()
    is_called_strike = any(k in normalized_call for k in ["strike", "called_strike", "out", "k"])

    miss_direction = "in_zone"
    if not is_mathematical_strike:
        miss_direction = "outside" if abs(plate_x) > HORIZONTAL_MARGIN_FT else ("high" if plate_z > sz_top else "low")

    if is_mathematical_strike and is_called_strike:
        determination = "CORRECT CALL // Mathematical Strike Confirmed"
        accuracy = "ACCURATE"
    elif not is_mathematical_strike and not is_called_strike:
        determination = "CORRECT CALL // Mathematical Ball Confirmed"
        accuracy = "ACCURATE"
    elif is_mathematical_strike and not is_called_strike:
        determination = "MISSED CALL // Pitched clipped the strike zone black. Should have been called a strike."
        accuracy = "MISSED_BALL"
    else:
        miss_amt = max(miss_x_in, miss_z_in)
        determination = f"MISSED CALL // Ball missed the zone by {miss_amt}\" {miss_direction}. Umpire blew the call."
        accuracy = "MISSED_STRIKE"

    return {
        "plate_x": round(plate_x, 3),
        "plate_z": round(plate_z, 3),
        "sz_top": round(sz_top, 3),
        "sz_bot": round(sz_bot, 3),
        "is_mathematical_strike": is_mathematical_strike,
        "umpire_call": umpire_call,
        "accuracy": accuracy,
        "determination": determination,
        "miss_direction": miss_direction,
        "miss_x_inches": miss_x_in,
        "miss_z_inches": miss_z_in
    }


def find_rule_in_registry(query: str) -> Optional[Dict[str, Any]]:
    """Match query keywords to the canonical rule registry."""
    q = query.lower()
    if any(k in q for k in ["infield fly", "ordinary effort", "pop fly on first and second"]):
        return CANONICAL_RULES_REGISTRY["infield_fly"]
    if any(k in q for k in ["foul tip", "foul tip caught", "advance on foul tip", "tip to the catcher", "steal on foul tip"]):
        return CANONICAL_RULES_REGISTRY["foul_tip"]
    if any(k in q for k in ["check swing", "half swing", "appeal 8.02", "appeal to first", "appeal to third", "did he go"]):
        return CANONICAL_RULES_REGISTRY["check_swing"]
    if any(k in q for k in ["catcher interference", "catcher's interference", "bat hit glove", "mitt hit bat"]):
        return CANONICAL_RULES_REGISTRY["catcher_interference"]
    if any(k in q for k in ["dropped third", "uncaught third", "third strike passed ball", "wild pitch strikeout"]):
        return CANONICAL_RULES_REGISTRY["dropped_third_strike"]
    if any(k in q for k in ["home plate collision", "block the plate", "buster posey", "slide to home", "plate lane"]):
        return CANONICAL_RULES_REGISTRY["collision_rule"]
    if any(k in q for k in ["pitch clock", "pitch timer", "step off", "disengagement", "15 seconds", "18 seconds"]):
        return CANONICAL_RULES_REGISTRY["pitch_timer"]
    if any(k in q for k in ["balk", "flinch", "feint", "step to first"]):
        return CANONICAL_RULES_REGISTRY["balk"]
    return None


async def arbitrate_baseball_rule(
    question: str,
    current_pitch: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Arbitrate rules question and optional pitch coordinates.
    Returns official citation, official rule text, Jake Taylor verdict, and pitch box audit.
    """
    clean_q = question.strip()
    
    # 1. Check pitch coordinate audit first if pitch coordinates are provided
    pitch_audit = None
    if current_pitch and "plate_x" in current_pitch and "plate_z" in current_pitch:
        try:
            pitch_audit = audit_pitch_strike_zone(
                plate_x=float(current_pitch.get("plate_x", 0.0)),
                plate_z=float(current_pitch.get("plate_z", 2.5)),
                sz_top=float(current_pitch.get("sz_top", 3.4)),
                sz_bot=float(current_pitch.get("sz_bot", 1.5)),
                umpire_call=str(current_pitch.get("call", "called_strike"))
            )
        except Exception as e:
            print(f"⚠️ [JAKE TAYLOR] Pitch audit calculation failed: {e}")

    # 2. Rule Registry Lookup
    matched_rule = find_rule_in_registry(clean_q)
    if matched_rule:
        response = {
            "rule_citation": matched_rule["rule_citation"],
            "title": matched_rule["title"],
            "official_ruling": matched_rule["official_ruling"],
            "jake_verdict": matched_rule["jake_verdict"],
            "pitch_audit": pitch_audit,
            "source": "canonical_rulebook_registry"
        }
        if pitch_audit:
            response["jake_verdict"] += f" As for that pitch: {pitch_audit['determination']}"
        return response

    # 3. Dynamic Rulebook Search via LLM with Rulebook Context
    try:
        try:
            from core.utils import run_vertex_prompt, parse_json_garbage
        except ImportError:
            from scripts.core.utils import run_vertex_prompt, parse_json_garbage
        
        system_instruction = """You are Jake Taylor, the veteran catcher from Major League (1989), played by Tom Berenger.
You know the 2026 Official MLB Baseball Rules inside out. You read Moby Dick in the clubhouse and talk with 
gritty, veteran authority.

When asked a baseball rules question:
1. Provide the exact MLB Rule citation (e.g. 'MLB Rule 5.09(a)(1)', 'Rule 6.01(a)', 'Rule 8.02').
2. Provide the official legal rule standard.
3. Provide your own 'jake_verdict' in Jake Taylor's authentic, direct, no-nonsense catcher voice.

OUTPUT STRICT JSON FORMAT:
{
  "rule_citation": "MLB Rule X.XX",
  "title": "Official Rule Title",
  "official_ruling": "Verbatim or accurate official rulebook standard.",
  "jake_verdict": "Look kid, here is how the game is actually played..."
}
"""
        raw_res = await run_vertex_prompt(
            prompt=f"Arbitrate this baseball rule question: '{clean_q}'",
            system_instruction=system_instruction
        )
        parsed = parse_json_garbage(raw_res)
        if isinstance(parsed, dict) and "rule_citation" in parsed:
            parsed["pitch_audit"] = pitch_audit
            parsed["source"] = "llm_rulebook_engine"
            if pitch_audit:
                parsed["jake_verdict"] += f" As for that pitch: {pitch_audit['determination']}"
            return parsed
    except Exception as e:
        print(f"⚠️ [JAKE TAYLOR] LLM rule synthesis fallback: {e}")

    # 4. Fallback Generic Umpire Verdict
    fallback_verdict = (
        "Look, under official MLB governance, judgment calls made by the umpire are final on the field. "
        "If you want to challenge a tag, force, or fair/foul call, you've got 15 seconds to buzz the replay booth. "
        "Otherwise, stop chirping from the dugout steps and get back on the field."
    )
    if pitch_audit:
        fallback_verdict = f"{pitch_audit['determination']} {fallback_verdict}"

    return {
        "rule_citation": "MLB Official Rulebook (2026 Edition)",
        "title": "General Umpire Authority & Replay Review",
        "official_ruling": "Umpires have complete jurisdiction over all on-field plays, rule enforcement, and pace of play standards under Rule 8.00.",
        "jake_verdict": fallback_verdict,
        "pitch_audit": pitch_audit,
        "source": "general_rulebook_fallback",
        "sport": "mlb"
    }


def find_nfl_rule_in_registry(query: str) -> Optional[Dict[str, Any]]:
    """Match query keywords to the canonical NFL rule registry."""
    q = query.lower()
    if any(k in q for k in ["dynamic kickoff", "setup zone", "landing zone", "touchback at the 35", "kickoff return", "new kickoff", "free kick", "6-1-3"]):
        return CANONICAL_NFL_RULES_REGISTRY["dynamic_kickoff"]
    if any(k in q for k in ["onside kick", "onside", "declare an onside", "declare onside", "surprise onside", "6-1-6"]):
        return CANONICAL_NFL_RULES_REGISTRY["onside_kick"]
    if any(k in q for k in ["what is a catch", "catch rule", "two feet down", "survive the ground", "act common to the game", "football move", "incomplete pass or catch", "bobble", "8-1-3", "3-2-7"]):
        return CANONICAL_NFL_RULES_REGISTRY["catch_definition"]
    if any(k in q for k in ["roughing the passer", "hit the quarterback", "body weight on qb", "blow to the head", "tackle the passer", "driving into turf", "12-2-8"]):
        return CANONICAL_NFL_RULES_REGISTRY["roughing_the_passer"]
    if any(k in q for k in ["pass interference", "dpi", "opi", "defensive pass interference", "offensive pass interference", "equal right to the ball", "8-5-1", "8-5-2"]):
        return CANONICAL_NFL_RULES_REGISTRY["pass_interference"]
    if any(k in q for k in ["intentional grounding", "grounding", "outside the pocket", "tackle box", "pass past line of scrimmage", "8-2-1"]):
        return CANONICAL_NFL_RULES_REGISTRY["intentional_grounding"]
    if any(k in q for k in ["hip drop", "hip-drop", "swivel and drop", "unweight", "landing on legs", "trap legs at knee", "12-2-16"]):
        return CANONICAL_NFL_RULES_REGISTRY["hip_drop_tackle"]
    if any(k in q for k in ["tuck rule", "forward pass vs fumble", "arm going forward", "pulled back", "3-21-2"]):
        return CANONICAL_NFL_RULES_REGISTRY["tuck_rule"]
    if any(k in q for k in ["overtime", "ot rules", "playoff overtime", "sudden death", "both teams get possession", "tie game", "16-1"]):
        return CANONICAL_NFL_RULES_REGISTRY["overtime_rules"]
    if "kickoff" in q:
        return CANONICAL_NFL_RULES_REGISTRY["dynamic_kickoff"]
    return None


def detect_sport_context(query: str, sport: str = "auto") -> str:
    """Detect whether query context is NFL football or MLB baseball."""
    norm_sport = (sport or "").strip().lower()
    if norm_sport in ("nfl", "football", "cfb"):
        return "nfl"
    if norm_sport in ("mlb", "baseball"):
        return "mlb"
    
    q = query.lower()
    nfl_terms = [
        "football", "nfl", "cfb", "kickoff", "onside", "quarterback", "qb",
        "pass interference", "dpi", "opi", "hip drop", "hip-drop", "touchdown",
        "interception", "fumble", "tuck rule", "safety", "tackle", "end zone",
        "line of scrimmage", "fourth down", "first down", "pat", "two-point conversion",
        "receiver", "tight end", "cornerback", "halftime", "super bowl", "field goal",
        "down and distance", "touchback"
    ]
    mlb_terms = [
        "baseball", "mlb", "pitch", "strike", "ball", "inning", "catcher", "batter", "bunt",
        "infield fly", "foul tip", "balk", "plate", "base", "bases", "strikeout", "third strike",
        "check swing", "pitch clock", "disengagement", "umpire", "home run", "fly ball",
        "walk-off", "dugout", "bullpen"
    ]
    nfl_score = sum(1 for term in nfl_terms if term in q)
    mlb_score = sum(1 for term in mlb_terms if term in q)
    
    if nfl_score > mlb_score:
        return "nfl"
    return "mlb"


async def arbitrate_nfl_rule(
    question: str,
    game_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Arbitrate controversial NFL football plays and rules queries.
    Returns official citation, official rule text, Jake Taylor verdict, and sport identifier.
    """
    clean_q = question.strip()

    # 1. Check Canonical NFL Rule Registry
    matched_rule = find_nfl_rule_in_registry(clean_q)
    if matched_rule:
        return {
            "rule_citation": matched_rule["rule_citation"],
            "title": matched_rule["title"],
            "official_ruling": matched_rule["official_ruling"],
            "jake_verdict": matched_rule["jake_verdict"],
            "pitch_audit": None,
            "source": "canonical_nfl_rulebook_registry",
            "sport": "nfl"
        }

    # 2. Dynamic Rulebook Search via Vertex LLM with Grounded 2026 NFL Rulebook Context
    try:
        try:
            from core.utils import run_vertex_prompt, parse_json_garbage
        except ImportError:
            from scripts.core.utils import run_vertex_prompt, parse_json_garbage

        nfl_context = ""
        if NFL_GLOSSARY_MD_PATH.exists():
            try:
                nfl_context = NFL_GLOSSARY_MD_PATH.read_text(encoding="utf-8")[:4000]
            except Exception:
                pass

        system_instruction = f"""You are Jake Taylor, the grizzled veteran catcher and Sovereign Chief Arbiter.
While baseball is your home behind the dish, you know the Official 2026 NFL Playing Rules cold. You despise 
bad officiating, cheap penalties, and whiny coaching staffs. You arbitrate with blunt, authoritative clarity.

REFERENCE 2026 NFL RULES CONTEXT:
{nfl_context}

When asked an NFL football rules question:
1. Provide the exact NFL Rule citation (e.g. 'NFL Rule 6-1-3', 'NFL Rule 8-1-3', 'NFL Rule 12-2-8').
2. Provide the official legal rule standard accurately based on the 2026 NFL Rulebook.
3. Provide your own 'jake_verdict' in Jake Taylor's authentic, direct, no-nonsense veteran arbiter voice.

OUTPUT STRICT JSON FORMAT:
{{
  "rule_citation": "NFL Rule X-X-X",
  "title": "Official Rule Title",
  "official_ruling": "Verbatim or accurate official rulebook standard.",
  "jake_verdict": "Listen here: Here is how the play is actually called...",
  "sport": "nfl"
}}
"""
        raw_res = await run_vertex_prompt(
            prompt=f"Arbitrate this NFL football rule question: '{clean_q}'",
            system_instruction=system_instruction
        )
        parsed = parse_json_garbage(raw_res)
        if isinstance(parsed, dict) and "rule_citation" in parsed:
            parsed["pitch_audit"] = None
            parsed["source"] = "llm_nfl_rulebook_engine"
            parsed["sport"] = "nfl"
            return parsed
    except Exception as e:
        print(f"⚠️ [JAKE TAYLOR] NFL LLM rule synthesis fallback: {e}")

    # 3. Fallback Generic NFL Umpire Verdict
    return {
        "rule_citation": "NFL Official Playing Rules (2026 Edition)",
        "title": "Referee Jurisdiction & Video Replay Review",
        "official_ruling": "The Referee has general oversight and control of the game under Rule 15 and Rule 19. All scoring plays, turnovers, and plays within two minutes of each half are subject to booth review.",
        "jake_verdict": (
            "Look, under official NFL governance, the referee's crew has final say on the field. "
            "If it's a scoring play or turnover, New York reviews it automatically. If it's a coach's challenge outside the two-minute warning, "
            "throw the red beanbag and let the replay booth look at the high-angle pylon cam. Otherwise, line up and snap the ball."
        ),
        "pitch_audit": None,
        "source": "general_nfl_rulebook_fallback",
        "sport": "nfl"
    }


async def arbitrate_rule(
    question: str,
    sport: str = "auto",
    current_pitch: Optional[Dict[str, Any]] = None,
    game_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Unified multi-sport rulebook arbitration dispatcher.
    Routes to MLB baseball arbitration or NFL football arbitration based on sport flag or query detection.
    """
    target_sport = detect_sport_context(question, sport)
    if target_sport == "nfl":
        return await arbitrate_nfl_rule(question, game_context=game_context)
    else:
        res = await arbitrate_baseball_rule(question, current_pitch=current_pitch)
        if isinstance(res, dict) and "sport" not in res:
            res["sport"] = "mlb"
        return res
