# acid-toy

GPL-3.0-or-later. hard acid generator. patterns in code. style rules reject the rest.

terminal player. `v` is a milkdrop-class GL window (feedback warp + waveform, ~60fps). not the old terminal julia.

```
pip install -r requirements.txt
python -m acidtoy
```

| key | |
|---|---|
| space | play / stop |
| n | skip — new seed |
| v | viz — fullscreen GL |
| esc | close viz |
| 1-5 | toxic · tunnel · julia · waste · grid |
| p | cycle preset |
| [ ] | volume |
| q | quit |

```
python -m acidtoy generate --seed 7
python -m acidtoy wav --seed 7
```

pack: `acidtoy/packs/hard_acid/`

ear: donit. 150+. toxic. kick owns the floor. 303 screams above it. the LLM does not write notes.

no roland dumps. no sample theft. synthesized drums. 4-pole tanh ladder.

viz needs `pygame-ce` + `PyOpenGL`. the toy still plays without them.
