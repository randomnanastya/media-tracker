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
    <div className={`flex items-center justify-center bg-gray-200 ${className}`}>
      <Film size={56} className="text-gray-400" aria-hidden="true" />
    </div>
  );
}
