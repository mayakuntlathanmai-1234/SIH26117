import { useEffect, useRef } from 'react'
import { Renderer, Program, Mesh, Triangle } from 'ogl'
import './GradientWaves.css'

const hexToRgb = (hex) => {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)

  if (!result) {
    return [1, 1, 1]
  }

  return [
    parseInt(result[1], 16) / 255,
    parseInt(result[2], 16) / 255,
    parseInt(result[3], 16) / 255,
  ]
}

const detailToSteps = (detail) => {
  if (detail === 'low') return 40.0
  if (detail === 'high') return 110.0
  return 70.0
}

const vertex = `#version 300 es

in vec2 position;

void main() {
  gl_Position = vec4(position, 0.0, 1.0);
}
`

const fragment = `#version 300 es

precision highp float;

uniform vec2 iResolution;
uniform float iTime;

uniform float uSpeed;
uniform float uAmplitude;
uniform float uWaveScale;
uniform float uWaveRatio;
uniform float uSwell;
uniform float uTurbulence;
uniform float uTilt;
uniform float uZoom;
uniform float uHeight;
uniform float uFogDepth;
uniform float uSteps;
uniform float uBrightness;
uniform float uOpacity;
uniform float uGrain;
uniform float uGrainIntensity;

uniform vec2 uMouse;
uniform float uParallax;
uniform bool uEnableMouse;

uniform vec3 uHorizonColor;
uniform vec3 uWaveColor;
uniform vec3 uCrestColor;

out vec4 fragColor;

const float MAX_DIST = 20000.0;

float hash21(vec2 p) {
  vec3 p3 = fract(vec3(p.xyx) * 0.1031);

  p3 += dot(
    p3,
    p3.yzx + 33.33
  );

  return fract(
    (p3.x + p3.y) * p3.z
  );
}

float plasma(
  vec3 r,
  vec2 freq,
  vec4 tc
) {
  float mx = r.x + tc.x;

  mx += uSwell *
    sin(
      (r.y + mx) / 20.0 + tc.y
    );

  float my = r.y - tc.z;

  my += uTurbulence *
    cos(
      r.x / 23.0 + tc.w
    );

  return r.z -
    (
      sin(mx * freq.x) * uAmplitude +
      sin(my * freq.y) * uAmplitude +
      uHeight
    );
}

float raymarch(
  vec3 pos,
  vec3 dir,
  vec2 freq,
  vec4 tc
) {
  float dist = 0.0;

  for (int i = 0; i < 128; i++) {

    if (float(i) >= uSteps) {
      break;
    }

    float dscene =
      plasma(
        pos + dist * dir,
        freq,
        tc
      );

    if (abs(dscene) < 0.1) {
      break;
    }

    dist += 0.9 * dscene;

    if (!(abs(dist) < MAX_DIST)) {
      return MAX_DIST;
    }
  }

  return dist;
}

void main() {

  float T = iTime * uSpeed;

  vec2 freq = vec2(
    uWaveScale / 7.0,
    (uWaveScale * uWaveRatio) / 3.0
  );

  vec4 tc = vec4(
    T / 0.130,
    T / 0.810,
    T / 0.200,
    T / 0.710
  );

  float c;
  float s;

  float vfov =
    (3.14159 / 2.3) /
    max(uZoom, 0.05);

  vec3 cam =
    vec3(0.0, 0.0, 30.0);

  vec2 uv =
    (gl_FragCoord.xy / iResolution.xy)
    - 0.5;

  uv.x *=
    iResolution.x /
    iResolution.y;

  uv.y *= -1.0;

  vec3 dir =
    vec3(0.0, 0.0, -1.0);

  float ulen =
    length(uv);

  float xrot =
    vfov * ulen;

  c = cos(xrot);
  s = sin(xrot);

  dir =
    mat3(
      1.0, 0.0, 0.0,
      0.0, c, -s,
      0.0, s, c
    ) * dir;

  vec2 nuv =
    ulen > 1e-5
      ? uv / ulen
      : vec2(1.0, 0.0);

  c = nuv.x;
  s = nuv.y;

  dir =
    mat3(
      c, -s, 0.0,
      s, c, 0.0,
      0.0, 0.0, 1.0
    ) * dir;

  c = cos(uTilt);
  s = sin(uTilt);

  dir =
    mat3(
      c, 0.0, s,
      0.0, 1.0, 0.0,
      -s, 0.0, c
    ) * dir;

  if (uEnableMouse) {

    float yaw =
      (uMouse.x - 0.5) *
      uParallax *
      0.4;

    float pitch =
      (uMouse.y - 0.5) *
      uParallax *
      0.4;

    c = cos(yaw);
    s = sin(yaw);

    dir =
      mat3(
        c, 0.0, s,
        0.0, 1.0, 0.0,
        -s, 0.0, c
      ) * dir;

    c = cos(pitch);
    s = sin(pitch);

    dir =
      mat3(
        1.0, 0.0, 0.0,
        0.0, c, -s,
        0.0, s, c
      ) * dir;
  }

  float dist =
    raymarch(
      cam,
      dir,
      freq,
      tc
    );

  vec3 pos =
    cam + dist * dir;

  float t =
    clamp(
      uFogDepth /
      max(dist, 0.001),
      0.0,
      1.0
    );

  vec3 body =
    mix(
      uWaveColor,
      uCrestColor,
      clamp(
        pos.z * 0.08 + 0.5,
        0.0,
        1.0
      )
    );

  vec3 col =
    mix(
      uHorizonColor,
      body,
      t
    );

  col *= uBrightness;

  col =
    clamp(
      col,
      0.0,
      1.0
    );

  float alpha =
    clamp(t, 0.0, 1.0) *
    uOpacity;

  if (uGrain > 0.5) {

    float g =
      hash21(
        gl_FragCoord.xy +
        mod(iTime, 64.0) * 11.0
      );

    alpha +=
      (g - 0.5) *
      uGrainIntensity;
  }

  alpha =
    clamp(
      alpha,
      0.0,
      1.0
    );

  fragColor =
    vec4(
      col * alpha,
      alpha
    );
}
`

