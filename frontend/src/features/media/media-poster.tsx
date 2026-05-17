import { Film } from "lucide-react";

interface Props {
  src: string | null;
  alt: string;
  className?: string;
}

export function MediaPoster({ src, alt, className = "" }: Props) {
  if (src) {
    return (
      <img
        src={src}
        alt={alt}
        className={`object-cover ${className}`}
      />
    );
  }
  return (
    <div className={`flex items-center justify-center bg-[#e5e1d8] ${className}`}>
      <Film size={48} className="text-[#6b6b6b] opacity-30" aria-hidden="true" />
    </div>
  );
}
