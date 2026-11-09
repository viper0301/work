import os
import random
import uuid
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Wordle API Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

WORD_BANK = [
    "APPLE", "TRAIN", "HOUSE", "PLANT", "SMART", "WORLD", "LIGHT", "BRAIN", "CLOUD", "WATER",
    "ABOUT", "ABOVE", "ACTOR", "ACUTE", "ADMIT", "ADOPT", "ADULT", "AFTER", "AGAIN", "AGENT",
    "AGREE", "AHEAD", "ALARM", "ALBUM", "ALERT", "ALIEN", "ALIKE", "ALIVE", "ALLOW", "ALONE",
    "ALONG", "ALTER", "AMONG", "ANGER", "ANGLE", "ANGRY", "APART", "APPLY", "ARGUE", "ARISE",
    "ARRAY", "ARROW", "ASIDE", "ASSET", "AUDIO", "AUDIT", "AVOID", "AWAKE", "AWARE", "BADGE",
    "BAKER", "BASIC", "BASIS", "BEACH", "BEGIN", "BEING", "BELOW", "BENCH", "BLACK", "BLAME",
    "BLANK", "BLAST", "BLEED", "BLEND", "BLOCK", "BLOOD", "BOARD", "BOAST", "BONUS", "BOOST",
    "BOUND", "BREAD", "BREAK", "BRICK", "BRIEF", "BRING", "BROAD", "BROWN", "BRUSH", "BUILD",
    "BUNCH", "BUYER", "CABLE", "CANDY", "CARGO", "CARRY", "CATCH", "CAUSE", "CHAIN", "CHAIR",
    "CHALK", "CHARM", "CHART", "CHASE", "CHEAP", "CHECK", "CHEST", "CHIEF", "CHILD", "CHOSE",
    "CIVIL", "CLAIM", "CLASS", "CLEAN", "CLEAR", "CLIMB", "CLOCK", "CLOSE", "COACH", "COAST",
    "COUNT", "COURT", "COVER", "CRASH", "CREAM", "CRIME", "CROSS", "CROWD", "CROWN", "CURVE",
    "CYCLE", "DAILY", "DANCE", "DEATH", "DELAY", "DEPTH", "DRAFT", "DRAMA", "DREAM", "DRIVE",
    "EAGLE", "EARLY", "EARTH", "EIGHT", "EMPTY", "ENEMY", "ENJOY", "ENTER", "EQUAL", "ERROR",
    "EVENT", "EVERY", "EXACT", "EXIST", "FAITH", "FALSE", "FAULT", "FIELD", "FIGHT", "FINAL",
    "FIRST", "FLAME", "FLASH", "FLOAT", "FLOOR", "FLOUR", "FLUID", "FOCUS", "FORCE", "FORTH",
    "FORTY", "FORUM", "FRAME", "FRESH", "FRONT", "FRUIT", "GIANT", "GLASS", "GLOBE", "GRACE",
    "GRADE", "GRAND", "GRANT", "GRASS", "GREAT", "GREEN", "GROUP", "GUARD", "GUESS", "GUIDE",
    "HAPPY", "HEART", "HEAVY", "HOTEL", "HUMAN", "IMAGE", "INDEX", "INPUT", "ISSUE", "JUDGE",
    "KNIFE", "LAYER", "LEMON", "LEVEL", "LIMIT", "LUNCH", "MAGIC", "MAJOR", "MARCH", "MATCH",
    "MEDAL", "MONEY", "MONTH", "MUSIC", "NIGHT", "NOVEL", "NURSE", "OCEAN", "OFFER", "ORDER"
]

games_db: Dict[str, dict] = {}

global_stats = {
    "total_games": 0,
    "wins": 0
}

def get_stats_payload():
    total = global_stats["total_games"]
    wins = global_stats["wins"]
    win_rate = (wins / total * 100) if total > 0 else 0.0
    return {
        "total": total,
        "wins": wins,
        "win_rate": round(win_rate, 1)
    }

class NewGameRequest(BaseModel):
    hard_mode: Optional[bool] = False  # 任務四：接收可選參數 hard_mode，預設為 False

class GuessRequest(BaseModel):
    game_id: str
    guess: str

@app.post("/api/new-game")
def start_new_game(req: NewGameRequest = None):
    """ 建立新一局遊戲，支援 hard_mode 參數 """
    game_id = str(uuid.uuid4())
    target_word = random.choice(WORD_BANK)
    
    global_stats["total_games"] += 1

    is_hard = req.hard_mode if req else False

    games_db[game_id] = {
        "target": target_word,
        "status": "PLAYING",
        "attempts": 0,
        "counted_win": False,
        "hard_mode": is_hard,
        "locked_greens": {}  # 任務四：記錄已被揭露為綠色的位置 {index: letter}
    }
    
    return {
        "game_id": game_id,
        "message": "New game started!",
        "stats": get_stats_payload()
    }

@app.post("/api/guess")
def process_guess(req: GuessRequest):
    """ 接收玩家猜測，比對答案並進行硬核模式驗證 """
    game_id = req.game_id
    guess = req.guess.upper()

    if game_id not in games_db:
        raise HTTPException(status_code=404, detail="Game session not found.")
    
    if len(guess) != 5:
        raise HTTPException(status_code=400, detail="Word must be 5 letters.")

    if guess not in WORD_BANK:
        raise HTTPException(status_code=400, detail="Word not in dictionary")

    game_info = games_db[game_id]
    target = game_info["target"]

    if game_info["status"] != "PLAYING":
        raise HTTPException(status_code=400, detail="Game already ended.")

    # 任務四：若為硬核模式 (hard_mode == True)，驗證是否符合先前已確認為綠色的字母與位置
    if game_info["hard_mode"]:
        locked_greens = game_info["locked_greens"]
        for idx, expected_char in locked_greens.items():
            if guess[idx] != expected_char:
                raise HTTPException(
                    status_code=400, 
                    detail="Hard Mode: Must use revealed hint at green position"
                )

    feedback = ["absent"] * 5
    target_letter_counts = {}

    for char in target:
        target_letter_counts[char] = target_letter_counts.get(char, 0) + 1

    for i in range(5):
        if guess[i] == target[i]:
            feedback[i] = "correct"
            target_letter_counts[guess[i]] -= 1
            # 任務四：記錄綠色位置供後續硬核模式檢查
            game_info["locked_greens"][i] = guess[i]

    for i in range(5):
        if feedback[i] != "correct" and guess[i] in target:
            if target_letter_counts[guess[i]] > 0:
                feedback[i] = "present"
                target_letter_counts[guess[i]] -= 1

    game_info["attempts"] += 1
    is_correct = (guess == target)
    is_game_over = is_correct or (game_info["attempts"] >= 6)

    if is_correct:
        game_info["status"] = "WON"
        if not game_info["counted_win"]:
            global_stats["wins"] += 1
            game_info["counted_win"] = True
    elif is_game_over:
        game_info["status"] = "LOST"

    return {
        "guess": guess,
        "feedback": feedback,
        "is_correct": is_correct,
        "is_game_over": is_game_over,
        "tries_left": max(0, 6 - game_info["attempts"]),
        "target_word": target if is_game_over else None,
        "stats": get_stats_payload()
    }

@app.get("/api/stats")
def get_stats():
    return get_stats_payload()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
