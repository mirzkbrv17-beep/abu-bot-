import unittest

from app.services.emoji import EmojiRenderer, valid_custom_id

CID = "5368324170671202286"


class EmojiTests(unittest.TestCase):
    def setUp(self):
        self.r = EmojiRenderer()
        self.r.set_mappings({"❤️": CID})

    def test_replaces_plain_emoji(self):
        out = self.r.render("Salom ❤️")
        self.assertIn(f'<tg-emoji emoji-id="{CID}">', out)

    def test_variation_selector_both_forms(self):
        self.assertIn("tg-emoji", self.r.render("❤"))
        self.assertIn("tg-emoji", self.r.render("❤\ufe0f"))

    def test_does_not_touch_tags_or_existing_custom(self):
        src = f'<a href="x❤">t</a> <tg-emoji emoji-id="1234567">❤</tg-emoji>'
        self.assertEqual(self.r.render(src), src)

    def test_fallback_disabled(self):
        self.assertEqual(self.r.render("❤️", use_custom=False), "❤️")

    def test_no_mappings(self):
        self.assertEqual(EmojiRenderer().render("❤️"), "❤️")

    def test_invalid_ids_ignored(self):
        r = EmojiRenderer()
        r.set_mappings({"❤️": "abc"})
        self.assertEqual(r.render("❤️"), "❤️")

    def test_id_validation(self):
        self.assertTrue(valid_custom_id(CID))
        for bad in ("", "12", "abc123456", "1" * 30, '1"><b>'):
            self.assertFalse(valid_custom_id(bad))

    def test_escaped_text_stays_escaped(self):
        self.assertEqual(self.r.render("&lt;b&gt;"), "&lt;b&gt;")


if __name__ == "__main__":
    unittest.main()
