interface SubmitButtonProps {
  label: string;
  isLoading: boolean;
}

export function SubmitButton({ label, isLoading }: SubmitButtonProps) {
  return (
    <button
      type="submit"
      disabled={isLoading}
      aria-busy={isLoading}
      className="w-full py-2.5 rounded-lg bg-mt-accent text-mt-black font-semibold hover:bg-mt-accent/90 disabled:opacity-50 transition-colors cursor-pointer mt-4 focus-visible:ring-2 focus-visible:ring-mt-accent focus-visible:outline-none"
    >
      {isLoading ? (
        <>
          <svg aria-hidden="true" className="inline-block animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
          </svg>
          <span className="sr-only">Loading...</span>
        </>
      ) : (
        label
      )}
    </button>
  );
}
