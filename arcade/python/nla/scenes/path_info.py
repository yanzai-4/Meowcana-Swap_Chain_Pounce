"""C on a Night Path node: a full-screen page that shows what waits there.

    NodeInfo(node)          modal Overlay (B or C closes). Rats and Chubbs show their portrait sprite, HP and the scrap
                            cards they will lay down; every other node shows its icon and a few plain facts.

Painted progressively like the other Path screens: the ground in fast bands, then one element per step while the frame
stays inside the busy budget.
"""

from nla import story
from nla.rules import cards
from nla.rules import enemies
from nla.ui import theme as T
from nla.ui import widgets as W

from .path_common import node_text, wrap

NODE_FRAME = {"fight": 0, "elite": 1, "stall": 2, "encounter": 3, "bed": 4, "box": 5, "boss": 6}
FACTS = {
    "stall": ["Buy cards, services and Tuna Cans with Treats.", "Sell cards for half price. Reroll for fresh stock.",
              "Leaving is final: you cannot come back."],
    "encounter": ["You pick one of two options.", "Press C on an option to read more.", "Some are safe. Some are a gamble."],
    "bed": ["Nap: heal 30% of your max HP.", "Sharpen: one card gets +1 Star.", "Groom: wash off a Curse, or flip a card."],
    "box": ["One card is hiding inside.", "It could be a Major. If your Box is full, you swap one out."],
}
BUDGET_MS = 58


class NodeInfo(W.Overlay):
    def __init__(self, node):
        super().__init__()
        self.node = node
        self.full_screen = True
        self.rect = (0, 0, T.SCREEN_W, T.SCREEN_H)
        self._steps = None
        self._i = 0
        self._y = 0
        self.busy = True

    def update(self, ctl, dt):
        if ctl.b or ctl.c or ctl.a:
            self.close()

    # ------------------------------------------------------------------ plan
    def _plan(self, scr):
        node = self.node
        title, tag, desc = node_text(node)
        enemy = enemies.ENEMIES.get(node.key) if node.kind in ("fight", "elite", "boss") else None
        steps = []

        def text(x, y, msg, color, font=T.BODY):
            """One text step; its estimate comes from the cell it paints (slow pixels)."""
            msg = W.glyphs(msg)
            w, h = scr.measure(msg, font)
            steps.append((4 + w * h / 180.0, lambda s: s.text(x, y, msg, color, T.GROUND, font)))

        def frame(s):
            s.rect(2, 2, T.SCREEN_W - 4, T.SCREEN_H - 4, T.RULE_DIM)
            W.corners(s, 2, 2, T.SCREEN_W - 4, T.SCREEN_H - 4)
        steps.append((12, frame))
        text(120, 22, title, T.LABEL, T.TITLE)
        sub = tag or ("Chapter 1 boss" if node.kind == "boss" else "Night Path")
        if enemy is not None:
            sub += "  {.}  HP %d" % enemy.hp
        text(120, 52, sub, T.ACCENT)
        for k, line in enumerate(desc):
            text(120, 74 + 16 * k, line, T.TEXT)

        def plate(s):
            s.rect(22, 22, 84, 84, T.RULE)
            s.fill_rect(23, 23, 82, 41, T.NIGHT0)
        steps.append((44, plate))

        def plate2(s):
            s.fill_rect(23, 64, 82, 41, T.NIGHT0)
        steps.append((44, plate2))

        def art(s):
            if enemy is not None:
                a = T.asset(node.key + "_idle")
                if a.h <= 80:
                    s.blit(a, 0, 64 - a.w // 2, 105 - a.h)
                else:                                   # Chubbs is bigger than the plate: show his upper body
                    s.asset_region(a, 0, 23, 23, (a.w - 82) // 2, a.h - 82, 82, 82)
            else:
                s.blit(T.asset("ui_node"), NODE_FRAME[node.kind], 64 - 30, 64 - 30, scale=3)
        steps.append((30 if enemy is not None else 20, art))
        steps.append((4, lambda s: W.divider(s, T.INNER_L, T.INNER_R, 118)))

        if enemy is not None:
            intro = story.ENEMY_TEXT[node.key].intro if node.key in story.ENEMY_TEXT else ""
            text(T.INNER_L, 128, "Its cards, played left to right", T.MUTED)
            n = len(enemy.spread)
            pitch = min(48, (T.INNER_W - 8) // max(1, n))
            x0 = T.INNER_L + 4
            for i, c in enumerate(enemy.spread):
                def paint(s, i=i, c=c):
                    v = W.CardView(x0 + i * pitch, 148, small=True)
                    v.set_enemy_card(c)
                    v.draw(s, True)
                steps.append((22, paint))
            names = []
            for c in enemy.spread:
                t = cards.enemy_card_title(c)
                if t not in names:
                    names.append(t)
            for k, line in enumerate(wrap("Plays: " + ", ".join(names), 56)[:2]):
                text(T.INNER_L, 214 + 16 * k, line, T.TEXT)
            if intro:
                text(T.INNER_L, 262, intro, T.MUTED)
        else:
            for k, fact in enumerate(FACTS.get(node.kind, [])):
                text(T.INNER_L + 8, 134 + 22 * k, "{.} " + fact, T.TEXT)
        steps.append((32, lambda s: W.Footer(hints=[("B", "Close")]).draw(s, True)))
        self._steps = steps

    # ------------------------------------------------------------------ paint
    def draw(self, scr, full=False):
        if full:
            self._steps, self._i, self._y = None, 0, 0
            self.busy = True
        if self._y < T.SCREEN_H:
            n = max(1, min(T.SCREEN_H - self._y, 24000 // T.SCREEN_W))
            scr.fill_rect(0, self._y, T.SCREEN_W, n, T.GROUND)
            self._y += n
            return
        if self._steps is None:
            self._plan(scr)
        while self._i < len(self._steps):
            est, fn = self._steps[self._i]
            st = scr.stats()
            if st["ops"] > 0 and st["ms"] + est > BUDGET_MS:
                return
            fn(scr)
            self._i += 1
        self.busy = False
