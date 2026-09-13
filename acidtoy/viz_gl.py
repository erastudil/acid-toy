"""milkdrop-class viz. GL feedback warp + waveform. pygame-ce + PyOpenGL."""

from __future__ import annotations

import ctypes
import threading
import time

import numpy as np

from acidtoy.viz import PRESETS

VERT = """
#version 330
in vec2 in_vert;
in vec2 in_uv;
out vec2 v_uv;
void main() {
    v_uv = in_uv;
    gl_Position = vec4(in_vert, 0.0, 1.0);
}
"""

FRAG = """
#version 330
in vec2 v_uv;
out vec4 f_color;
uniform sampler2D prev;
uniform sampler2D wave;
uniform float time;
uniform float bass;
uniform float kick;
uniform float cut;
uniform float drive;
uniform int preset;
uniform vec2 res;

vec2 warp_uv(vec2 uv) {
    vec2 p = uv * 2.0 - 1.0;
    p.x *= res.x / max(res.y, 1.0);
    float z = 0.985 - kick * 0.045 - bass * 0.03;
    float ang = time * 0.07 + cut * 0.55 + float(preset) * 0.4;
    if (preset == 1) ang += time * 0.11;
    if (preset == 2) z -= 0.02;
    float c = cos(ang);
    float s = sin(ang);
    vec2 q = vec2(c * p.x - s * p.y, s * p.x + c * p.y) * z;
    float w = 0.018 + drive * 0.03 + kick * 0.02;
    if (preset == 0) {
        q += w * vec2(sin(q.y * 9.0 + time * 1.4), cos(q.x * 8.0 - time));
    } else if (preset == 1) {
        float r = length(q) + 1e-4;
        q += w * vec2(q.x, q.y) / r * sin(r * 14.0 - time * 2.0);
    } else if (preset == 2) {
        q += w * vec2(sin(time + q.y * 6.0), sin(time * 0.7 + q.x * 6.0));
    } else if (preset == 3) {
        q.y += w * sin(q.x * 12.0 + time * 2.2);
        q.x += w * 0.6 * cos(q.y * 7.0 - time);
    } else {
        q.x += w * sin(q.y * 16.0);
        q.y += w * 0.4 * sin(time * 0.8);
    }
    q.x /= res.x / max(res.y, 1.0);
    return clamp(q * 0.5 + 0.5, 0.002, 0.998);
}

vec3 tint(float v) {
    vec3 violet = vec3(0.35, 0.12, 0.85);
    vec3 toxic = vec3(0.15, 0.95, 0.12);
    vec3 waste = vec3(0.55, 0.95, 0.05);
    vec3 white = vec3(0.95);
    if (preset == 3) return mix(violet, waste, v);
    if (preset == 4) return mix(violet * 0.4, white, v);
    return mix(violet, toxic, v);
}

void main() {
    vec2 uv = warp_uv(v_uv);
    vec3 old = texture(prev, uv).rgb;
    float decay = 0.93 - kick * 0.04;
    vec3 col = old * decay;

    vec2 p = v_uv * 2.0 - 1.0;
    p.x *= res.x / max(res.y, 1.0);
    float r = length(p);
    float ring = smoothstep(0.04, 0.0, abs(r - (0.22 + bass * 0.35)));
    col += tint(cut) * ring * (0.25 + kick * 0.55);

    float wx = clamp(v_uv.x, 0.001, 0.999);
    float samp = texture(wave, vec2(wx, 0.5)).r;
    float wy = 0.5 + samp * (0.22 + drive * 0.12);
    float wave_line = smoothstep(0.012, 0.0, abs(v_uv.y - wy));
    col += vec3(0.85, 0.85, 1.0) * wave_line * (0.35 + kick * 0.4);

    if (preset == 4) {
        float gx = abs(fract(p.x * 8.0) - 0.5);
        float gy = abs(fract((p.y + time * 0.15) * 8.0) - 0.5);
        float grid = smoothstep(0.03, 0.0, min(gx, gy));
        col += vec3(0.55, 0.2, 1.0) * grid * 0.18;
    }
    col += vec3(0.55, 0.15, 1.0) * kick * 0.08;
    f_color = vec4(clamp(col, 0.0, 1.0), 1.0);
}
"""

