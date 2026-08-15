import { forwardRef } from 'react';
import { clsx } from 'clsx';

interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number;
  max?: number;
  variant?: 'default' | 'success' | 'warning' | 'destructive';
  showLabel?: boolean;
}

const Progress = forwardRef<HTMLDivElement, ProgressProps>(
  ({ className, value, max = 100, variant = 'default', showLabel = false, ...props }, ref) => {
    const percentage = Math.min(Math.max((value / max) * 100, 0), 100);
    return (
      <div ref={ref} className={clsx('relative h-2 w-full overflow-hidden rounded-full bg-moon-800', className)} {...props}>
        <div
          className={clsx(
            'h-full transition-all duration-300 ease-out',
            {
              'bg-gradient-to-r from-green-500 to-green-400': variant === 'success',
              'bg-gradient-to-r from-yellow-500 to-yellow-400': variant === 'warning',
              'bg-gradient-to-r from-red-500 to-red-400': variant === 'destructive',
              'bg-gradient-to-r from-moon-400 to-moon-500': variant === 'default',
            }
          )}
          style={{ width: `${percentage}%` }}
        />
        {showLabel && (
          <span className="absolute inset-0 flex items-center justify-center text-xs font-mono text-moon-900">
            {Math.round(percentage)}%
          </span>
        )}
      </div>
    );
  }
);
Progress.displayName = 'Progress';

export { Progress };