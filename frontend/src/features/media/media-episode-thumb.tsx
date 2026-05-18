import { useState } from "react";
import { Film } from "lucide-react";

interface ThumbProps {
  src: string | null;
  alt: string;
  className?: string;
}

export function MediaEpisodeThumb({ src, alt, className = "" }: ThumbProps) {
  const [status, setStatus] = useState<"loading" | "loaded" | "error">(src ? "loading" : "error");

  if (!src || status === "error") {
    return (
      <div className={`flex items-center justify-center bg-[#2a2520]/8 aspect-video ${className}`}>
        <Film size={24} className="text-[#2a2520]/40" aria-hidden="true" />
      </div>
    );
  }

  return (
    <div className={`relative aspect-video overflow-hidden ${className}`}>
      {status === "loading" && (
        <div className="absolute inset-0 bg-[#2a2520]/8 animate-pulse" />
      )}
      <img
        src={src}
        alt={alt}
        loading="lazy"
        decoding="async"
        onLoad={() => setStatus("loaded")}
        onError={() => setStatus("error")}
        className={`w-full h-full object-cover transition-opacity duration-200 ${status === "loading" ? "opacity-0" : "opacity-100"}`}
      />
    </div>
  );
}
