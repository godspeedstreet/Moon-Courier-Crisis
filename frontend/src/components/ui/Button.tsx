import { Slot } from '@radix-ui/react-slot';
import { forwardRef } from 'react';
import { clsx } from 'clsx';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  asChild?: boolean;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp
        className={clsx(
          'inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-moon-950 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-moon-400 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
          {
            'bg-moon-700 text-moon-50 hover:bg-moon-600': variant === 'default',
            'bg-red-600 text-white hover:bg-red-700': variant === 'destructive',
            'border border-moon-600 bg-transparent hover:bg-moon-800': variant === 'outline',
            'bg-moon-800 text-moon-50 hover:bg-moon-700': variant === 'secondary',
            'hover:bg-moon-800': variant === 'ghost',
            'text-moon-400 underline-offset-4 hover:underline': variant === 'link',
            'h-10 px-4 py-2': size === 'default',
            'h-9 rounded-md px-3': size === 'sm',
            'h-11 rounded-md px-8': size === 'lg',
            'h-10 w-10': size === 'icon',
          },
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = 'Button';

export { Button };