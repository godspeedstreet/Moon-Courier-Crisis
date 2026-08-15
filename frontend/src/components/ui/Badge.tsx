import { forwardRef } from 'react';
import { clsx } from 'clsx';

interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning';
}

const Badge = forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant = 'default', ...props }, ref) => (
    <div
      ref={ref}
      className={clsx(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-moon-400 focus:ring-offset-2',
        {
          'border-transparent bg-moon-700 text-moon-50 hover:bg-moon-600': variant === 'default',
          'border-transparent bg-moon-800 text-moon-50 hover:bg-moon-700': variant === 'secondary',
          'border-transparent bg-red-600 text-white hover:bg-red-700': variant === 'destructive',
          'border-moon-600 text-moon-50 hover:bg-moon-800': variant === 'outline',
          'border-transparent bg-green-600 text-white hover:bg-green-700': variant === 'success',
          'border-transparent bg-yellow-600 text-white hover:bg-yellow-700': variant === 'warning',
        },
        className
      )}
      {...props}
    />
  )
);
Badge.displayName = 'Badge';

export { Badge };