BLIT_FRAG = """
#version 330
in vec2 v_uv;
out vec4 f_color;
uniform sampler2D src;
void main() {
    f_color = texture(src, v_uv);
}
"""

QUAD = np.array(
    [
        -1.0, -1.0, 0.0, 0.0,
        1.0, -1.0, 1.0, 0.0,
        -1.0, 1.0, 0.0, 1.0,
        1.0, 1.0, 1.0, 1.0,
    ],
    dtype=np.float32,
)


def _compile(gl, src, kind):
    s = gl.glCreateShader(kind)
    gl.glShaderSource(s, src)
    gl.glCompileShader(s)
    ok = gl.glGetShaderiv(s, gl.GL_COMPILE_STATUS)
    if not ok:
        log = gl.glGetShaderInfoLog(s)
        raise RuntimeError(log.decode() if isinstance(log, bytes) else str(log))
    return s


def _program(gl, vs, fs):
    p = gl.glCreateProgram()
    gl.glAttachShader(p, _compile(gl, vs, gl.GL_VERTEX_SHADER))
    gl.glAttachShader(p, _compile(gl, fs, gl.GL_FRAGMENT_SHADER))
    gl.glBindAttribLocation(p, 0, "in_vert")
    gl.glBindAttribLocation(p, 1, "in_uv")
    gl.glLinkProgram(p)
    ok = gl.glGetProgramiv(p, gl.GL_LINK_STATUS)
    if not ok:
        log = gl.glGetProgramInfoLog(p)
        raise RuntimeError(log.decode() if isinstance(log, bytes) else str(log))
    return p


def _tex(gl, w, h, internal, fmt, typ, data=None, filt=None):
    t = gl.glGenTextures(1)
    gl.glBindTexture(gl.GL_TEXTURE_2D, t)
    f = filt if filt is not None else gl.GL_LINEAR
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, f)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, f)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
    gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, internal, w, h, 0, fmt, typ, data)
    return t


def _fbo(gl, tex):
    fb = gl.glGenFramebuffers(1)
    gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, fb)
    gl.glFramebufferTexture2D(
        gl.GL_FRAMEBUFFER, gl.GL_COLOR_ATTACHMENT0, gl.GL_TEXTURE_2D, tex, 0
    )
    st = gl.glCheckFramebufferStatus(gl.GL_FRAMEBUFFER)
    if st != gl.GL_FRAMEBUFFER_COMPLETE:
        raise RuntimeError(f"fbo {st}")
    gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
    return fb


