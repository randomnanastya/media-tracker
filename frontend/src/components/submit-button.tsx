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
          <span aria-hidden="true" className="inline-block animate-spin">⟳</span>
          <span className="sr-only">Loading...</span>
        </>
      ) : (
        label
      )}
    </button>
  );
}
