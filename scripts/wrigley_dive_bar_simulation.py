import asyncio
import websockets
import json

async def simulate_dive_bar():
    # Sequence of injected prompts outlining a narrative arc in a Wrigleyville dive bar
    interactions = [
        {"node": "bleacher_bum_bill", "text": "Set the scene: you are three Old Styles deep at Murphy's Bleachers. You see a depressed Mets fan in a Pete Alonso jersey sitting alone at the end of the bar. Yell something obnoxiously cheerful about the Cubs' chances today."},
        {"node": "barf", "text": "React to the loud Cubs fan down the bar. Tell him that cheering for a baseball team is just volunteering for emotional distress, and point out that the Mets entering 0-8 is just the universe establishing its baseline of suffering."},
        {"node": "ivy_inspector_ian", "text": "Walk into the bar with a tape measure around your neck. Start examining the brick walls of Murphy's. Overhear the Mets fan and offer a bizarre conspiracy theory about how the ivy at Wrigley Field absorbs negative energy from losing teams."},
        {"node": "7_train_terry", "text": "Barge into the bar holding a half-eaten pastrami sandwich. Defend your fellow Mets fan (Barf). Tell these deep-dish Chicago weirdos that real baseball is played in Queens, and that 0-8 just means they have 'em right where they want 'em."},
        {"node": "dot", "text": "Interrupt the argument from your position as the objective bar television. Output a cold statistical analysis showing how mathematically improbable an 0-8 start is for a payroll of $340M, draining all the emotion from the room."},
        {"node": "bartmans_ghost", "text": "Materialize in the corner booth wearing a Walkman. Whine about how everyone acts cursed until they've ruined a playoff game. Warn the Mets fans that curses are real, and the wind is blowing out today."},
        {"node": "uncle_stevie_stan", "text": "Order a $400 bottle of whiskey and tell everyone to put it on Steve Cohen's tab. Start arguing with Bartman's Ghost about how infinite money cures all curses, despite what the analytics (Dot) just said."},
        {"node": "ivy_truther", "text": "Start raving about how Steve Cohen's money is actually funding a subterranean weather control machine under Citi Field that is malfunctioning and causing the Mets to lose."},
        {"node": "barf", "text": "Drop your head to the sticky bar surface. Conclude that the weather control machine, the cursed ivy, and statistics don't matter, because existence is a flat circle of grim, Mets-related fatalities."},
        {"node": "wardy", "text": "Wrap up the incredible dive bar chaos! Welcome everyone to the NYM @ CHC Pre-Game Show, summarizing the absolute insanity that just unfolded at Murphy's Bleachers!"}
    ]
    
    try:
        # Stop existing background jobs to avoid collision
        print("Starting Wrigleyville Dive Bar Simulation...")
        for i, interaction in enumerate(interactions):
            try:
                update_payload = {
                    "type": "custom_prompt",
                    "persona": interaction['node'],
                    "prompt": f"DIVE BAR SCENE OVERRIDE: {interaction['text']}",
                    "target_game_pk": "824693"
                }
                async with websockets.connect("ws://127.0.0.1:8008/ws") as ws:
                    await ws.send(json.dumps(update_payload))
                print(f"🎬 Scene {i+1}/10 Triggered: [{interaction['node']}] -> {interaction['text'][:60]}...")
            except Exception as e:
                print(f"Failed to inject scene {i+1}: {e}")
            
            # Wait 45 seconds between beats to let LLMs generate and socket to resolve
            await asyncio.sleep(45)
            
        print("🍻 Dive Bar Pre-Game Simulation Complete!")
    except Exception as e:
            print(f"Simulation crashed: {e}")

if __name__ == "__main__":
    asyncio.run(simulate_dive_bar())