class VizWindow:
    def __init__(self, engine) -> None:
        self.engine = engine
        self.alive = False
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self.error = ""

    def start(self) -> str:
        if self.alive:
            return ""
        try:
            import pygame  # noqa: F401
            from OpenGL import GL  # noqa: F401
        except ImportError:
            self.error = "pip install pygame-ce PyOpenGL"
            return self.error
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="acid-viz", daemon=True)
        self._thread.start()
        return ""

    def close(self) -> None:
        self._stop.set()
        t = self._thread
        if t is not None:
            t.join(timeout=2.0)
        self.alive = False

    def _run(self) -> None:
        try:
            self._loop()
        except Exception as e:
            self.error = str(e)
            self.alive = False

    def _loop(self) -> None:
        import pygame
        from OpenGL import GL as gl

        pygame.init()
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
        pygame.display.gl_set_attribute(
            pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE
        )
        screen = pygame.display.set_mode(
            (0, 0), pygame.OPENGL | pygame.DOUBLEBUF | pygame.FULLSCREEN
        )
        pygame.display.set_caption("acid-toy")
        w, h = screen.get_size()

        prog = _program(gl, VERT, FRAG)
        blit = _program(gl, VERT, BLIT_FRAG)
        loc = {
            "prev": gl.glGetUniformLocation(prog, "prev"),
            "wave": gl.glGetUniformLocation(prog, "wave"),
            "time": gl.glGetUniformLocation(prog, "time"),
            "bass": gl.glGetUniformLocation(prog, "bass"),
            "kick": gl.glGetUniformLocation(prog, "kick"),
            "cut": gl.glGetUniformLocation(prog, "cut"),
            "drive": gl.glGetUniformLocation(prog, "drive"),
            "preset": gl.glGetUniformLocation(prog, "preset"),
            "res": gl.glGetUniformLocation(prog, "res"),
            "src": gl.glGetUniformLocation(blit, "src"),
        }

        vao = gl.glGenVertexArrays(1)
        vbo = gl.glGenBuffers(1)
        gl.glBindVertexArray(vao)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, QUAD.nbytes, QUAD, gl.GL_STATIC_DRAW)
        gl.glEnableVertexAttribArray(0)
        gl.glVertexAttribPointer(0, 2, gl.GL_FLOAT, gl.GL_FALSE, 16, ctypes.c_void_p(0))
        gl.glEnableVertexAttribArray(1)
        gl.glVertexAttribPointer(1, 2, gl.GL_FLOAT, gl.GL_FALSE, 16, ctypes.c_void_p(8))

        tex_a = _tex(gl, w, h, gl.GL_RGBA8, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE)
        tex_b = _tex(gl, w, h, gl.GL_RGBA8, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE)
        fbo_a = _fbo(gl, tex_a)
        fbo_b = _fbo(gl, tex_b)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, fbo_a)
        gl.glClearColor(0, 0, 0, 1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, fbo_b)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)

        wave_tex = _tex(
            gl, 512, 1, gl.GL_R32F, gl.GL_RED, gl.GL_FLOAT, np.zeros(512, dtype=np.float32)
        )

        clock = pygame.time.Clock()
        t0 = time.perf_counter()
        src_tex, dst_tex = tex_a, tex_b
        src_fbo, dst_fbo = fbo_a, fbo_b
        self.alive = True

        while not self._stop.is_set():
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._stop.set()
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        self._stop.set()
                    elif event.key == pygame.K_p:
                        i = (
                            PRESETS.index(self.engine.preset)
                            if self.engine.preset in PRESETS
                            else 0
                        )
                        self.engine.preset = PRESETS[(i + 1) % len(PRESETS)]
                    elif pygame.K_1 <= event.key <= pygame.K_5:
                        self.engine.preset = PRESETS[event.key - pygame.K_1]

            m = self.engine.meter
            preset = self.engine.preset if self.engine.preset in PRESETS else "toxic"
            gl.glBindTexture(gl.GL_TEXTURE_2D, wave_tex)
            gl.glTexSubImage2D(
                gl.GL_TEXTURE_2D,
                0,
                0,
                0,
                512,
                1,
                gl.GL_RED,
                gl.GL_FLOAT,
                np.ascontiguousarray(self.engine.wave, dtype=np.float32),
            )

            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, dst_fbo)
            gl.glViewport(0, 0, w, h)
            gl.glUseProgram(prog)
            gl.glActiveTexture(gl.GL_TEXTURE0)
            gl.glBindTexture(gl.GL_TEXTURE_2D, src_tex)
            gl.glUniform1i(loc["prev"], 0)
            gl.glActiveTexture(gl.GL_TEXTURE1)
            gl.glBindTexture(gl.GL_TEXTURE_2D, wave_tex)
            gl.glUniform1i(loc["wave"], 1)
            gl.glUniform1f(loc["time"], time.perf_counter() - t0)
            gl.glUniform1f(loc["bass"], float(min(m.rms * 6.0, 1.0)))
            gl.glUniform1f(loc["kick"], float(m.kick))
            gl.glUniform1f(loc["cut"], float(m.cutoff))
            gl.glUniform1f(loc["drive"], float(m.drive))
            gl.glUniform1i(loc["preset"], PRESETS.index(preset))
            gl.glUniform2f(loc["res"], float(w), float(h))
            gl.glBindVertexArray(vao)
            gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, 4)

            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
            gl.glViewport(0, 0, w, h)
            gl.glUseProgram(blit)
            gl.glActiveTexture(gl.GL_TEXTURE0)
            gl.glBindTexture(gl.GL_TEXTURE_2D, dst_tex)
            gl.glUniform1i(loc["src"], 0)
            gl.glBindVertexArray(vao)
            gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, 4)
            pygame.display.flip()
            src_tex, dst_tex = dst_tex, src_tex
            src_fbo, dst_fbo = dst_fbo, src_fbo
            clock.tick(60)

        pygame.quit()
        self.alive = False
