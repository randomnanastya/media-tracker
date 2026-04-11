import { Image } from "lucide-react";

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
    <div className={`flex items-center justify-center bg-[#2a2520]/5 ${className}`}>
      <Image size={32} className="text-[#2a2520]/20" aria-hidden="true" />
    </div>
  );
}
