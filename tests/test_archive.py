import tempfile
import unittest

from arhivach_archive.database import connect, initialise
from arhivach_archive.parser import index_links, parse_thread


class ArchiveTests(unittest.TestCase):
    def test_index_deduplicates_thread_urls(self):
        links = index_links('<a href="/thread/42/">a</a><a href="/thread/42/">b</a>', "https://arhivach.vc/index/")
        self.assertEqual([(item.id, item.url) for item in links], [(42, "https://arhivach.vc/thread/42/")])

    def test_thread_extracts_post_and_images(self):
        html = '''<title>Example</title><span class="taglabel">/g/</span>
        <div class="post"><div class="post_head"><h1 class="post_subject">Subject</h1><span class="poster_name">Anon</span><span class="post_time">today</span><span class="post_num">#1</span></div><div class="post_comment"><img src="/storage/t/a.jpg"><div class="post_comment_body">Hello<br>world</div></div></div>'''
        thread = parse_thread(html, "https://arhivach.vc/thread/1/")
        self.assertEqual(thread.tags, ["/g/"])
        self.assertEqual(thread.posts[0].body_text, "Hello world")
        self.assertEqual(thread.posts[0].images[0][0], "https://arhivach.vc/storage/t/a.jpg")

    def test_fts_index_removes_deleted_post(self):
        with tempfile.NamedTemporaryFile() as temporary:
            initialise(temporary.name)
            with connect(temporary.name) as db:
                db.execute("INSERT INTO threads(id,url,title,status) VALUES (1,'u','t','fetched')")
                db.execute("INSERT INTO posts(thread_id,body_html,body_text) VALUES (1,'','needle')")
                self.assertEqual(db.execute("SELECT count(*) FROM posts_fts WHERE posts_fts MATCH 'needle'").fetchone()[0], 1)
                db.execute("DELETE FROM posts")
                self.assertEqual(db.execute("SELECT count(*) FROM posts_fts WHERE posts_fts MATCH 'needle'").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
