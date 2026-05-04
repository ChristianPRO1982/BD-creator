import { CSSProperties, MouseEvent } from "react";
import { assetContentUrl } from "../services/media";
import { Asset, Panel, Slot, TextBlock } from "../types";

type Props = {
  panel: Panel;
  slot?: Slot;
  asset?: Asset;
  textBlocks: TextBlock[];
  mode: "preview" | "edit";
  active?: boolean;
  onSelect?: () => void;
  onTextDragStart?: (textBlock: TextBlock, event: MouseEvent<HTMLDivElement>) => void;
};

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function hexToRgba(color: string, opacity: number) {
  const safe = /^#[0-9a-fA-F]{6}$/.test(color) ? color : "#ffffff";
  const raw = safe.slice(1);
  const r = parseInt(raw.slice(0, 2), 16);
  const g = parseInt(raw.slice(2, 4), 16);
  const b = parseInt(raw.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${clamp(opacity, 0, 1)})`;
}

export function PanelCanvas({ panel, slot, asset, textBlocks, mode, active = false, onSelect, onTextDragStart }: Props) {
  const zoom = clamp(panel.crop_zoom || 1, 0.2, 5);
  const offsetX = clamp(panel.crop_offset_x || 0, -1, 1);
  const offsetY = clamp(panel.crop_offset_y || 0, -1, 1);

  const bgStyle: CSSProperties = asset
    ? {
        backgroundImage: `url(${assetContentUrl(asset.id)})`,
        backgroundRepeat: "no-repeat",
        backgroundSize: `${zoom * 100}% ${zoom * 100}%`,
        backgroundPosition: `${50 + offsetX * 50}% ${50 + offsetY * 50}%`,
      }
    : { background: "linear-gradient(120deg, #ece9e0, #f8f8f8)" };

  return (
    <div
      className={`panel-canvas ${active ? "active" : ""} ${mode === "edit" ? "edit" : ""}`}
      style={{
        gridColumn: slot ? `${slot.col_start} / span ${slot.col_span}` : undefined,
        gridRow: slot ? `${slot.row_start} / span ${slot.row_span}` : undefined,
      }}
      onClick={onSelect}
      role={onSelect ? "button" : undefined}
      tabIndex={onSelect ? 0 : undefined}
      onKeyDown={(e) => {
        if (!onSelect) return;
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect();
        }
      }}
    >
      <div className="panel-canvas-bg" style={bgStyle} />
      <div className="panel-canvas-overlay">
        {textBlocks.map((tb) => (
          <div
            key={tb.id}
            className={`text-block ${mode === "edit" ? "draggable" : ""}`}
            style={{
              left: `${tb.x * 100}%`,
              top: `${tb.y * 100}%`,
              width: `${tb.width * 100}%`,
              height: `${tb.height * 100}%`,
              fontSize: `${tb.font_size}px`,
              color: tb.text_color,
              background: hexToRgba(tb.background_color, tb.background_opacity),
            }}
            onMouseDown={(event) => {
              if (mode !== "edit" || !onTextDragStart) return;
              event.stopPropagation();
              onTextDragStart(tb, event);
            }}
          >
            {tb.content}
          </div>
        ))}
      </div>
      <span className="panel-order">{panel.reading_order}</span>
    </div>
  );
}
