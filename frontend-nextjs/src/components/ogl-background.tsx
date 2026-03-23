"use client";

import { useEffect, useRef } from "react";
import { Mesh, Program, Renderer, Triangle } from "ogl";

export function OglBackground() {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const renderer = new Renderer({
      alpha: true,
      dpr: Math.min(window.devicePixelRatio, 2),
    });
    const gl = renderer.gl;
    gl.clearColor(0, 0, 0, 0);

    const geometry = new Triangle(gl);
    const uniforms = {
      uTime: { value: 0 },
      uResolution: { value: [window.innerWidth, window.innerHeight] as [number, number] },
    };

    const program = new Program(gl, {
      vertex: `
        attribute vec2 uv;
        attribute vec2 position;
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = vec4(position, 0.0, 1.0);
        }
      `,
      fragment: `
        precision highp float;

        uniform float uTime;
        uniform vec2 uResolution;
        varying vec2 vUv;

        float hash(vec2 p) {
          return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
        }

        float noise(vec2 p) {
          vec2 i = floor(p);
          vec2 f = fract(p);
          vec2 u = f * f * (3.0 - 2.0 * f);
          return mix(
            mix(hash(i + vec2(0.0, 0.0)), hash(i + vec2(1.0, 0.0)), u.x),
            mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x),
            u.y
          );
        }

        void main() {
          vec2 uv = vUv;
          vec2 p = uv * 3.0;
          float t = uTime * 0.12;

          float n = noise(p + vec2(t, -t));
          float wave = sin((uv.x + uv.y + t) * 8.0) * 0.5 + 0.5;
          float glow = smoothstep(0.15, 0.95, n * 0.65 + wave * 0.35);

          vec3 deep = vec3(0.03, 0.06, 0.18);
          vec3 mid = vec3(0.16, 0.10, 0.36);
          vec3 accent = vec3(0.17, 0.46, 0.86);

          vec3 color = mix(deep, mid, glow);
          color = mix(color, accent, smoothstep(0.6, 1.0, glow) * 0.55);

          float vignette = smoothstep(1.3, 0.2, length(uv - 0.5));
          color *= vignette;

          gl_FragColor = vec4(color, 0.45);
        }
      `,
      uniforms,
    });

    const mesh = new Mesh(gl, { geometry, program });
    container.appendChild(gl.canvas);
    gl.canvas.style.width = "100%";
    gl.canvas.style.height = "100%";
    gl.canvas.style.display = "block";

    let raf = 0;
    const start = performance.now();

    const resize = () => {
      const width = container.clientWidth || window.innerWidth;
      const height = container.clientHeight || window.innerHeight;
      renderer.setSize(width, height);
      uniforms.uResolution.value = [width, height];
    };

    const update = (now: number) => {
      uniforms.uTime.value = (now - start) * 0.001;
      renderer.render({ scene: mesh });
      raf = window.requestAnimationFrame(update);
    };

    resize();
    raf = window.requestAnimationFrame(update);
    window.addEventListener("resize", resize);

    return () => {
      window.cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      if (gl.canvas.parentNode) {
        gl.canvas.parentNode.removeChild(gl.canvas);
      }
      gl.getExtension("WEBGL_lose_context")?.loseContext();
    };
  }, []);

  return <div ref={containerRef} className="absolute inset-0 pointer-events-none" aria-hidden />;
}

