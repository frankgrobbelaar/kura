# What Kura ships beside its code

Upscaling needs two things that aren't code, and English subtitles a third. All three ship inside
Kura (the engine bundle), so nothing is downloaded for them, and each keeps its licence, which goes
into `THIRD-PARTY-NOTICES.txt` (`engine/tools/third_party_notices.py`). Whisper, the speech model
the subtitles need, is too big to ship: it's a download (`engine/src/kura/downloads.json`).

| File | What it is | Licence | SHA-256 |
| --- | --- | --- | --- |
| `realesr-animevideov3.onnx` | Real-ESRGAN's anime video model (v0.2.5.0) for SD sources, in full precision, as an ONNX graph that takes and gives ffmpeg's planar float RGB | BSD-3-Clause, Xintao Wang (`realesr-animevideov3.LICENSE.txt`) | `f4f5d8d79bd11b7a7c2069372201258e1b0ad522831ed8ebf2ca797513d2021c` |
| `anime4k-mode-a-hq.glsl` | Anime4K v4.0's "Mode A (HQ)": its six shaders one after another, for 720p sources | MIT, bloc97 (`anime4k.LICENSE.txt`) | `75441f0a5f422d11a4903311c6597d9e517a394489b1dffa280fa9d7d1bc2795` |
| `pyannote-segmentation-3.0.onnx` | pyannote's speaker segmentation model 3.0, as onnx-community converted it: who speaks when, 10 s at a time, which Kura uses to find speech for English subtitles | MIT, as its model card says; the text is pyannote.audio's, CNRS (`pyannote-segmentation-3.0.LICENSE.txt`) | `057ee564753071c0b09b5b611648b50ac188d50846bff5f01e9f7bbf1591ea25` |

How they were made:

- The model: `uv run --with torch --with onnx python tools/export_model.py realesr-animevideov3.pth`
  (PyTorch 2.14.1, onnx 1.23.2) from Real-ESRGAN's release v0.2.5.0. The graph turns ffmpeg's
  G, B, R planes into R, G, B, runs the model (4x), halves the result with a box filter (720x540
  becomes 1440x1080) and hands back G, B, R planes; width and height are free. Exporting again
  gives the same model (identical output), though the file's bytes can differ.
- The shader: `uv run python tools/build_shaders.py Anime4K_v4.0.zip` from Anime4K's release v4.0
  (its newest, v4.0.1, carries the same zip).
- The voice detector: `onnx/model.onnx` from
  [onnx-community/pyannote-segmentation-3.0](https://huggingface.co/onnx-community/pyannote-segmentation-3.0)
  at commit `733a93b6473d019a773298e08cefa686894b1854`, as it is.

Why the model and the shader: the upscaling test on the owner's GTX 1660 Super (2026-10-11, see
[docs/stack/upscaling.md](../../../../docs/stack/upscaling.md)). Why the voice detector: it hears
voices over music, where Silero's missed whole scenes (2026-10-15, see
[docs/stack/speech.md](../../../../docs/stack/speech.md)).
