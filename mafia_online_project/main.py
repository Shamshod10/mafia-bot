import asyncio
import os
import secrets
import string
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import aiosqlite
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://example.com").strip()
DB_PATH = os.getenv("DB_PATH", "mafia.db")
router = Router()
bot = Bot(BOT_TOKEN) if BOT_TOKEN else None
dp = Dispatcher()
dp.include_router(router)

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            games INTEGER NOT NULL DEFAULT 0,
            wins INTEGER NOT NULL DEFAULT 0,
            xp INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS rooms (
            code TEXT PRIMARY KEY,
            host_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'lobby',
            phase TEXT NOT NULL DEFAULT 'lobby',
            round_no INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS room_players (
            room_code TEXT NOT NULL,
            telegram_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            role TEXT,
            alive INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (room_code, telegram_id)
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_code TEXT NOT NULL,
            telegram_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS votes (
            room_code TEXT NOT NULL,
            round_no INTEGER NOT NULL,
            voter_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            PRIMARY KEY (room_code, round_no, voter_id)
        );
        """)
        await db.commit()

def make_code():
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))

@router.message(CommandStart())
async def start(message: Message):
    uid = message.from_user.id
    name = message.from_user.full_name or message.from_user.username or "O'yinchi"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO players(telegram_id, username) VALUES(?, ?) "
            "ON CONFLICT(telegram_id) DO UPDATE SET username=excluded.username",
            (uid, name)
        )
        await db.commit()
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎭 Mafia Online'ni ochish", web_app=WebAppInfo(url=WEBAPP_URL))
    ]])
    await message.answer(
        "🕴️ <b>MAFIA ONLINE</b>\n\n"
        "Qora, qizil va oltin dunyoga xush kelibsiz.\n"
        "Xona yarating, do'stlaringizni taklif qiling va mafiyani toping!\n\n"
        "O'yinni boshlash uchun pastdagi tugmani bosing.",
        reply_markup=kb, parse_mode="HTML"
    )

class PlayerIn(BaseModel):
    telegram_id: int = Field(gt=0)
    username: str = Field(min_length=1, max_length=64)

class CreateRoom(PlayerIn):
    pass

class JoinRoom(PlayerIn):
    code: str = Field(min_length=6, max_length=6)

class ChatMessage(PlayerIn):
    code: str
    body: str = Field(min_length=1, max_length=400)

class VoteIn(PlayerIn):
    code: str
    target_id: int

class StartGame(PlayerIn):
    code: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    if bot:
        asyncio.create_task(dp.start_polling(bot))
    yield
    if bot:
        await bot.session.close()

app = FastAPI(title="Mafia Online API", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def index():
    return FileResponse("static/index.html")

@app.get("/api/health")
async def health():
    return {"ok": True, "project": "Mafia Online"}

async def ensure_player(db, p):
    await db.execute(
        "INSERT INTO players(telegram_id, username) VALUES(?, ?) "
        "ON CONFLICT(telegram_id) DO UPDATE SET username=excluded.username",
        (p.telegram_id, p.username)
    )

@app.post("/api/rooms")
async def create_room(p: CreateRoom):
    async with aiosqlite.connect(DB_PATH) as db:
        await ensure_player(db, p)
        code = make_code()
        while await (await db.execute("SELECT code FROM rooms WHERE code=?", (code,))).fetchone():
            code = make_code()
        await db.execute("INSERT INTO rooms(code, host_id, created_at) VALUES(?,?,?)",
                         (code, p.telegram_id, datetime.now(timezone.utc).isoformat()))
        await db.execute("INSERT INTO room_players(room_code, telegram_id, username) VALUES(?,?,?)",
                         (code, p.telegram_id, p.username))
        await db.commit()
    return {"code": code}

@app.post("/api/rooms/join")
async def join_room(p: JoinRoom):
    code = p.code.upper()
    async with aiosqlite.connect(DB_PATH) as db:
        room = await (await db.execute("SELECT status FROM rooms WHERE code=?", (code,))).fetchone()
        if not room:
            raise HTTPException(404, "Bunday xona topilmadi")
        if room[0] != "lobby":
            raise HTTPException(400, "Bu xona allaqachon boshlangan")
        count = (await (await db.execute("SELECT COUNT(*) FROM room_players WHERE room_code=?", (code,))).fetchone())[0]
        existing = await (await db.execute("SELECT 1 FROM room_players WHERE room_code=? AND telegram_id=?",
                                           (code, p.telegram_id))).fetchone()
        if not existing and count >= 15:
            raise HTTPException(400, "Xona to'lgan (15/15)")
        await ensure_player(db, p)
        await db.execute("INSERT OR IGNORE INTO room_players(room_code, telegram_id, username) VALUES(?,?,?)",
                         (code, p.telegram_id, p.username))
        await db.commit()
    return {"ok": True, "code": code}

@app.get("/api/rooms/{code}")
async def room_state(code: str, telegram_id: int):
    code = code.upper()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        room = await (await db.execute("SELECT * FROM rooms WHERE code=?", (code,))).fetchone()
        if not room:
            raise HTTPException(404, "Xona topilmadi")
        players = await (await db.execute(
            "SELECT telegram_id, username, alive, role FROM room_players WHERE room_code=? ORDER BY rowid",
            (code,))).fetchall()
        me = next((dict(x) for x in players if x["telegram_id"] == telegram_id), None)
        if not me:
            raise HTTPException(403, "Siz bu xonada emassiz")
        # Roles are private: each player receives only their own role.
        safe_players = [{"telegram_id": x["telegram_id"], "username": x["username"],
                         "alive": bool(x["alive"]),
                         "role": x["role"] if x["telegram_id"] == telegram_id or room["status"] == "finished" else None}
                        for x in players]
        msgs = await (await db.execute(
            "SELECT username, body, created_at FROM messages WHERE room_code=? ORDER BY id DESC LIMIT 40",
            (code,))).fetchall()
        return {"room": dict(room), "players": safe_players, "me": me,
                "messages": [dict(m) for m in reversed(msgs)]}

@app.post("/api/rooms/start")
async def start_game(p: StartGame):
    code = p.code.upper()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        room = await (await db.execute("SELECT * FROM rooms WHERE code=?", (code,))).fetchone()
        if not room:
            raise HTTPException(404, "Xona topilmadi")
        if room["host_id"] != p.telegram_id:
            raise HTTPException(403, "Faqat xona egasi boshlashi mumkin")
        if room["status"] != "lobby":
            raise HTTPException(400, "O'yin boshlangan")
        rows = await (await db.execute("SELECT telegram_id FROM room_players WHERE room_code=?", (code,))).fetchall()
        if len(rows) < 5:
            raise HTTPException(400, "Boshlash uchun kamida 5 o'yinchi kerak")
        import random
        ids = [r["telegram_id"] for r in rows]
        roles = ["mafia"] * max(1, len(ids)//4) + ["doctor", "detective"]
        roles += ["citizen"] * (len(ids)-len(roles))
        random.shuffle(roles)
        for uid, role in zip(ids, roles):
            await db.execute("UPDATE room_players SET role=? WHERE room_code=? AND telegram_id=?",
                             (role, code, uid))
        await db.execute("UPDATE rooms SET status='playing', phase='night', round_no=1 WHERE code=?", (code,))
        await db.commit()
    return {"ok": True, "message": "O'yin boshlandi. Birinchi tun!"}

@app.post("/api/chat")
async def send_chat(p: ChatMessage):
    code = p.code.upper()
    async with aiosqlite.connect(DB_PATH) as db:
        member = await (await db.execute(
            "SELECT rp.alive, r.status, r.phase FROM room_players rp JOIN rooms r ON r.code=rp.room_code "
            "WHERE rp.room_code=? AND rp.telegram_id=?", (code, p.telegram_id))).fetchone()
        if not member:
            raise HTTPException(403, "Xonada emassiz")
        if member[1] == "playing" and (member[0] == 0 or member[2] != "day"):
            raise HTTPException(400, "Chat faqat tirik o'yinchilar uchun kunduz kuni ochiq")
        await db.execute("INSERT INTO messages(room_code, telegram_id, username, body, created_at) VALUES(?,?,?,?,?)",
                         (code, p.telegram_id, p.username, p.body.strip(),
                          datetime.now(timezone.utc).isoformat()))
        await db.commit()
    return {"ok": True}

@app.post("/api/vote")
async def vote(p: VoteIn):
    code = p.code.upper()
    async with aiosqlite.connect(DB_PATH) as db:
        room = await (await db.execute("SELECT status, phase, round_no FROM rooms WHERE code=?", (code,))).fetchone()
        if not room or room[0] != "playing" or room[1] != "day":
            raise HTTPException(400, "Ovoz berish faqat kunduzgi bosqichda")
        voter = await (await db.execute("SELECT alive FROM room_players WHERE room_code=? AND telegram_id=?",
                                        (code, p.telegram_id))).fetchone()
        target = await (await db.execute("SELECT alive FROM room_players WHERE room_code=? AND telegram_id=?",
                                         (code, p.target_id))).fetchone()
        if not voter or not target or not voter[0] or not target[0] or p.telegram_id == p.target_id:
            raise HTTPException(400, "Bu ovoz berish mumkin emas")
        await db.execute("INSERT INTO votes(room_code, round_no, voter_id, target_id) VALUES(?,?,?,?) "
                         "ON CONFLICT(room_code, round_no, voter_id) DO UPDATE SET target_id=excluded.target_id",
                         (code, room[2], p.telegram_id, p.target_id))
        await db.commit()
    return {"ok": True}

@app.post("/api/rooms/next-phase")
async def next_phase(p: StartGame):
    code = p.code.upper()
    async with aiosqlite.connect(DB_PATH) as db:
        room = await (await db.execute("SELECT host_id, status, phase, round_no FROM rooms WHERE code=?", (code,))).fetchone()
        if not room or room[0] != p.telegram_id:
            raise HTTPException(403, "Faqat xona egasi bosqichni almashtira oladi")
        if room[1] != "playing":
            raise HTTPException(400, "O'yin davom etmayapti")
        if room[2] == "day":
            # Resolve plurality vote and eliminate the target.
            target = await (await db.execute(
                "SELECT target_id, COUNT(*) AS n FROM votes WHERE room_code=? AND round_no=? "
                "GROUP BY target_id ORDER BY n DESC LIMIT 1", (code, room[3]))).fetchone()
            if target:
                await db.execute("UPDATE room_players SET alive=0 WHERE room_code=? AND telegram_id=?",
                                 (code, target[0]))
            await db.execute("UPDATE rooms SET phase='night', round_no=round_no+1 WHERE code=?", (code,))
        else:
            # MVP: switch to day; night actions are not yet automated.
            await db.execute("UPDATE rooms SET phase='day' WHERE code=?", (code,))
        await db.commit()
    return {"ok": True}

@app.get("/api/profile/{telegram_id}")
async def profile(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        row = await (await db.execute("SELECT username, games, wins, xp FROM players WHERE telegram_id=?",
                                      (telegram_id,))).fetchone()
    if not row:
        return {"username": "O'yinchi", "games": 0, "wins": 0, "xp": 0}
    return {"username": row[0], "games": row[1], "wins": row[2], "xp": row[3]}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=False)
