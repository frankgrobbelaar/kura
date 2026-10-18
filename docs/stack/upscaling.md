# Upscaling (ONNX Runtime, Real-ESRGAN, Anime4K, the encoders)

Every file goes to the library standard (1080p or 720p HEVC 10-bit). How its picture gets there
depends on where it starts, as the owner chose after the upscaling test on 2026-10-11 (the
numbers are in [kura/core/estimate.py](../../engine/src/kura/core/estimate.py)):

| Source | Method | How | On the GTX 1660 Super |
| --- | --- | --- | --- |
| SD (480p, 576p) | Best | Real-ESRGAN's anime video model on the graphics card | about an hour an episode |
| 720p and the like | Fast | Anime4K's "Mode A (HQ)" shaders through ffmpeg's libplacebo | about 10 minutes |
| 1080p, not HEVC 10-bit | Re-encode | ffmpeg alone | about 3 minutes |
| Bigger than 1080p | Re-encode | brought down to 1080p | |

Whatever the method, the card's encoder writes HEVC 10-bit (NVIDIA's NVENC, AMD's AMF or Intel's
Quick Sync, whichever the PC has), and the picture keeps its shape: 4:3 stays 4:3 at 1440x1080,
nothing stretched or cropped. [kura/core/convert.py](../../engine/src/kura/core/convert.py) builds
the ffmpeg commands. On another PC, a way that doesn't run there gives way to the next one down
and a slow one is said to be slow, with that PC's own times: [hardware.md](hardware.md).

## The AI model: ONNX Runtime with DirectML

`onnxruntime-directml` (MIT, Microsoft) runs `realesr-animevideov3.onnx` on the graphics card
through DirectML, which every DirectX 12 card has: no CUDA download (CUDA was no faster here and
adds more than a gigabyte). The model runs in full precision: half precision is slower on GTX 16
cards, which have no tensor cores. The session uses `DmlExecutionProvider` with memory patterns
off and sequential execution (DirectML's requirements), and fixes the free width and height to
the source's (`add_free_dimension_override_by_name`), which DirectML runs faster. DirectML takes
the PC's high-performance card (`performance_preference`: a laptop's card of its own, not the
processor's graphics), and a session ONNX Runtime quietly moved to the processor, as it does when
DirectML can't start, is refused: the model there would take days an episode. In one process
DirectML breaks two ways (`kura/directml.py`): two threads loading or running models at once crash
the graphics driver, so every session is made and run under one lock, a frame or a token at a
time; and a model loaded and let go of while Whisper is loaded crashes Whisper's next step, lock
or no lock. So the queue lets Whisper go before a conversion loads the model, and the model's use
outside the queue, See it first and the PC check, runs in a process of its own (`kura
upscale-frame`, `kura check-model`). ONNX Runtime's
official Windows builds report their use to Microsoft through Windows' diagnostics unless told
not to, so Kura turns that off (`disable_telemetry_events`) before loading the model. The engine
carries Microsoft's C++ runtime, which ONNX Runtime needs (see [pyinstaller.md](pyinstaller.md)),
and `DirectML.dll` comes inside the package; both are Microsoft's redistributable files, listed
apart in the third-party notices.

Frames travel as ffmpeg's planar float RGB (`gbrpf32le`): one ffmpeg decodes the source to raw
frames on its standard output, the model upscales each (4x, then a 2x box downscale built into
the graph, so 720x540 becomes 1440x1080), and a second ffmpeg reads them on its standard input,
scales them to the standard's size and encodes them, taking the sound, subtitles, fonts and
chapters from the source. Decoding, the model and encoding run side by side.

The model file and how it was made: [engine/src/kura/assets/README.md](../../engine/src/kura/assets/README.md).

Checked 2026-10-18: Real-ESRGAN's newest release (v0.3.0) adds only a general model, not one
for anime video, so `realesr-animevideov3` stays; Anime4K's newest release, v4.0.1, carries the
same `Anime4K_v4.0.zip` the shader is built from (SHA-256 `139cd282…`), so it's current too.

## Anime4K through libplacebo

ffmpeg's `libplacebo` filter (in the LGPL build Kura downloads) runs Anime4K's GLSL shaders on
the card through Vulkan: `-init_hw_device vulkan=vk -filter_hw_device vk` and
`hwupload,libplacebo=w=1920:h=1080:format=p010le:custom_shader_path=…,hwdownload`. The shader
is Anime4K v4.0's "Mode A (HQ)", six shaders in one file
(`engine/src/kura/assets/anime4k-mode-a-hq.glsl`, MIT). Its path is written by
`kura/core/filters.py`, escaped for the filter's option and again for the graph
(`C\\:/Users/…`), so a folder with an apostrophe, a comma or brackets in its name reads back
as it is.

## The encoders

`hevc_nvenc`, preset p5, tuned for quality, constant quality 23 with no bitrate cap, spatial
adaptive quantisation, 10-bit (`main10`, `p010le`). At quality 20 the test's episodes came out at
590 to 810 MB; 23 lands near the standard's 450 MB for 24 minutes. Turing cards (GTX 16) encode
HEVC 10-bit but not AV1.

On PCs without NVIDIA's, AMD's `hevc_amf` (transcoding, quality preset, constant QP 22 and 24) or
Intel's `hevc_qsv` (preset slower, global quality 23), both `main10`, make the same standard. The
check of the PC finds which one starts ([hardware.md](hardware.md)); they haven't been measured
against NVENC's sizes on real cards yet.

## Tests

No test needs a graphics card: CI runs on Windows machines without one. The commands are tested
as values, the model's loop with a stand-in for ONNX Runtime, and the real thing runs on the
owner's PC.
