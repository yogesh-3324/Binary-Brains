export const LogoIcon = ({ className = "w-8 h-8" }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 40 40"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <defs>
      <linearGradient id="sameShotGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#3B82F6" />
        <stop offset="100%" stopColor="#6366F1" />
      </linearGradient>
    </defs>
    <rect width="40" height="40" rx="10" fill="url(#sameShotGrad)" />
    <rect x="9" y="13" width="16" height="16" rx="3" stroke="white" strokeWidth="2.2" strokeOpacity="0.75" fill="none" />
    <rect x="15" y="9" width="16" height="16" rx="3" stroke="white" strokeWidth="2.2" fill="none" />
    <circle cx="23" cy="17" r="2.5" fill="#60A5FA" />
  </svg>
);

export const LogoBrand = ({
  textClassName = "text-xl font-bold tracking-tight text-slate-900",
  lightMode = false
}: {
  textClassName?: string;
  lightMode?: boolean;
}) => (
  <div className="flex items-center gap-2.5">
    <LogoIcon className="w-8 h-8 drop-shadow-md" />
    <span className={textClassName}>
      Same<span className={lightMode ? "text-blue-200" : "text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600"}>Shot</span>
    </span>
  </div>
);
