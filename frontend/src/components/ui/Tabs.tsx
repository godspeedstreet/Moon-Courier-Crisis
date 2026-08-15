import * as TabsPrimitive from '@radix-ui/react-tabs';
import { clsx } from 'clsx';

const Tabs = TabsPrimitive.Root;

const TabsList = ({ className, ...props }: React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>) => (
  <TabsPrimitive.List
    className={clsx(
      'inline-flex h-10 items-center justify-center rounded-md bg-moon-800 p-1 text-moon-300',
      className
    )}
    {...props}
  />
);

const TabsTrigger = ({ className, ...props }: React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>) => (
  <TabsPrimitive.Trigger
    className={clsx(
      'inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-moon-400 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-moon-700 data-[state=active]:text-white data-[state=active]:shadow-sm',
      className
    )}
    {...props}
  />
);

const TabsContent = ({ className, ...props }: React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>) => (
  <TabsPrimitive.Content
    className={clsx(
      'mt-2 ring-offset-moon-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-moon-400 focus-visible:ring-offset-2',
      className
    )}
    {...props}
  />
);

export { Tabs, TabsList, TabsTrigger, TabsContent };