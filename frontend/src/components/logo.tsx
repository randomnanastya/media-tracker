import logoMark from "../assets/logo-mark.svg";

export function Logo() {
  return (
    <div className="flex flex-col items-center gap-2 mb-6">
      <img src={logoMark} alt="Media Tracker" className="w-14 h-14" />
      <div className="text-mt-light font-semibold text-2xl tracking-tight lowercase">
        mediatracker
      </div>
      <div className="text-mt-light/50 text-xs tracking-[0.3em]">SELF-HOSTED</div>
    </div>
  );
}
