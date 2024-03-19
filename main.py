from os import getenv
import logging

from fastapi import FastAPI
from pydantic import BaseModel

from requests import post

import psycopg


class Activity(BaseModel):
    username: str
    show: str
    season: int
    episode: int


app = FastAPI()

conn = psycopg.connect(
    host=getenv("DB_HOST"),
    dbname=getenv("DB_DB"),
    user=getenv("DB_USER"),
    password=getenv("DB_PASS"),
)


@app.post("/activity")
def activity(activity: Activity):
    """
    Log a users activity
    """

    season = str(activity.season).zfill(2)
    episode = str(activity.episode).zfill(2)

    position = log_activity(activity.username, season, episode)

    if position == 1:
        message = f"{activity.username} is watching S{season}E{episode} first! 🥇"
    elif position == 2:
        message = f"{activity.username} is watching S{season}E{episode}! 🥈"
    elif position == 3:
        message = f"{activity.username} is watching S{season}E{episode}! 🥉"
    elif position == 4:
        message = f"{activity.username} is finally watching S{season}E{episode}! We no longer need spoiler tags."

    resp = post(
        f"{getenv('SIGNAL_API')}/v2/send",
        json={
            "message": message,
            "number": getenv("SIGNAL_FROM"),
            "recipients": [getenv("SIGNAL_TO")],
        },
    )

    if resp.status_code >= 400:
        logging.error(resp.text)
    else:
        logging.info(resp.text)

    return position


def log_activity(username: str, season: int, episode: int) -> int:
    """
    Store activity in the database
    """

    cur = conn.cursor()

    select = """SELECT id FROM survivorLog WHERE season = %s AND episode = %s;"""

    cur.execute(select, (season, episode))
    position = len(cur.fetchall()) + 1

    insert = """INSERT INTO survivorLog(username, season, episode, timestamp)
            VALUES(%s, %s, %s, current_timestamp)
            RETURNING id;"""

    cur.execute(insert, (username, season, episode))
    result = cur.fetchone()[0]

    if result:
        logging.info(f"stored: {result}")
        conn.commit()

    cur.close()

    return position