const ctxMap = new WeakMap()

function GradientWaves({
  horizonColor = '#f0eef7',
  waveColor = '#f1e5f1',
  crestColor = '#FFFFFF',

  speed = 0.4,
  amplitude = 2.5,
  waveScale = 0.6,
  waveRatio = 0.9,

  swell = 35,
  turbulence = 20,

  tilt = 1.11,
  zoom = 1.0,

  height = 5.5,
  fogDepth = 15,

  detail = 'medium',

  brightness = 1.0,
  opacity = 1.0,

  mouseInteraction = true,
  parallaxStrength = 0.5,

  grain = true,
  grainIntensity = 0.05,

  className = '',
}) {

  const containerRef =
    useRef(null)

  const enableMouseRef =
    useRef(mouseInteraction)

  useEffect(() => {

    const container =
      containerRef.current

    if (!container) {
      return
    }

    const renderer =
      new Renderer({
        webgl: 2,
        alpha: true,
        premultipliedAlpha: true,
        antialias: false,
        dpr: Math.min(
          window.devicePixelRatio || 1,
          2
        ),
      })

    const gl =
      renderer.gl

    gl.clearColor(
      0,
      0,
      0,
      0
    )

    const canvas =
      gl.canvas

    canvas.style.width =
      '100%'

    canvas.style.height =
      '100%'

    canvas.style.display =
      'block'

    container.appendChild(canvas)

    const geometry =
      new Triangle(gl)

    const program =
      new Program(gl, {

        vertex,
        fragment,

        uniforms: {

          iTime: {
            value: 0,
          },

          iResolution: {
            value:
              new Float32Array([
                1,
                1,
              ]),
          },

          uSpeed: {
            value: 0.4,
          },

          uAmplitude: {
            value: 2.5,
          },

          uWaveScale: {
            value: 0.6,
          },

          uWaveRatio: {
            value: 0.9,
          },

          uSwell: {
            value: 35,
          },

          uTurbulence: {
            value: 20,
          },

          uTilt: {
            value: 1.11,
          },

          uZoom: {
            value: 1.0,
          },

          uHeight: {
            value: 5.5,
          },

          uFogDepth: {
            value: 15,
          },

          uSteps: {
            value: 70.0,
          },

          uBrightness: {
            value: 1.0,
          },

          uOpacity: {
            value: 1.0,
          },

          uGrain: {
            value: 1.0,
          },

          uGrainIntensity: {
            value: 0.05,
          },

          uMouse: {
            value:
              new Float32Array([
                0.5,
                0.5,
              ]),
          },

          uParallax: {
            value: 0.5,
          },

          uEnableMouse: {
            value: true,
          },

          uHorizonColor: {
            value:
              new Float32Array([
                1,
                1,
                1,
              ]),
          },

          uWaveColor: {
            value:
              new Float32Array([
                1,
                1,
                1,
              ]),
          },

          uCrestColor: {
            value:
              new Float32Array([
                1,
                1,
                1,
              ]),
          },
        },
      })

    const mesh =
      new Mesh(gl, {
        geometry,
        program,
      })

    ctxMap.set(
      container,
      {
        renderer,
        program,
        mesh,
      }
    )

    const setSize = () => {

      const rect =
        container.getBoundingClientRect()

      const width =
        Math.max(
          1,
          Math.floor(rect.width)
        )

      const height =
        Math.max(
          1,
          Math.floor(rect.height)
        )

      renderer.setSize(
        width,
        height
      )

      const res =
        program.uniforms
          .iResolution.value

      res[0] =
        gl.drawingBufferWidth

      res[1] =
        gl.drawingBufferHeight

      renderer.render({
        scene: mesh,
      })
    }

    const resizeObserver =
      new ResizeObserver(
        setSize
      )

    resizeObserver.observe(
      container
    )

    setSize()

    const currentMouse =
      [0.5, 0.5]

    const targetMouse =
      [0.5, 0.5]

    const onPointerMove =
      (event) => {

        const rect =
          canvas.getBoundingClientRect()

        targetMouse[0] =
          (
            event.clientX -
            rect.left
          ) / rect.width

        targetMouse[1] =
          1.0 -
          (
            event.clientY -
            rect.top
          ) / rect.height
      }

    const onPointerLeave =
      () => {

        targetMouse[0] =
          0.5

        targetMouse[1] =
          0.5
      }

    canvas.addEventListener(
      'pointermove',
      onPointerMove
    )

    canvas.addEventListener(
      'pointerleave',
      onPointerLeave
    )

    let animationFrame = 0

    let isVisible = true

    let isPageVisible =
      !document.hidden

    const startTime =
      performance.now()

    const loop =
      (time) => {

        program.uniforms
          .iTime.value =
          (time - startTime) *
          0.001

        const targetX =
          enableMouseRef.current
            ? targetMouse[0]
            : 0.5

        const targetY =
          enableMouseRef.current
            ? targetMouse[1]
            : 0.5

        currentMouse[0] +=
          0.05 *
          (
            targetX -
            currentMouse[0]
          )

        currentMouse[1] +=
          0.05 *
          (
            targetY -
            currentMouse[1]
          )

        program.uniforms
          .uMouse.value[0] =
          currentMouse[0]

        program.uniforms
          .uMouse.value[1] =
          currentMouse[1]

        renderer.render({
          scene: mesh,
        })

        animationFrame =
          requestAnimationFrame(
            loop
          )
      }

    const start =
      () => {

        if (
          isVisible &&
          isPageVisible &&
          animationFrame === 0
        ) {

          animationFrame =
            requestAnimationFrame(
              loop
            )
        }
      }

    const stop =
      () => {

        if (animationFrame !== 0) {

          cancelAnimationFrame(
            animationFrame
          )

          animationFrame = 0
        }
      }

    const intersectionObserver =
      new IntersectionObserver(
        ([entry]) => {

          isVisible =
            entry.isIntersecting

          if (isVisible) {
            start()
          } else {
            stop()
          }
        },
        {
          threshold: 0,
        }
      )

    intersectionObserver.observe(
      container
    )

    const onVisibilityChange =
      () => {

        isPageVisible =
          !document.hidden

        if (isPageVisible) {
          start()
        } else {
          stop()
        }
      }

    document.addEventListener(
      'visibilitychange',
      onVisibilityChange
    )

    start()

    return () => {

      stop()

      resizeObserver.disconnect()

      intersectionObserver.disconnect()

      document.removeEventListener(
        'visibilitychange',
        onVisibilityChange
      )

      canvas.removeEventListener(
        'pointermove',
        onPointerMove
      )

      canvas.removeEventListener(
        'pointerleave',
        onPointerLeave
      )

      ctxMap.delete(
        container
      )

      try {
        container.removeChild(
          canvas
        )
      } catch {}

      gl
        .getExtension(
          'WEBGL_lose_context'
        )
        ?.loseContext()
    }

  }, [])

  useEffect(() => {

    const container =
      containerRef.current

    if (!container) {
      return
    }

    const context =
      ctxMap.get(container)

    if (!context) {
      return
    }

    const { program } =
      context

    const uniforms =
      program.uniforms

    enableMouseRef.current =
      mouseInteraction

    uniforms.uSpeed.value =
      speed

    uniforms.uAmplitude.value =
      amplitude

    uniforms.uWaveScale.value =
      waveScale

    uniforms.uWaveRatio.value =
      waveRatio

    uniforms.uSwell.value =
      swell

    uniforms.uTurbulence.value =
      turbulence

    uniforms.uTilt.value =
      tilt

    uniforms.uZoom.value =
      zoom

    uniforms.uHeight.value =
      height

    uniforms.uFogDepth.value =
      fogDepth

    uniforms.uSteps.value =
      detailToSteps(detail)

    uniforms.uBrightness.value =
      brightness

    uniforms.uOpacity.value =
      opacity

    uniforms.uGrain.value =
      grain ? 1.0 : 0.0

    uniforms.uGrainIntensity.value =
      grainIntensity

    uniforms.uParallax.value =
      parallaxStrength

    uniforms.uEnableMouse.value =
      mouseInteraction

    const horizon =
      hexToRgb(horizonColor)

    const wave =
      hexToRgb(waveColor)

    const crest =
      hexToRgb(crestColor)

    uniforms.uHorizonColor.value[0] =
      horizon[0]

    uniforms.uHorizonColor.value[1] =
      horizon[1]

    uniforms.uHorizonColor.value[2] =
      horizon[2]

    uniforms.uWaveColor.value[0] =
      wave[0]

    uniforms.uWaveColor.value[1] =
      wave[1]

    uniforms.uWaveColor.value[2] =
      wave[2]

    uniforms.uCrestColor.value[0] =
      crest[0]

    uniforms.uCrestColor.value[1] =
      crest[1]

    uniforms.uCrestColor.value[2] =
      crest[2]

  }, [
    horizonColor,
    waveColor,
    crestColor,
    speed,
    amplitude,
    waveScale,
    waveRatio,
    swell,
    turbulence,
    tilt,
    zoom,
    height,
    fogDepth,
    detail,
    brightness,
    opacity,
    grain,
    grainIntensity,
    mouseInteraction,
    parallaxStrength,
  ])

  return (
    <div
      ref={containerRef}
      className={
        `gradient-waves-container ${className}`.trim()
      }
    />
  )
}

export default GradientWaves