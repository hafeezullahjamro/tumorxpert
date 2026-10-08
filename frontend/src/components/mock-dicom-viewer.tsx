"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useViewerStore } from "../lib/store";
import { Tabs } from "./ui/tabs";

const VIEW_SHAPES = {
  axial: [128, 128, 64] as const,
  coronal: [128, 64, 128] as const,
  sagittal: [64, 128, 128] as const
};

type Orientation = keyof typeof VIEW_SHAPES;

function generateVolume(seed: string, dims: readonly [number, number, number]) {
  const data = new Float32Array(dims[0] * dims[1] * dims[2]);
  let hash = 0;
  for (const char of seed) hash = (hash << 5) - hash + char.charCodeAt(0);
  for (let i = 0; i < data.length; i += 1) {
    const value = Math.abs(Math.sin(hash + i * 0.013)) * 0.8 + 0.2;
    data[i] = value;
  }
  return data;
}

interface MockDicomViewerProps {
  studyId: string;
}

export function MockDicomViewer({ studyId }: MockDicomViewerProps) {
  const [orientation, setOrientation] = useState<Orientation>("axial");
  const [sliceIndex, setSliceIndex] = useState(0);

  const overlayOpacity = useViewerStore((state) => state.overlayOpacity);
  const toggleOverlayOpacity = useViewerStore((state) => state.toggleOverlayOpacity);
  const selectedRegion = useViewerStore((state) => state.selectedRegion);
  const setSelectedRegion = useViewerStore((state) => state.setSelectedRegion);
  const uncertaintyVisible = useViewerStore((state) => state.uncertaintyVisible);
  const toggleUncertainty = useViewerStore((state) => state.toggleUncertainty);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const dims = VIEW_SHAPES[orientation];
  const volume = useMemo(() => generateVolume(studyId + orientation, dims), [studyId, orientation]);

  useEffect(() => {
    const maxSlices = dims[2];
    setSliceIndex((current) => Math.min(current, maxSlices - 1));
  }, [dims]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === "[") {
        setSliceIndex((prev) => Math.max(prev - 1, 0));
      }
      if (event.key === "]") {
        setSliceIndex((prev) => Math.min(prev + 1, dims[2] - 1));
      }
      if (event.key.toLowerCase() === "u") {
        toggleUncertainty();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [dims, toggleUncertainty]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const [width, height, depth] = dims;
    canvas.width = width;
    canvas.height = height;

    const imageData = ctx.createImageData(width, height);
    for (let y = 0; y < height; y += 1) {
      for (let x = 0; x < width; x += 1) {
        const idx = sliceIndex * width * height + y * width + x;
        const value = volume[idx] ?? 0;
        const base = Math.round(value * 255);
        const pixelIndex = (y * width + x) * 4;
        imageData.data[pixelIndex] = base;
        imageData.data[pixelIndex + 1] = base;
        imageData.data[pixelIndex + 2] = base;
        imageData.data[pixelIndex + 3] = 255;
      }
    }
    ctx.putImageData(imageData, 0, 0);

    if (overlayOpacity > 0) {
      ctx.fillStyle =
        selectedRegion === "WT"
          ? `rgba(155, 104, 255, ${overlayOpacity})`
          : selectedRegion === "TC"
          ? `rgba(255, 104, 202, ${overlayOpacity})`
          : `rgba(255, 176, 104, ${overlayOpacity})`;
      ctx.fillRect(Math.floor(width * 0.25), Math.floor(height * 0.25), Math.floor(width * 0.5), Math.floor(height * 0.5));
    }

    if (uncertaintyVisible) {
      const gradient = ctx.createRadialGradient(width / 2, height / 2, width * 0.1, width / 2, height / 2, width * 0.6);
      gradient.addColorStop(0, "rgba(255,255,255,0)");
      gradient.addColorStop(1, "rgba(255,0,0,0.35)");
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, height);
    }
  }, [dims, overlayOpacity, selectedRegion, sliceIndex, uncertaintyVisible, volume]);

  return (
    <div className="flex h-full flex-col gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow">
      <div className="flex items-center justify-between">
        <Tabs
          tabs={[
            { id: "axial", label: "Axial" },
            { id: "sagittal", label: "Sagittal" },
            { id: "coronal", label: "Coronal" }
          ]}
          activeId={orientation}
          onChange={(tab) => setOrientation(tab as Orientation)}
        />
        <div className="flex items-center gap-3 text-sm">
          <label className="flex items-center gap-2">
            Overlay
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={overlayOpacity}
              onChange={(event) => toggleOverlayOpacity(Number(event.currentTarget.value))}
            />
          </label>
          <label className="flex items-center gap-2">
            Uncertainty
            <input type="checkbox" checked={uncertaintyVisible} onChange={toggleUncertainty} />
          </label>
          <select
            value={selectedRegion}
            onChange={(event) => setSelectedRegion(event.currentTarget.value as "WT" | "TC" | "ET")}
            className="rounded-md border border-slate-200 px-2 py-1"
          >
            <option value="WT">WT</option>
            <option value="TC">TC</option>
            <option value="ET">ET</option>
          </select>
        </div>
      </div>
      <div className="flex flex-1 items-center justify-center bg-black">
        <canvas ref={canvasRef} className="max-h-[480px] max-w-full" />
      </div>
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>
          Slice {sliceIndex + 1} / {dims[2]}
        </span>
        <span>Shortcuts: [ / ] to scroll | U toggles uncertainty.</span>
      </div>
    </div>
  );
}
