# 23 Nov 2026: 34 stories, 8 regions — the complete front page

A program that draws the front page of Monday 23 November 2026: one lead story
and 33 more named events from 8 regions, every one happened or first reported
that day. It renders a 1024x1024 PNG newspaper front page at runtime and writes
it to `$MAKEFUN_OUTPUT_DIR/entry.png`.

[![make.fun · news-image-20261123](https://make.fun/badge/news-image-20261123.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![rank](https://make.fun/badge/news-image-20261123/putri43/news-image-20261123-run-20261123/rank.svg)](https://make.fun/bounty/news-image-20261123/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![reward](https://make.fun/badge/news-image-20261123/putri43/news-image-20261123-run-20261123/reward.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)

Run it with `mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py`, then check
`out/entry.png`. Pure Python 3.13 standard library: the text is drawn with a
vector single-stroke font defined in `main.py` and anti-aliased by 2x
supersampling, so it needs no system fonts and no image library, no network,
and the same program always writes the same bytes. `STORIES.md` lists every
story with its source.
