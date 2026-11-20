from database.connection import connect
from database.init_db import initialize
from backend.moderation_service import clean
from backend.senator_service import SenatorService


class CommunityService:
    def __init__(self, path=None, seed=True):
        self.path = path
        self.topics = {s["id"] for s in SenatorService().senators} | {"general"}
        initialize(path, seed)

    def _topic(self, topic):
        if topic not in self.topics:
            raise ValueError("Choose a valid discussion topic.")

    def list_posts(self, topic=None, sort="Latest"):
        if topic:
            self._topic(topic)
        order = "like_count DESC, p.created_at DESC, p.id DESC" if sort == "Popular" else "p.created_at DESC, p.id DESC"
        with connect(self.path) as db:
            return [dict(row) for row in db.execute(
                "SELECT p.*, (SELECT COUNT(*) FROM likes WHERE post_id=p.id) AS like_count, "
                "(SELECT COUNT(*) FROM comments WHERE post_id=p.id) AS comment_count FROM posts p "
                + ("WHERE p.topic=? " if topic else "") + "ORDER BY " + order, (topic,) if topic else ())]

    def create_post(self, topic, name, title, content, session_id):
        self._topic(topic)
        values = (topic, clean(name, "Display name", 60), clean(title, "Title", 150),
                  clean(content, "Post", 5000), session_id)
        with connect(self.path) as db:
            return db.execute("INSERT INTO posts(topic,display_name,title,content,session_id) VALUES (?,?,?,?,?)", values).lastrowid

    def comments(self, post_id):
        with connect(self.path) as db:
            return [dict(row) for row in db.execute("SELECT * FROM comments WHERE post_id=? ORDER BY id", (post_id,))]

    def add_comment(self, post_id, name, content, session_id):
        with connect(self.path) as db:
            self._exists(db, post_id)
            db.execute("INSERT INTO comments(post_id,display_name,content,session_id) VALUES (?,?,?,?)",
                       (post_id, clean(name, "Display name", 60), clean(content, "Reply", 2000), session_id))

    @staticmethod
    def _exists(db, post_id):
        if not db.execute("SELECT 1 FROM posts WHERE id=?", (post_id,)).fetchone():
            raise ValueError("This post no longer exists.")

    def liked(self, post_id, session_id):
        with connect(self.path) as db:
            return bool(db.execute("SELECT 1 FROM likes WHERE post_id=? AND session_id=?", (post_id, session_id)).fetchone())

    def toggle_like(self, post_id, session_id):
        with connect(self.path) as db:
            self._exists(db, post_id)
            deleted = db.execute("DELETE FROM likes WHERE post_id=? AND session_id=?", (post_id, session_id)).rowcount
            if not deleted:
                db.execute("INSERT INTO likes VALUES (?,?)", (post_id, session_id))

    def report(self, post_id, session_id, reason):
        reason = clean(reason, "Report reason", 500)
        with connect(self.path) as db:
            self._exists(db, post_id)
            db.execute("INSERT INTO reports(post_id,session_id,reason) VALUES (?,?,?) "
                       "ON CONFLICT(post_id,session_id) DO UPDATE SET reason=excluded.reason", (post_id, session_id, reason))

    def edit_post(self, post_id, session_id, title, content):
        title, content = clean(title, "Title", 150), clean(content, "Post", 5000)
        with connect(self.path) as db:
            changed = db.execute("UPDATE posts SET title=?,content=? WHERE id=? AND session_id=? AND is_demo=0",
                                 (title, content, post_id, session_id)).rowcount
            if not changed:
                raise ValueError("Only posts created in this guest session can be edited.")

    def delete_post(self, post_id, session_id):
        with connect(self.path) as db:
            if not db.execute("DELETE FROM posts WHERE id=? AND session_id=? AND is_demo=0", (post_id, session_id)).rowcount:
                raise ValueError("Only posts created in this guest session can be deleted.")
