import { useState } from "react";

interface RecoveryCodeDisplayProps {
  code: string;
  onContinue: () => void;
}

export function RecoveryCodeDisplay({
  code,
  onContinue,
}: RecoveryCodeDisplayProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    void navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div>
      <p className="text-mt-light font-semibold mb-2">
        Save this recovery code
      </p>
      <p className="text-mt-light/70 text-sm mb-4">
        This is your only way to reset your password. Store it securely.
      </p>
      <output
        aria-label="Recovery code"
        className="block bg-mt-input-bg border border-mt-input-border rounded-lg p-3 font-mono text-mt-accent text-center text-lg mb-4 break-all"
      >
        {code}
      </output>
      <button
        type="button"
        onClick={handleCopy}
        className="w-full py-2 rounded-lg border border-mt-input-border text-mt-light text-sm mb-3 hover:border-mt-accent transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-mt-accent focus-visible:outline-none"
      >
        {copied ? "Copied!" : "Copy"}
      </button>
      <button
        type="button"
        onClick={onContinue}
        className="w-full py-2.5 rounded-lg bg-mt-accent text-mt-black font-semibold hover:bg-mt-accent/90 transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-mt-accent focus-visible:outline-none"
      >
        I saved it, continue
      </button>
    </div>
  );
}
