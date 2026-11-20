from database.connection import connect
from database.models import SCHEMA


def initialize(path=None, seed=True):
    with connect(path) as db:
        db.executescript(SCHEMA)
        if seed and not db.execute("SELECT 1 FROM metadata WHERE key='seeded'").fetchone():
            db.execute("INSERT INTO metadata VALUES ('seeded','1')")
            cursor = db.execute("INSERT INTO posts(topic,display_name,title,content,session_id,is_demo) VALUES (?,?,?,?,?,1)",
                               ("risa-hontiveros", "Alyssa Reyes", "How do I read a legislative record?",
                                "I’m reviewing Risa Hontiveros’s record. How do I distinguish authored bills from sponsored measures?",
                                "demo"))
            db.execute("INSERT INTO comments(post_id,display_name,content,session_id) VALUES (?,?,?,?)",
                       (cursor.lastrowid, "Miguel Torres", "Check the bill status and the linked Senate journal before drawing a conclusion.", "demo"))
            db.execute("INSERT INTO posts(topic,display_name,title,content,session_id,is_demo) VALUES (?,?,?,?,?,1)",
                       ("risa-hontiveros", "Miguel Torres", "Start with the original document",
                        "A helpful starting point: read the bill text and its legislative history together. A title alone doesn’t explain a measure.", "demo"))
            db.execute("INSERT INTO posts(topic,display_name,title,content,session_id,is_demo) VALUES (?,?,?,?,?,1)",
                       ("general", "Community desk", "Welcome to a space for civic curiosity",
                        "What would you like to understand about the legislative process? Share a question and distinguish evidence from opinion.", "demo"))
        # Give the two illustrative discussions distinct dates in the reference order.
        # Only bundled demo records are adjusted, once; guest content is untouched.
        if seed and not db.execute("SELECT 1 FROM metadata WHERE key='demo_chronology_v2'").fetchone():
            for name, title, age in [("Alyssa Reyes", "How do I read a legislative record?", "-12 minutes"),
                                     ("Miguel Torres", "Start with the original document", "-38 minutes")]:
                db.execute("UPDATE posts SET created_at=strftime('%Y-%m-%dT%H:%M:%fZ','now',?) "
                           "WHERE is_demo=1 AND session_id='demo' AND display_name=? AND title=?", (age, name, title))
            db.execute("INSERT INTO metadata VALUES ('demo_chronology_v2','1')")
