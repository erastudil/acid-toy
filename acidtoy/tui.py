from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Click
from textual.widgets import Button, Footer, Static

from acidtoy.grid import ascii_track
from acidtoy.live import LiveEngine
from acidtoy.viz import PRESETS
from acidtoy.viz_gl import VizWindow


class VolBar(Static):
    def on_click(self, event: Click) -> None:
        w = max(self.size.width, 1)
        self.app.set_volume(event.x / w)


class AcidTui(App):
    CSS = """
    Screen { background: #000000; color: #ffffff; }
    Footer { background: #000000; color: #8b5cf6; }
    #player {
        width: 100%;
        height: 1fr;
        align: center middle;
        background: #000000;
    }
    #dock {
        width: 52;
        height: auto;
        align: center middle;
    }
    #title {
        width: 100%;
        height: 3;
        color: #8b5cf6;
        text-align: center;
        content-align: center middle;
    }
    #controls {
        width: 100%;
        height: 5;
        align: center middle;
    }
    #controls Button {
        width: 12;
        margin: 0 1;
        background: #000000;
        color: #ffffff;
        border: solid #8b5cf6;
    }
    #controls Button:hover {
        background: #8b5cf6;
        color: #000000;
    }
    #vol {
        width: 32;
        height: 3;
        content-align: center middle;
        color: #8b5cf6;
        border: solid #8b5cf6;
        margin: 1 0;
    }
    #meta {
        width: 100%;
        height: 3;
        color: #ffffff;
        text-align: center;
        content-align: center middle;
    }
    #grid {
        width: 100%;
        height: 8;
        color: #ffffff;
        text-align: center;
        overflow: hidden;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("space", "toggle", "play"),
        Binding("n", "skip", "skip"),
        Binding("s", "skip", "skip", show=False),
        Binding("v", "full", "viz"),
        Binding("f", "full", "viz", show=False),
        Binding("escape", "exit_full", "close viz", show=False),
        Binding("[", "vol_down", "vol-", show=False),
        Binding("]", "vol_up", "vol+", show=False),
        Binding("1", "preset_0", "toxic", show=False),
        Binding("2", "preset_1", "tunnel", show=False),
        Binding("3", "preset_2", "julia", show=False),
        Binding("4", "preset_3", "waste", show=False),
        Binding("5", "preset_4", "grid", show=False),
        Binding("p", "cycle_preset", "preset"),
        Binding("q", "quit", "quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.engine = LiveEngine()
        self.preset_i = 0
        self._viz: VizWindow | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="player"):
            with Vertical(id="dock"):
                yield Static("acid-toy", id="title")
                with Horizontal(id="controls"):
                    yield Button("play", id="play")
                    yield Button("skip", id="skip")
                    yield Button("viz", id="vizbtn")
                yield VolBar("", id="vol")
                yield Static("", id="meta")
                yield Static("", id="grid")
        yield Footer()

    def on_mount(self) -> None:
        self.engine.load(1)
        self._paint_vol()
        self._paint_grid()
        self._paint_meta()
        self.set_interval(1 / 30, self._tick)
        self.query_one("#play").focus()

    def on_unmount(self) -> None:
        if self._viz is not None:
            self._viz.close()
            self._viz = None
        self.engine.close()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "play":
            self.action_toggle()
        elif event.button.id == "skip":
            self.action_skip()
        elif event.button.id == "vizbtn":
            self.action_full()

    def set_volume(self, v: float) -> None:
        self.engine.set_volume(v)
        self._paint_vol()

    def action_toggle(self) -> None:
        self.engine.toggle()
        b = self.query_one("#play", Button)
        b.label = "stop" if self.engine.playing else "play"
        self._paint_meta()

    def action_skip(self) -> None:
        self.engine.skip()
        self._paint_grid()
        self._paint_meta()

    def action_full(self) -> None:
        if self._viz is not None and self._viz.alive:
            self._viz.close()
            self._viz = None
            self._paint_meta()
            return
        viz = VizWindow(self.engine)
        err = viz.start()
        if err:
            self.query_one("#meta", Static).update(err)
            return
        self._viz = viz
        self._paint_meta()

    def action_exit_full(self) -> None:
        if self._viz is not None:
            self._viz.close()
            self._viz = None
            self._paint_meta()

    def action_vol_up(self) -> None:
        self.set_volume(self.engine.volume + 0.07)

    def action_vol_down(self) -> None:
        self.set_volume(self.engine.volume - 0.07)

    def action_cycle_preset(self) -> None:
        self.preset_i = (self.preset_i + 1) % len(PRESETS)
        self.engine.preset = PRESETS[self.preset_i]
        self._paint_meta()

    def action_preset_0(self) -> None:
        self._set_preset(0)

    def action_preset_1(self) -> None:
        self._set_preset(1)

    def action_preset_2(self) -> None:
        self._set_preset(2)

    def action_preset_3(self) -> None:
        self._set_preset(3)

    def action_preset_4(self) -> None:
        self._set_preset(4)

    def _set_preset(self, i: int) -> None:
        self.preset_i = i
        self.engine.preset = PRESETS[i]
        self._paint_meta()

    def _tick(self) -> None:
        self.engine.feed_phrases()
        if self._viz is not None and not self._viz.alive:
            err = self._viz.error
            self._viz = None
            if err:
                self.query_one("#meta", Static).update(err)
                return
        self._paint_meta()
        if self.engine.meter.step == 0:
            self._paint_grid()

    def _paint_vol(self) -> None:
        v = self.engine.volume
        n = 14
        filled = int(v * n + 0.5)
        bar = "█" * filled + "░" * (n - filled)
        self.query_one("#vol", VolBar).update(f"vol  {bar}")

    def _paint_meta(self) -> None:
        m = self.engine.meter
        t = self.engine.track
        key = ""
        if t is not None:
            from acidtoy.packs.hard_acid.dna import KEY_NAMES

            key = KEY_NAMES.get(t.key_root, "")
        preset = PRESETS[self.preset_i]
        self.query_one("#meta", Static).update(
            f"seed {m.seed}   {m.bpm} bpm   {key}   {m.phrase}"
            + (f"   {preset}" if self._viz is not None else "")
        )

    def _paint_grid(self) -> None:
        t = self.engine.track
        if t is None:
            return
        self.query_one("#grid", Static).update(ascii_track(t))


def run() -> int:
    AcidTui().run()
    return 0
